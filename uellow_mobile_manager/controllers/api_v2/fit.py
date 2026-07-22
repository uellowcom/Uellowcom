"""Smart Fit profile — /api/mobile/v2/fit/*

The existing /fit/* endpoints in `uellow_smart_fit` are type='json' +
auth='user' (Odoo JSON-RPC + Odoo session login). The mobile app uses
Bearer tokens against type='http' + auth='public' routes — so we wrap
the same logic here with the right auth.

Endpoints:
  GET  /api/mobile/v2/fit/profile         → current measurements
  POST /api/mobile/v2/fit/profile/save    → upsert measurements
  POST /api/mobile/v2/fit/recommend       → size suggestion for a product
"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner, require_auth,
    decode_image_upload,
)


_FIELDS = (
    'height', 'weight', 'body_type', 'gender', 'shoulder', 'chest',
    'waist', 'hip', 'arm_length', 'inseam', 'thigh',
    'shoe_size_eu', 'shoe_size_us', 'shoe_width', 'preferred_fit',
)


def _get_or_create_profile(partner):
    BP = request.env.get('customer.body.profile')
    if BP is None:
        return None
    # v2.1.47 — look across the whole partner family (the website
    # account sometimes saves under the commercial partner or a child
    # contact) so the app shows the SAME profile as the Odoo account.
    family = [partner.id]
    try:
        if partner.commercial_partner_id and \
                partner.commercial_partner_id.id != partner.id:
            family.append(partner.commercial_partner_id.id)
        family += partner.child_ids.ids
        if partner.parent_id:
            family.append(partner.parent_id.id)
            family += partner.parent_id.child_ids.ids
    except Exception:
        pass
    prof = BP.sudo().search([
        ('partner_id', 'in', family),
        ('profile_complete', '=', True),
    ], limit=1)
    if not prof:
        prof = BP.sudo().search([('partner_id', 'in', family)], limit=1)
    if not prof:
        prof = BP.sudo().create({'partner_id': partner.id})
    return prof


def _to_dict(profile):
    if not profile:
        return {}
    out = {'id': profile.id}
    for f in _FIELDS:
        if f in profile._fields:
            v = profile[f]
            out[f] = v if not hasattr(v, 'id') else (v.id or 0)
    # Computed helpers
    for f in ('profile_complete', 'completion_pct'):
        if f in profile._fields:
            out[f] = profile[f]
    # v2.1.54 — measurement history for the My Sizes screen.
    try:
        import json as _json
        if 'measure_history_json' in profile._fields:
            out['history'] = _json.loads(
                profile.measure_history_json or '[]')[:20]
    except Exception:
        out['history'] = []
    return out


class MobileFitAPI(http.Controller):

    @http.route('/api/mobile/v2/fit/profile', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def get_profile(self, **kw):
        partner = current_partner()
        prof = _get_or_create_profile(partner)
        if prof is None:
            return fail('NO_MODULE', 'Smart Fit module not installed', 503)
        return ok({'profile': _to_dict(prof)})

    @http.route('/api/mobile/v2/fit/profile/save', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def save_profile(self, **kw):
        partner = current_partner()
        prof = _get_or_create_profile(partner)
        if prof is None:
            return fail('NO_MODULE', 'Smart Fit module not installed', 503)
        p = get_payload()
        vals = {}
        # v2.1.49 — legacy/foreign aliases mapped to real selection keys.
        aliases = {
            'body_type': {'average': 'regular', 'normal': 'regular',
                          'fit': 'athletic'},
            'preferred_fit': {'tight': 'slim', 'relaxed': 'loose',
                              'normal': 'regular'},
        }
        for f in _FIELDS:
            if f in p and p[f] not in (None, ''):
                # Cast numerics safely
                v = p[f]
                if f in ('height', 'weight', 'shoulder', 'chest', 'waist',
                          'hip', 'arm_length', 'inseam', 'thigh',
                          'shoe_size_eu', 'shoe_size_us'):
                    try:
                        v = float(v) if v else 0
                    except (TypeError, ValueError):
                        continue
                # v2.1.49 — selection fields: alias-map then VALIDATE so a
                # wrong key can never crash the save with a 500.
                field = prof._fields.get(f)
                if field and field.type == 'selection':
                    v = aliases.get(f, {}).get(v, v)
                    allowed = [k for k, _lbl in
                               (field.selection or [])
                               ] if not callable(field.selection) else None
                    if allowed is not None and v not in allowed:
                        continue
                vals[f] = v
        if vals:
            # v2.1.54 — append a history snapshot of the NUMERIC values
            # that actually changed (newest first, capped at 20).
            try:
                import json as _json
                from datetime import datetime as _dt
                changed = {}
                for f, v in vals.items():
                    if isinstance(v, (int, float)) and \
                            float(prof[f] or 0) != float(v):
                        changed[f] = v
                if changed:
                    hist = []
                    if 'measure_history_json' in prof._fields:
                        try:
                            hist = _json.loads(
                                prof.measure_history_json or '[]')
                        except Exception:
                            hist = []
                        hist.insert(0, {
                            'date': _dt.now().strftime('%Y-%m-%d %H:%M'),
                            'values': changed,
                        })
                        vals['measure_history_json'] = _json.dumps(
                            hist[:20], ensure_ascii=False)
            except Exception:
                pass
            prof.sudo().write(vals)
        return ok({'profile': _to_dict(prof)})

    # ── Try-On (v2.1.50): Bearer-auth wrappers — the legacy /tryon/*
    # routes are Odoo-session JSON-RPC and always failed from the app. ──

    @http.route('/api/mobile/v2/tryon/photo', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def tryon_photo_save(self, **kw):
        """Persist the customer's try-on source photo on their body
        profile — uploaded ONCE, reused forever."""
        partner = current_partner()
        prof = _get_or_create_profile(partner)
        if prof is None:
            return fail('NO_MODULE', 'Smart Fit module not installed', 503)
        p = get_payload()
        b64 = (p.get('image_base64') or '').strip()
        if not b64:
            return fail('BAD_INPUT', 'image_base64 required')
        # Validate: real image bytes within the size cap (was stored raw,
        # letting a client persist arbitrary / huge blobs into the Binary
        # field). decode_image_upload returns clean bytes or an error.
        import base64 as _b64
        raw, err = decode_image_upload(b64)
        if err:
            return fail('BAD_IMAGE', err, 400)
        b64 = _b64.b64encode(raw).decode('ascii')
        vals = {}
        if 'tryon_photo' in prof._fields:
            vals['tryon_photo'] = b64
        if 'tryon_photo_filename' in prof._fields:
            vals['tryon_photo_filename'] = p.get('filename') or 'tryon.jpg'
        if 'tryon_photo_uploaded' in prof._fields:
            from datetime import datetime as _dt
            vals['tryon_photo_uploaded'] = _dt.now()
        if not vals:
            return fail('NO_FIELD', 'Profile has no photo storage', 503)
        prof.sudo().write(vals)
        return ok({'saved': True})

    @http.route('/api/mobile/v2/tryon/photo', type='http', auth='public',
                methods=['GET'], csrf=False)
    @safe_endpoint
    @require_auth
    def tryon_photo_get(self, **kw):
        """Return the saved source photo (base64) — or null."""
        partner = current_partner()
        prof = _get_or_create_profile(partner)
        if prof is None or 'tryon_photo' not in prof._fields \
                or not prof.tryon_photo:
            return ok({'photo': None})
        raw = prof.tryon_photo
        return ok({'photo': raw.decode() if isinstance(raw, bytes)
                   else str(raw)})

    @http.route('/api/mobile/v2/tryon/generate', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def tryon_generate(self, **kw):
        """Availability gate + generation kick-off. Until the AI provider
        (Replicate) is configured this returns available=False so the app
        shows a friendly coming-soon state instead of a raw error."""
        ICP = request.env['ir.config_parameter'].sudo()
        token = (ICP.get_param('uellow_ai.tryon_replicate_token')
                 or ICP.get_param('tryon_replicate_token') or '').strip()
        enabled = (ICP.get_param('uellow_ai.tryon_enabled')
                   or ICP.get_param('tryon_enabled') or '').strip()             in ('1', 'True', 'true')
        if not token or not enabled:
            return ok({'available': False, 'reason': 'coming_soon'})
        # v2.1.52 — run the generation with the BEARER partner + the SAME
        # profile our photo-save endpoint writes to. Delegating to the
        # session-auth controller used the PUBLIC user's empty profile,
        # which surfaced as the 'no_photo' error.
        try:
            from datetime import datetime as _dt
            from odoo.addons.uellow_smart_fit.controllers.tryon_controller \
                import TryOnController
            ctrl = TryOnController()
            partner = current_partner()
            p = get_payload()
            product_id = int(p.get('product_id') or 0)
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists():
                return ok({'available': True, 'error': 'product_not_found'})
            okc, reason, info = ctrl._product_eligible(product)
            if not okc:
                return ok({'available': True, 'error': reason, 'info': info})
            prof = _get_or_create_profile(partner)
            photo = getattr(prof, 'tryon_photo', False)
            if not photo:
                return ok({'available': True, 'error': 'no_photo'})
            okc, reason, info = ctrl._check_caps(partner)
            if not okc:
                return ok({'available': True, 'error': reason, 'info': info})
            if not product.image_1920:
                return ok({'available': True,
                           'error': 'product_image_missing'})
            human_url = ctrl._binary_to_data_url(photo)
            garment_url = ctrl._binary_to_data_url(product.image_1920)
            garment_des = product.name or 'clothing item'
            fashn_cat = ctrl._fashn_category(product)
            order = [ctrl._provider_primary()]
            fb = ctrl._provider_fallback()
            if fb != 'none' and fb not in order:
                order.append(fb)
            used = result = None
            last_err = None
            for prov in order:
                if not ctrl._provider_available(prov):
                    last_err = {'error': '%s_not_configured' % prov}
                    continue
                result = (ctrl._call_replicate(human_url, garment_url,
                                               garment_des)
                          if prov == 'replicate'
                          else ctrl._call_fashn(human_url, garment_url,
                                                fashn_cat))
                if result.get('success'):
                    used = prov
                    break
                last_err = result
            if not used:
                return ok(dict(last_err or {'error': 'all_providers_failed'},
                               available=True))
            Session = request.env['customer.tryon.session'].sudo()
            session = Session.create({
                'partner_id': partner.id,
                'product_id': product.id,
                'source_photo': photo,
                'source_photo_filename':
                    getattr(prof, 'tryon_photo_filename', '') or 'tryon.jpg',
                'status': 'running',
            })
            Image = request.env['customer.tryon.image'].sudo()
            image = Image.create({
                'session_id': session.id,
                'provider': used,
                'provider_model': result.get('model') or '',
                'provider_prediction_id': result['prediction_id'],
                'status': 'running',
                'cost_usd': ctrl._cost_per_call(used),
                'started_at': _dt.now(),
            })
            request.env.cr.commit()
            return ok({'available': True, 'success': True,
                       'image_id': image.id, 'provider': used,
                       'status': 'running'})
        except Exception as e:
            return fail('TRYON_ERROR', str(e), 500)

    @http.route('/api/mobile/v2/tryon/status/<int:image_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def tryon_status(self, image_id, **kw):
        """v2.1.52 — poll a generation. Marks the record done/failed and
        returns the output URL when ready."""
        from datetime import datetime as _dt
        from odoo.addons.uellow_smart_fit.controllers.tryon_controller \
            import TryOnController
        partner = current_partner()
        ctrl = TryOnController()
        Image = request.env['customer.tryon.image'].sudo()
        img = Image.browse(image_id)
        if not img.exists() or img.partner_id.id != partner.id:
            return fail('NOT_FOUND', 'Generation not found', 404)
        if img.status in ('done', 'failed'):
            return ok({'status': img.status,
                       'result_url': img.image_url or '',
                       'error': img.error_msg or ''})
        st = (ctrl._fetch_fashn_status(img.provider_prediction_id)
              if img.provider == 'fashn'
              else ctrl._fetch_replicate_status(img.provider_prediction_id))
        if not st.get('ok'):
            return ok({'status': 'running'})
        if st['status'] == 'done':
            out_url = st.get('output_url') or ''
            img_b64 = None
            try:
                import base64 as _b64
                import requests as _rq
                if out_url:
                    dl = _rq.get(out_url, timeout=60)
                    if dl.status_code == 200:
                        img_b64 = _b64.b64encode(dl.content)
            except Exception:
                pass
            img.write({'status': 'done', 'image_url': out_url or False,
                       'image': img_b64 or False,
                       'finished_at': _dt.now()})
            img.session_id.sudo().write({'status': 'done'})
            request.env.cr.commit()
            return ok({'status': 'done', 'result_url': out_url})
        if st['status'] == 'failed':
            img.write({'status': 'failed',
                       'error_msg': st.get('error') or ''})
            img.session_id.sudo().write({'status': 'failed'})
            request.env.cr.commit()
            return ok({'status': 'failed', 'error': st.get('error') or ''})
        return ok({'status': 'running'})

    @http.route('/api/mobile/v2/fit/recommend', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def recommend(self, **kw):
        """Wraps SmartFitController._analyze_fit with a clean HTTP shell."""
        p = get_payload()
        try:
            product_id = int(p.get('product_id') or 0)
        except (TypeError, ValueError):
            return fail('BAD_INPUT', 'product_id must be int')
        if not product_id:
            return fail('NO_PRODUCT', 'product_id is required')
        partner = current_partner()
        prof = _get_or_create_profile(partner)
        if prof is None or not getattr(prof, 'profile_complete', False):
            return ok({
                'recommended_size': None,
                'needs_profile':    True,
            })
        # Defer to SmartFitController logic if available
        try:
            from odoo.addons.uellow_smart_fit.controllers.fit_controller import \
                SmartFitController
            ctrl = SmartFitController()
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists():
                return fail('PRODUCT_NOT_FOUND', 'No such product', 404)
            sizes = ctrl._get_product_sizes(product)
            cat   = ctrl._detect_category(product)
            profile_data = _to_dict(prof)
            result = ctrl._analyze_fit(profile_data, sizes, cat)
            return ok({
                'recommended_size': (result or {}).get('recommended_size')
                                    or (result or {}).get('size'),
                'category':         cat,
                'details':          result or {},
            })
        except Exception as e:
            return fail('FIT_ERROR', str(e), 500)

    @http.route('/api/mobile/v2/fit/check', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def check(self, **kw):
        """v2.1.77 — rich per-area fit for the in-app body figure.
        Returns: profile (gender/body_type), and when a product is given,
        per-area fit (chest/waist/shoulder/hip/length/sleeve/inseam →
        tight | comfortable | loose), overall %, recommended size, and the
        full size ladder. Drives the painted body figure + bars + chips."""
        p = get_payload()
        partner = current_partner()
        prof = _get_or_create_profile(partner)
        prof_d = _to_dict(prof)
        complete = bool(prof and getattr(prof, 'profile_complete', False))
        base = {
            'has_profile': complete,
            'gender': prof_d.get('gender') or 'male',
            'body_type': prof_d.get('body_type') or 'regular',
            'preferred_fit': prof_d.get('preferred_fit') or 'regular',
            'completion_pct': prof_d.get('completion_pct') or 0,
            'profile': prof_d,
        }
        try:
            product_id = int(p.get('product_id') or 0)
        except (TypeError, ValueError):
            product_id = 0
        if not product_id or not complete:
            return ok({**base, 'state':
                       'ready' if complete else 'no_profile'})

        try:
            from odoo.addons.uellow_smart_fit.controllers.fit_controller import \
                SmartFitController
            ctrl = SmartFitController()
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists():
                return fail('PRODUCT_NOT_FOUND', 'No such product', 404)
            cat = ctrl._detect_category(product)
            sizes = ctrl._get_product_sizes(product)
            profile_data = _to_dict(prof)
            # _analyze_fit returns a ranked LIST of size dicts (size, score,
            # details{area:{status,diff}}, recommended, fit_label, fit_color).
            res = ctrl._analyze_fit(profile_data, sizes, cat) or []
            results = res if isinstance(res, list) else (res.get('results') or [])
            rec = next((r for r in results if r.get('recommended')),
                       results[0] if results else {})
            recommended = rec.get('size')
            details = rec.get('details') or {}
            # map raw status (perfect/ok/tight/loose/check/close/far) → buckets
            def bucket(st):
                st = (st or '').lower()
                if st in ('tight', 'small', 'too_small'): return 'tight'
                if st in ('loose', 'large', 'too_large'): return 'loose'
                if st in ('perfect', 'ok', 'comfortable', 'close'): return 'comfortable'
                return 'unknown'
            # per-area % for the figure bars (details carry no pct, derive it)
            def area_pct(info):
                if info.get('pct'):
                    return int(info['pct'])
                b = bucket(info.get('status'))
                return {'comfortable': 90, 'tight': 50, 'loose': 50}.get(b, 0)
            AR_LABELS = {
                'chest': 'الصدر', 'waist': 'الخصر', 'hip': 'الورك',
                'shoulder': 'الكتف', 'length': 'الطول', 'sleeve': 'الكم',
                'inseam': 'الساق', 'thigh': 'الفخذ', 'foot_length': 'القدم',
            }
            EN_LABELS = {
                'chest': 'Chest', 'waist': 'Waist', 'hip': 'Hip',
                'shoulder': 'Shoulder', 'length': 'Length', 'sleeve': 'Sleeve',
                'inseam': 'Inseam', 'thigh': 'Thigh', 'foot_length': 'Foot',
            }
            areas = []
            for key, info in details.items():
                if not isinstance(info, dict):
                    continue
                areas.append({
                    'key': key,
                    'label': {'en': EN_LABELS.get(key, key.title()),
                              'ar': AR_LABELS.get(key, key)},
                    'fit': bucket(info.get('status')),
                    'diff_cm': round(float(info.get('diff') or 0), 1),
                    'pct': area_pct(info),
                })
            ladder = [{
                'size': r.get('size'),
                'pct': int(r.get('score') or 0),
                'fit_label': r.get('fit_label') or '',
                'fit_color': r.get('fit_color') or 'yellow',
                'recommended': bool(r.get('recommended')),
            } for r in results]
            return ok({
                **base,
                'state': 'ready',
                'category': cat,
                'product': {'id': product.id,
                            'name': product.name or ''},
                'recommended_size': recommended,
                'overall_pct': int(rec.get('score') or 0),
                'areas': areas,
                'sizes': ladder,
            })
        except Exception as e:
            return fail('FIT_ERROR', str(e), 500)
