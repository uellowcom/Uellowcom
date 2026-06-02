import base64
import json
import logging
from datetime import datetime, timedelta

import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

REPLICATE_API_BASE = 'https://api.replicate.com/v1'
REPLICATE_TIMEOUT  = 30  # seconds for API calls (not for the generation itself)

FASHN_API_BASE = 'https://api.fashn.ai/v1'
FASHN_TIMEOUT  = 30

# Per-call cost in USD. idm-vton: ~$0.04. Override via setting tryon_cost_per_call.
DEFAULT_COST_PER_CALL_REPLICATE = 0.04
DEFAULT_COST_PER_CALL_FASHN     = 0.08


class TryOnController(http.Controller):

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            f'uellow_ai.{key}', default
        )

    def _is_enabled(self):
        return self._param('tryon_enabled', 'False') in ('True', '1', 'true')

    # Replicate
    def _get_token(self):
        return (self._param('tryon_replicate_token', '') or '').strip()

    def _get_model(self):
        return (self._param('tryon_replicate_model', 'cuuupid/idm-vton') or 'cuuupid/idm-vton').strip()

    # FASHN
    def _fashn_enabled(self):
        return self._param('tryon_fashn_enabled', 'False') in ('True', '1', 'true')

    def _fashn_token(self):
        return (self._param('tryon_fashn_token', '') or '').strip()

    def _fashn_model(self):
        return (self._param('tryon_fashn_model', 'tryon-v1.5') or 'tryon-v1.5').strip()

    # Routing
    def _provider_primary(self):
        v = (self._param('tryon_provider_primary', 'replicate') or 'replicate').strip()
        return v if v in ('replicate', 'fashn') else 'replicate'

    def _provider_fallback(self):
        v = (self._param('tryon_provider_fallback', 'none') or 'none').strip()
        return v if v in ('replicate', 'fashn', 'none') else 'none'

    def _provider_available(self, name):
        if name == 'replicate':
            return bool(self._get_token())
        if name == 'fashn':
            return bool(self._fashn_enabled() and self._fashn_token())
        return False

    def _cost_per_call(self, provider='replicate'):
        key = f'tryon_cost_per_call_{provider}'
        default = (DEFAULT_COST_PER_CALL_FASHN if provider == 'fashn'
                   else DEFAULT_COST_PER_CALL_REPLICATE)
        try:
            return float(self._param(key, str(default)))
        except (TypeError, ValueError):
            return default

    def _logged_in_partner(self):
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return None
        return request.env.user.partner_id

    def _eligible_categories(self):
        raw = self._param('tryon_eligible_categories', 'shirt,tshirt,dress') or ''
        return [c.strip().lower() for c in raw.replace('\n', ',').split(',') if c.strip()]

    def _product_eligible(self, product):
        """Check if a product is eligible for try-on (category + price)."""
        try:
            min_price = float(self._param('tryon_min_price_kd', '5.0'))
        except (TypeError, ValueError):
            min_price = 5.0

        if product.list_price < min_price:
            return False, 'price_below_min', {'min_kd': min_price, 'product_kd': product.list_price}

        cats = self._eligible_categories()
        if not cats:
            return False, 'no_categories_configured', {}

        haystack = (product.name or '').lower()
        if product.categ_id:
            haystack += ' ' + (product.categ_id.name or '').lower()
        if not any(c in haystack for c in cats):
            return False, 'category_not_eligible', {'allowed': cats}

        return True, None, {}

    def _check_caps(self, partner):
        """Check monthly USD cap, monthly count cap, daily-per-customer cap.
        Returns (ok, reason, info)."""
        Image = request.env['customer.tryon.image'].sudo()

        # Month-to-date stats
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly = Image.search([('create_date', '>=', month_start),
                                ('status', '!=', 'failed')])
        spent_usd = sum(i.cost_usd or 0.0 for i in monthly)
        gen_count = len(monthly)

        try:
            usd_cap = float(self._param('tryon_monthly_usd_cap', '50.0'))
        except (TypeError, ValueError):
            usd_cap = 50.0
        try:
            gen_cap = int(self._param('tryon_monthly_gen_cap', '1000'))
        except (TypeError, ValueError):
            gen_cap = 1000
        try:
            per_day = int(self._param('tryon_daily_per_customer_cap', '5'))
        except (TypeError, ValueError):
            per_day = 5

        if spent_usd >= usd_cap:
            return False, 'monthly_usd_cap_reached', {'spent_usd': spent_usd, 'cap_usd': usd_cap}
        if gen_count >= gen_cap:
            return False, 'monthly_gen_cap_reached', {'count': gen_count, 'cap': gen_cap}

        # Daily per-customer
        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_for_user = Image.search_count([
            ('create_date', '>=', day_start),
            ('partner_id', '=', partner.id),
            ('status', '!=', 'failed'),
        ])
        if today_for_user >= per_day:
            return False, 'daily_customer_cap_reached', {'count': today_for_user, 'cap': per_day}

        return True, None, {'spent_usd': spent_usd, 'gen_count': gen_count,
                            'today_for_user': today_for_user}

    def _get_or_create_profile(self, partner):
        Profile = request.env['customer.body.profile'].sudo()
        profile = Profile.search([('partner_id', '=', partner.id)], limit=1)
        if not profile:
            profile = Profile.create({'partner_id': partner.id})
        return profile

    def _binary_to_data_url(self, binary_b64, mime='image/jpeg'):
        """Convert an Odoo binary field value to a data URL Replicate can fetch."""
        if not binary_b64:
            return None
        raw = binary_b64.decode() if isinstance(binary_b64, bytes) else str(binary_b64)
        return f'data:{mime};base64,{raw}'

    # ── Endpoints ─────────────────────────────────────────────────────────────

    @http.route('/tryon/upload-photo', type='json', auth='user', methods=['POST'], csrf=False)
    def upload_photo(self, **kwargs):
        """Customer uploads their try-on source photo. Saved on the body profile."""
        if not self._is_enabled():
            return {'success': False, 'error': 'tryon_disabled'}

        partner = self._logged_in_partner()
        if not partner:
            return {'success': False, 'error': 'login_required'}

        image_b64 = kwargs.get('image_base64')
        if not image_b64:
            return {'success': False, 'error': 'image_required'}

        # Strip data URL prefix if present
        if isinstance(image_b64, str) and image_b64.startswith('data:'):
            image_b64 = image_b64.split(',', 1)[1] if ',' in image_b64 else image_b64

        filename = kwargs.get('filename') or 'tryon_photo.jpg'
        profile  = self._get_or_create_profile(partner)
        profile.write({
            'tryon_photo':          image_b64,
            'tryon_photo_filename': filename,
            'tryon_photo_uploaded': datetime.now(),
        })
        return {'success': True, 'filename': filename}

    # ── Provider clients ────────────────────────────────────────────────

    def _fashn_category(self, product):
        """Map our product category to FASHN's category enum."""
        from odoo.addons.uellow_smart_fit.controllers.fit_controller import SmartFitController
        cat = SmartFitController()._detect_category(product)
        if cat in ('shirt', 'tshirt', 'jacket', 'top', 'sweater', 'hoodie', 'coat'):
            return 'tops'
        if cat in ('pants', 'jeans', 'shorts'):
            return 'bottoms'
        if cat in ('dress', 'gown', 'abaya'):
            return 'one-pieces'
        return 'auto'

    def _call_replicate(self, human_url, garment_url, garment_des):
        """Returns {success, prediction_id, model, status, error, detail}."""
        token = self._get_token()
        if not token:
            return {'success': False, 'error': 'replicate_token_missing'}

        headers = {
            'Authorization': f'Token {token}',
            'Content-Type':  'application/json',
            'Prefer':        'respond-async',
        }
        payload_input = {
            'human_img':   human_url,
            'garm_img':    garment_url,
            'garment_des': garment_des,
        }
        model = self._get_model()

        # Strategy 1: official-model shortcut endpoint
        try:
            resp = requests.post(
                f'{REPLICATE_API_BASE}/models/{model}/predictions',
                headers=headers, json={'input': payload_input},
                timeout=REPLICATE_TIMEOUT,
            )
        except requests.RequestException as e:
            return {'success': False, 'error': 'replicate_unreachable', 'detail': str(e)}

        # Strategy 2: community model — fetch version and POST to /predictions
        if resp.status_code == 404:
            try:
                meta = requests.get(
                    f'{REPLICATE_API_BASE}/models/{model}',
                    headers={'Authorization': f'Token {token}'},
                    timeout=10,
                )
                if meta.status_code != 200:
                    return {'success': False, 'error': 'replicate_model_not_found',
                            'status': meta.status_code, 'detail': meta.text[:500]}
                version_id = (meta.json().get('latest_version') or {}).get('id')
                if not version_id:
                    return {'success': False, 'error': 'no_model_version'}
                resp = requests.post(
                    f'{REPLICATE_API_BASE}/predictions',
                    headers=headers,
                    json={'version': version_id, 'input': payload_input},
                    timeout=REPLICATE_TIMEOUT,
                )
            except requests.RequestException as e:
                return {'success': False, 'error': 'replicate_unreachable',
                        'detail': str(e)}

        if resp.status_code not in (200, 201):
            return {'success': False, 'error': 'replicate_error',
                    'status': resp.status_code, 'detail': resp.text[:500]}

        data = resp.json()
        prediction_id = data.get('id')
        if not prediction_id:
            return {'success': False, 'error': 'no_prediction_id', 'detail': str(data)[:300]}
        return {
            'success':       True,
            'prediction_id': prediction_id,
            'model':         model,
            'status':        data.get('status') or 'running',
        }

    def _call_fashn(self, human_url, garment_url, category='auto'):
        """Returns {success, prediction_id, model, status, error, detail}.
        FASHN's API: POST /v1/run with model_image + garment_image + category.
        """
        token = self._fashn_token()
        if not token:
            return {'success': False, 'error': 'fashn_token_missing'}
        model_name = self._fashn_model()

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type':  'application/json',
        }
        payload = {
            'model_name':    model_name,
            'inputs': {
                'model_image':   human_url,
                'garment_image': garment_url,
                'category':      category or 'auto',
            },
        }
        try:
            resp = requests.post(
                f'{FASHN_API_BASE}/run',
                headers=headers, json=payload, timeout=FASHN_TIMEOUT,
            )
        except requests.RequestException as e:
            return {'success': False, 'error': 'fashn_unreachable', 'detail': str(e)}

        if resp.status_code not in (200, 201, 202):
            return {'success': False, 'error': 'fashn_error',
                    'status': resp.status_code, 'detail': resp.text[:500]}

        data = resp.json()
        # FASHN returns {id, error}. If error is set, treat as failure.
        if data.get('error'):
            return {'success': False, 'error': 'fashn_error',
                    'detail': str(data.get('error'))[:500]}
        prediction_id = data.get('id')
        if not prediction_id:
            return {'success': False, 'error': 'no_prediction_id',
                    'detail': str(data)[:300]}
        return {
            'success':       True,
            'prediction_id': prediction_id,
            'model':         model_name,
            'status':        'running',
        }

    @http.route('/tryon/generate', type='json', auth='user', methods=['POST'], csrf=False)
    def generate(self, **kwargs):
        """Start a virtual try-on generation. Routes to the configured primary
        provider; falls back to the configured fallback on failure."""
        if not self._is_enabled():
            return {'success': False, 'error': 'tryon_disabled'}

        partner = self._logged_in_partner()
        if not partner:
            return {'success': False, 'error': 'login_required'}

        product_id = kwargs.get('product_id')
        if not product_id:
            return {'success': False, 'error': 'product_id_required'}

        product = request.env['product.template'].sudo().browse(int(product_id))
        if not product.exists():
            return {'success': False, 'error': 'product_not_found'}

        # Eligibility
        ok, reason, info = self._product_eligible(product)
        if not ok:
            return {'success': False, 'error': reason, 'info': info}

        # Profile photo
        profile = self._get_or_create_profile(partner)
        if not profile.tryon_photo:
            return {'success': False, 'error': 'no_photo'}

        # Caps
        ok, reason, info = self._check_caps(partner)
        if not ok:
            return {'success': False, 'error': reason, 'info': info}

        # Product image
        if not product.image_1920:
            return {'success': False, 'error': 'product_image_missing'}

        # Build inputs as data URLs (simplest, works without public hosting)
        human_url   = self._binary_to_data_url(profile.tryon_photo)
        garment_url = self._binary_to_data_url(product.image_1920)
        if not human_url or not garment_url:
            return {'success': False, 'error': 'image_encoding_failed'}

        garment_des = product.name or 'clothing item'
        fashn_cat   = self._fashn_category(product)

        # ── Provider dispatch ──
        primary  = self._provider_primary()
        fallback = self._provider_fallback()
        order = [primary]
        if fallback != 'none' and fallback != primary:
            order.append(fallback)

        last_err = None
        used = None
        result = None
        for prov in order:
            if not self._provider_available(prov):
                last_err = {'success': False, 'error': f'{prov}_not_configured'}
                continue
            if prov == 'replicate':
                result = self._call_replicate(human_url, garment_url, garment_des)
            else:  # fashn
                result = self._call_fashn(human_url, garment_url, fashn_cat)
            if result.get('success'):
                used = prov
                break
            last_err = result
            _logger.warning('try-on provider %s failed: %s', prov, result)

        if not used or not result or not result.get('success'):
            return last_err or {'success': False, 'error': 'all_providers_failed'}

        # Persist session + image
        Session = request.env['customer.tryon.session'].sudo()
        session = Session.create({
            'partner_id':            partner.id,
            'product_id':            product.id,
            'source_photo':          profile.tryon_photo,
            'source_photo_filename': profile.tryon_photo_filename,
            'status':                'running',
        })
        Image = request.env['customer.tryon.image'].sudo()
        image = Image.create({
            'session_id':             session.id,
            'provider':               used,
            'provider_model':         result.get('model') or '',
            'provider_prediction_id': result['prediction_id'],
            'status':                 'running',
            'cost_usd':               self._cost_per_call(used),
            'started_at':             datetime.now(),
        })
        request.env.cr.commit()

        return {
            'success':       True,
            'session_id':    session.id,
            'image_id':      image.id,
            'prediction_id': result['prediction_id'],
            'provider':      used,
            'status':        result.get('status') or 'running',
        }

    def _fetch_replicate_status(self, prediction_id):
        """Returns {ok, status, output_url, error}."""
        token = self._get_token()
        if not token:
            return {'ok': False, 'error': 'token_not_configured'}
        try:
            resp = requests.get(
                f'{REPLICATE_API_BASE}/predictions/{prediction_id}',
                headers={'Authorization': f'Token {token}'},
                timeout=REPLICATE_TIMEOUT,
            )
        except requests.RequestException as e:
            return {'ok': False, 'error': 'replicate_unreachable', 'detail': str(e)}
        if resp.status_code != 200:
            return {'ok': False, 'error': 'replicate_error',
                    'status': resp.status_code, 'detail': resp.text[:300]}
        data = resp.json()
        rstatus = data.get('status')  # starting | processing | succeeded | failed | canceled
        if rstatus == 'succeeded':
            output = data.get('output')
            img_url = output[0] if isinstance(output, list) and output else output
            return {'ok': True, 'status': 'done', 'output_url': img_url}
        if rstatus in ('failed', 'canceled'):
            return {'ok': True, 'status': 'failed',
                    'error': str(data.get('error') or rstatus)[:500]}
        return {'ok': True, 'status': 'running'}

    def _fetch_fashn_status(self, prediction_id):
        """Returns {ok, status, output_url, error}.
        FASHN status payload: {id, status: in_queue|processing|completed|failed,
        output: [url], error: str|None}.
        """
        token = self._fashn_token()
        if not token:
            return {'ok': False, 'error': 'fashn_token_missing'}
        try:
            resp = requests.get(
                f'{FASHN_API_BASE}/status/{prediction_id}',
                headers={'Authorization': f'Bearer {token}'},
                timeout=FASHN_TIMEOUT,
            )
        except requests.RequestException as e:
            return {'ok': False, 'error': 'fashn_unreachable', 'detail': str(e)}
        if resp.status_code != 200:
            return {'ok': False, 'error': 'fashn_error',
                    'status': resp.status_code, 'detail': resp.text[:300]}
        data = resp.json()
        fstatus = data.get('status')
        if fstatus == 'completed':
            output = data.get('output')
            img_url = output[0] if isinstance(output, list) and output else output
            return {'ok': True, 'status': 'done', 'output_url': img_url}
        if fstatus == 'failed':
            return {'ok': True, 'status': 'failed',
                    'error': str(data.get('error') or 'failed')[:500]}
        return {'ok': True, 'status': 'running'}

    @http.route('/tryon/status/<int:image_id>', type='json', auth='user', methods=['POST'], csrf=False)
    def status(self, image_id, **kwargs):
        """Poll the status of a generation. Dispatches by provider."""
        if not self._is_enabled():
            return {'success': False, 'error': 'tryon_disabled'}

        partner = self._logged_in_partner()
        if not partner:
            return {'success': False, 'error': 'login_required'}

        Image = request.env['customer.tryon.image'].sudo()
        image = Image.browse(image_id)
        if not image.exists() or image.partner_id.id != partner.id:
            return {'success': False, 'error': 'not_found'}

        # Already finished — return cached state
        if image.status in ('done', 'failed'):
            return {
                'success':   True,
                'image_id':  image.id,
                'status':    image.status,
                'image_url': image.image_url,
                'error':     image.error_msg or None,
                'provider':  image.provider,
            }

        provider = image.provider or 'replicate'
        if provider == 'fashn':
            res = self._fetch_fashn_status(image.provider_prediction_id)
        else:
            res = self._fetch_replicate_status(image.provider_prediction_id)

        if not res.get('ok'):
            return {'success': False, 'error': res.get('error') or 'status_failed',
                    'detail': res.get('detail')}

        rstatus = res.get('status')
        if rstatus == 'done':
            img_url = res.get('output_url')
            img_b64 = None
            if img_url:
                try:
                    dl = requests.get(img_url, timeout=REPLICATE_TIMEOUT)
                    if dl.status_code == 200:
                        img_b64 = base64.b64encode(dl.content)
                except requests.RequestException as e:
                    _logger.warning('Failed to download generated image: %s', e)
            image.write({
                'status':      'done',
                'image_url':   img_url or False,
                'image':       img_b64 or False,
                'finished_at': datetime.now(),
            })
            image.session_id.sudo().write({'status': 'done'})
            request.env.cr.commit()
            return {'success': True, 'image_id': image.id, 'status': 'done',
                    'image_url': img_url, 'provider': provider}

        if rstatus == 'failed':
            err = res.get('error') or 'failed'
            image.write({
                'status':      'failed',
                'error_msg':   str(err)[:500],
                'finished_at': datetime.now(),
            })
            image.session_id.sudo().write({'status': 'failed'})
            request.env.cr.commit()
            return {'success': True, 'image_id': image.id, 'status': 'failed',
                    'error': str(err)[:500], 'provider': provider}

        # Still in progress
        image.write({'status': 'running'})
        return {'success': True, 'image_id': image.id, 'status': 'running',
                'provider': provider}

    @http.route('/tryon/my-sessions', type='json', auth='user', methods=['POST'], csrf=False)
    def my_sessions(self, **kwargs):
        """Customer's try-on history."""
        partner = self._logged_in_partner()
        if not partner:
            return {'success': False, 'error': 'login_required'}

        limit = int(kwargs.get('limit') or 20)
        Session = request.env['customer.tryon.session'].sudo()
        sessions = Session.search([('partner_id', '=', partner.id)],
                                  limit=limit, order='create_date desc')
        return {
            'success': True,
            'sessions': [{
                'id':           s.id,
                'product_id':   s.product_id.id,
                'product_name': s.product_id.name,
                'status':       s.status,
                'image_count':  s.image_count,
                'created':      s.create_date and s.create_date.isoformat() or None,
                'images':       [{
                    'id':        i.id,
                    'status':    i.status,
                    'image_url': i.image_url,
                    'color':     i.color_text,
                } for i in s.image_ids],
            } for s in sessions],
        }
