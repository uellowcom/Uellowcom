"""Try-On post-generation features: color swap, styling tips, save to wishlist,
PDF download, reviewer share, background swap, outfit composer, model compare.

Every feature checks its toggle in settings (uellow_ai.tryon_feat_*). When the
toggle is OFF the endpoint returns {'enabled': False}; the JS card hides the
corresponding button.
"""
import base64
import io
import json
import logging
from datetime import datetime

import requests

from odoo import http, _
from odoo.http import request

from odoo.addons.uellow_smart_fit.controllers.tryon_controller import (
    TryOnController, FASHN_API_BASE, FASHN_TIMEOUT, REPLICATE_TIMEOUT,
)

_logger = logging.getLogger(__name__)


def _t(en, ar):
    """Bilingual helper based on request lang."""
    lang = (request.env.context.get('lang') or 'en')[:2]
    return ar if lang == 'ar' else en


class TryOnExtrasController(TryOnController):
    """Inherits the base controller to share its helpers."""

    # ─────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────
    #
    # Defaults for each feature toggle — what we want enabled out of the
    # box. ir.config_parameter only gets written when the admin saves the
    # settings form, so until then we read these defaults.
    DEFAULT_FEAT = {
        'color_swap':        True,
        'styling_tips':      True,
        'save_wishlist':     True,
        'pdf_download':      True,
        'reviewer_opinion':  True,
        'background_swap':   False,
        'outfit_composer':   False,
        'compare_models':    False,
    }

    def _feat_enabled(self, key):
        default = 'True' if self.DEFAULT_FEAT.get(key, False) else 'False'
        return self._param(f'tryon_feat_{key}', default) in ('True', '1', 'true')

    @http.route('/tryon/features', type='json', auth='public', methods=['POST'], csrf=False)
    def features(self, **kw):
        """Return which post-generation buttons the JS card should render.
        Public — no PII leaked, just the toggle states."""
        return {
            'color_swap':       self._feat_enabled('color_swap'),
            'styling_tips':     self._feat_enabled('styling_tips'),
            'save_wishlist':    self._feat_enabled('save_wishlist'),
            'pdf_download':     self._feat_enabled('pdf_download'),
            'reviewer_opinion': self._feat_enabled('reviewer_opinion'),
            'background_swap':  self._feat_enabled('background_swap'),
            'outfit_composer':  self._feat_enabled('outfit_composer'),
            'compare_models':   self._feat_enabled('compare_models'),
        }

    def _require_image(self, image_id):
        partner = self._logged_in_partner()
        if not partner:
            return None, {'success': False, 'error': 'login_required'}
        image = request.env['customer.tryon.image'].sudo().browse(int(image_id))
        if not image.exists() or image.partner_id.id != partner.id:
            return None, {'success': False, 'error': 'not_found'}
        return image, None

    def _color_attribute_line(self, product):
        """Return the product's Color attribute line (or False)."""
        keywords = ['color', 'colour', 'لون']
        for line in product.attribute_line_ids:
            n = (line.attribute_id.name or '').lower()
            if any(kw in n for kw in keywords):
                return line
        return False

    def _color_attribute_values(self, product):
        line = self._color_attribute_line(product)
        if not line:
            return []
        return [{
            'id':    v.id,
            'name':  v.name,
            'html':  getattr(v, 'html_color', '') or '',
        } for v in line.value_ids]

    def _color_garment_image(self, product, color_attribute_value_id):
        """Return base64 garment image for a specific color, if a variant has
        its own image. Falls back to product.image_1920."""
        if not color_attribute_value_id:
            return product.image_1920
        ptav = product.attribute_line_ids.product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id.id == int(color_attribute_value_id)
        )
        if not ptav:
            return product.image_1920
        variant = product.product_variant_ids.filtered(
            lambda v: ptav in v.product_template_attribute_value_ids
        )
        v = variant[:1]
        if v and v.image_1920:
            return v.image_1920
        # Try product.image_variant_ids / product.image
        if v and getattr(v, 'image', False):
            return v.image
        return product.image_1920

    # ─────────────────────────────────────────────────────────────────────
    # Feature 1: Color swap
    # ─────────────────────────────────────────────────────────────────────
    @http.route('/tryon/colors/<int:image_id>', type='json', auth='user', methods=['POST'], csrf=False)
    def list_colors(self, image_id, **kw):
        if not self._feat_enabled('color_swap'):
            return {'enabled': False}
        image, err = self._require_image(image_id)
        if err:
            return err
        colors = self._color_attribute_values(image.product_id)
        return {'enabled': True, 'colors': colors}

    @http.route('/tryon/regenerate-color', type='json', auth='user', methods=['POST'], csrf=False)
    def regenerate_color(self, **kw):
        if not self._is_enabled():
            return {'success': False, 'error': 'tryon_disabled'}
        if not self._feat_enabled('color_swap'):
            return {'success': False, 'error': 'feature_disabled'}
        image_id = kw.get('image_id')
        color_id = kw.get('color_attribute_value_id')
        if not image_id or not color_id:
            return {'success': False, 'error': 'missing_params'}
        image, err = self._require_image(image_id)
        if err:
            return err

        partner = self._logged_in_partner()
        product = image.product_id
        profile = self._get_or_create_profile(partner)
        if not profile.tryon_photo:
            return {'success': False, 'error': 'no_photo'}

        # Caps still apply
        ok, reason, info = self._check_caps(partner)
        if not ok:
            return {'success': False, 'error': reason, 'info': info}

        garment_bin = self._color_garment_image(product, color_id)
        if not garment_bin:
            return {'success': False, 'error': 'product_image_missing'}

        human_url   = self._binary_to_data_url(profile.tryon_photo)
        garment_url = self._binary_to_data_url(garment_bin)
        if not human_url or not garment_url:
            return {'success': False, 'error': 'image_encoding_failed'}

        # Pick the active provider
        provider = self._provider_primary()
        if not self._provider_available(provider):
            provider = self._provider_fallback()
            if provider == 'none' or not self._provider_available(provider):
                return {'success': False, 'error': 'no_provider'}

        if provider == 'fashn':
            result = self._call_fashn(human_url, garment_url, self._fashn_category(product))
        else:
            result = self._call_replicate(human_url, garment_url, product.name or 'clothing')
        if not result.get('success'):
            return result

        # Resolve color name for storage
        color_name = ''
        av = request.env['product.attribute.value'].sudo().browse(int(color_id))
        if av.exists():
            color_name = av.name or ''

        Image = request.env['customer.tryon.image'].sudo()
        new_img = Image.create({
            'session_id':             image.session_id.id,
            'provider':               provider,
            'provider_model':         result.get('model') or '',
            'provider_prediction_id': result['prediction_id'],
            'color_text':             color_name,
            'status':                 'running',
            'cost_usd':               self._cost_per_call(provider),
            'started_at':             datetime.now(),
        })
        request.env.cr.commit()

        return {
            'success':       True,
            'image_id':      new_img.id,
            'prediction_id': result['prediction_id'],
            'provider':      provider,
            'color_name':    color_name,
            'status':        'running',
        }

    # ─────────────────────────────────────────────────────────────────────
    # Feature 2: AI styling tips + product recommendations
    # ─────────────────────────────────────────────────────────────────────
    @http.route('/tryon/styling-tips/<int:image_id>', type='json', auth='user', methods=['POST'], csrf=False)
    def styling_tips(self, image_id, **kw):
        if not self._feat_enabled('styling_tips'):
            return {'enabled': False}
        image, err = self._require_image(image_id)
        if err:
            return err

        product = image.product_id
        # Find category for the worn product
        from odoo.addons.uellow_smart_fit.controllers.fit_controller import SmartFitController
        category = SmartFitController()._detect_category(product)

        # Define complementary categories per worn category
        pair_map = {
            'shirt':   ['pants', 'jeans', 'shorts'],
            'tshirt':  ['pants', 'jeans', 'shorts'],
            'top':     ['pants', 'jeans', 'skirt', 'shorts'],
            'jacket':  ['pants', 'jeans'],
            'sweater': ['pants', 'jeans'],
            'hoodie':  ['pants', 'jeans'],
            'pants':   ['shirt', 'tshirt', 'top'],
            'jeans':   ['shirt', 'tshirt', 'top', 'sweater'],
            'shorts':  ['tshirt', 'top', 'shirt'],
            'dress':   ['shoe', 'sneaker', 'sandal'],
            'skirt':   ['top', 'tshirt', 'shirt'],
        }
        pair_cats = pair_map.get(category, ['shoe', 'sneaker'])

        # Fetch a handful of matching products from the catalog
        Product = request.env['product.template'].sudo()
        candidates = []
        for cat_kw in pair_cats:
            recs = Product.search([
                ('is_published', '=', True),
                ('id', '!=', product.id),
                '|', ('name', 'ilike', cat_kw),
                     ('categ_id.name', 'ilike', cat_kw),
            ], limit=3)
            candidates.extend(recs)
            if len(candidates) >= 6:
                break
        # Dedupe + pick 3
        seen = set()
        suggestions = []
        for p in candidates:
            if p.id in seen:
                continue
            seen.add(p.id)
            suggestions.append({
                'id':        p.id,
                'name':      p.name,
                'price_kd':  float(p.list_price or 0.0),
                'image_url': '/web/image/product.template/%s/image_256' % p.id,
                'url':       '/shop/product/%s' % p.id,
            })
            if len(suggestions) >= 3:
                break

        # Build a friendly tip text. We do NOT call Claude to keep cost predictable;
        # the suggestions list speaks for itself. The text is canned but tailored.
        product_name = product.name or ''
        tip_text = _t(
            f"For {product_name}, try pairing with one of these — they match the style.",
            f"يناسب {product_name} الإقتران مع أحد هذي القطع — تكامل الستايل.",
        )
        return {
            'enabled':    True,
            'tip':        tip_text,
            'suggestions': suggestions,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Feature 3: Save to wishlist with photo
    # ─────────────────────────────────────────────────────────────────────
    @http.route('/tryon/save-wishlist', type='json', auth='user', methods=['POST'], csrf=False)
    def save_wishlist(self, **kw):
        if not self._feat_enabled('save_wishlist'):
            return {'success': False, 'error': 'feature_disabled'}
        image_id = kw.get('image_id')
        image, err = self._require_image(image_id)
        if err:
            return err

        partner = self._logged_in_partner()
        product = image.product_id
        # Best variant id (default if no specific variant)
        variant = product.product_variant_id

        Wish = request.env['product.wishlist'].sudo()
        existing = Wish.search([
            ('partner_id', '=', partner.id),
            ('product_id', '=', variant.id),
        ], limit=1)
        if not existing:
            existing = Wish.create({
                'partner_id': partner.id,
                'product_id': variant.id,
                'website_id': request.env['website'].sudo().search([], limit=1).id,
                'pricelist_id': False,
                'currency_id': request.env.company.currency_id.id,
                'price':       variant.list_price,
            })

        # Attach the tryon image to the wishlist record via mail attachment
        try:
            if image.image:
                request.env['ir.attachment'].sudo().create({
                    'name':      f'tryon-{image.id}.png',
                    'res_model': 'product.wishlist',
                    'res_id':    existing.id,
                    'type':      'binary',
                    'datas':     image.image,
                    'mimetype':  'image/png',
                })
        except Exception as e:
            _logger.warning('attach tryon to wishlist failed: %s', e)

        return {
            'success':     True,
            'wishlist_id': existing.id,
            'wishlist_url': '/shop/wishlist',
            'message':     _t('Saved to your wishlist with the try-on photo ✓',
                              'تم الحفظ في قائمة الرغبات مع صورة التجربة ✓'),
        }

    # ─────────────────────────────────────────────────────────────────────
    # Feature 4: PDF download
    # ─────────────────────────────────────────────────────────────────────
    @http.route('/tryon/pdf/<int:image_id>', type='http', auth='user', csrf=False)
    def download_pdf(self, image_id, **kw):
        if not self._feat_enabled('pdf_download'):
            return request.not_found()
        image, err = self._require_image(image_id)
        if err:
            return request.not_found()
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
        except ImportError:
            return request.make_response('reportlab not installed', [('Content-Type','text/plain')], status=500)

        buf = io.BytesIO()
        c   = canvas.Canvas(buf, pagesize=A4)
        W, H = A4

        # Header bar
        c.setFillColor(colors.HexColor('#F5C320'))
        c.rect(0, H - 2.5*cm, W, 2.5*cm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor('#412402'))
        c.setFont('Helvetica-Bold', 22)
        c.drawString(2*cm, H - 1.6*cm, 'Uellow Virtual Try-On')

        # Image
        if image.image:
            try:
                img_data = base64.b64decode(image.image)
                from reportlab.lib.utils import ImageReader
                ir = ImageReader(io.BytesIO(img_data))
                iw, ih = ir.getSize()
                aspect = ih / float(iw) if iw else 1
                draw_w = W - 4*cm
                draw_h = draw_w * aspect
                if draw_h > H - 8*cm:
                    draw_h = H - 8*cm
                    draw_w = draw_h / aspect
                c.drawImage(ir, (W - draw_w)/2, H - 3*cm - draw_h, draw_w, draw_h)
            except Exception as e:
                _logger.warning('PDF image embed failed: %s', e)

        # Product info
        c.setFillColor(colors.HexColor('#1A1A1A'))
        c.setFont('Helvetica-Bold', 16)
        c.drawString(2*cm, 5.5*cm, image.product_id.name[:60] if image.product_id.name else '')
        c.setFont('Helvetica', 12)
        c.setFillColor(colors.HexColor('#854F0B'))
        c.drawString(2*cm, 4.6*cm, f'{image.product_id.list_price:.3f} KD')
        if image.color_text:
            c.setFillColor(colors.HexColor('#5F5E5A'))
            c.drawString(2*cm, 4.0*cm, f'Color: {image.color_text}')

        # Footer / watermark
        c.setFillColor(colors.HexColor('#BDB9B0'))
        c.setFont('Helvetica', 9)
        c.drawString(2*cm, 1.5*cm, 'Generated by Beena · uellow.com')
        c.drawRightString(W - 2*cm, 1.5*cm,
                          image.create_date.strftime('%Y-%m-%d %H:%M') if image.create_date else '')

        c.showPage()
        c.save()
        pdf = buf.getvalue()
        buf.close()
        return request.make_response(
            pdf,
            [('Content-Type', 'application/pdf'),
             ('Content-Disposition',
              f'attachment; filename="uellow-tryon-{image.id}.pdf"')],
        )

    # ─────────────────────────────────────────────────────────────────────
    # Feature 5: Share with a reviewer for opinion
    # ─────────────────────────────────────────────────────────────────────
    @http.route('/tryon/ask-reviewer', type='json', auth='user', methods=['POST'], csrf=False)
    def ask_reviewer(self, **kw):
        if not self._feat_enabled('reviewer_opinion'):
            return {'success': False, 'error': 'feature_disabled'}
        image_id = kw.get('image_id')
        image, err = self._require_image(image_id)
        if err:
            return err

        product = image.product_id
        # Find a category-matched approved reviewer (prefer online)
        Profile = request.env['reviewer.profile'].sudo()
        domain = [('state', '=', 'approved')]
        if product.categ_id:
            online_match = Profile.search(
                domain + [('is_online', '=', True),
                          ('specialty_ids', 'in', [product.categ_id.id])],
                limit=1, order='rating desc, review_count desc')
            if online_match:
                reviewer = online_match
            else:
                reviewer = Profile.search(
                    domain + [('specialty_ids', 'in', [product.categ_id.id])],
                    limit=1, order='rating desc, review_count desc')
        else:
            reviewer = False
        if not reviewer:
            reviewer = Profile.search(domain, limit=1, order='rating desc')

        if not reviewer:
            return {'success': False, 'error': 'no_reviewer_available'}

        # Create a review.request (if model exists)
        ReviewReq = request.env.get('review.request')
        if ReviewReq is None:
            return {'success': False, 'error': 'reviewer_module_missing'}
        partner = self._logged_in_partner()
        req_rec = ReviewReq.sudo().create({
            'product_id':  product.id,
            'customer_id': partner.id,
            'reviewer_id': reviewer.id,
            'kind':        'tryon_opinion',
            'state':       'pending',
            'note':        _t(
                f"Please give your opinion on this try-on of {product.name}.",
                f"شو رأيك بهذي التجربة على {product.name}؟",
            ),
        }) if 'kind' in ReviewReq._fields else ReviewReq.sudo().create({
            'product_id':  product.id,
            'customer_id': partner.id,
            'reviewer_id': reviewer.id,
            'state':       'pending',
        })

        # Attach the try-on image
        try:
            if image.image:
                request.env['ir.attachment'].sudo().create({
                    'name':      f'tryon-{image.id}.png',
                    'res_model': 'review.request',
                    'res_id':    req_rec.id,
                    'type':      'binary',
                    'datas':     image.image,
                    'mimetype':  'image/png',
                })
        except Exception as e:
            _logger.warning('attach tryon to review.request failed: %s', e)

        return {
            'success':     True,
            'reviewer_id': reviewer.id,
            'reviewer_name': reviewer.display_name,
            'avatar_url':  '/web/image/reviewer.profile/%d/avatar/64x64' % reviewer.id,
            'request_id':  req_rec.id,
            'message':     _t(
                f"Sent to {reviewer.display_name} — they'll respond shortly.",
                f"تم الإرسال لـ {reviewer.display_name} — راح يرد قريباً.",
            ),
        }

    # ─────────────────────────────────────────────────────────────────────
    # Feature 5b: Reviewer picker + group voting
    # ─────────────────────────────────────────────────────────────────────
    @http.route('/tryon/reviewers/list/<int:image_id>', type='json', auth='user', methods=['POST'], csrf=False)
    def list_reviewers(self, image_id, **kw):
        """Return reviewer cards for the customer to pick from. Prefers online
        + category-matched reviewers, with non-matched filling the list."""
        if not self._feat_enabled('reviewer_opinion'):
            return {'enabled': False}
        image, err = self._require_image(image_id)
        if err:
            return err

        product = image.product_id
        Profile = request.env['reviewer.profile'].sudo()
        domain = [('state', '=', 'approved')]
        ordered = []
        seen = set()

        def _add(recs):
            for r in recs:
                if r.id in seen:
                    continue
                seen.add(r.id)
                ordered.append(r)

        # 1) category-matched + online
        if product.categ_id:
            _add(Profile.search(
                domain + [('is_online', '=', True),
                          ('specialty_ids', 'in', [product.categ_id.id])],
                order='rating desc, review_count desc', limit=6))
            _add(Profile.search(
                domain + [('specialty_ids', 'in', [product.categ_id.id])],
                order='rating desc, review_count desc', limit=6))
        # 2) any online
        _add(Profile.search(domain + [('is_online', '=', True)],
                            order='rating desc, review_count desc', limit=8))
        # 3) any approved
        _add(Profile.search(domain, order='rating desc, review_count desc', limit=8))

        level_labels = {
            'elite':   {'en': '⭐⭐⭐⭐ Elite',   'ar': '⭐⭐⭐⭐ نخبة'},
            'expert':  {'en': '⭐⭐⭐ Expert',    'ar': '⭐⭐⭐ خبير'},
            'regular': {'en': '⭐⭐ Regular',    'ar': '⭐⭐ معتمد'},
            'starter': {'en': '⭐ Starter',     'ar': '⭐ مبتدئ'},
        }
        out = []
        for r in ordered[:8]:
            out.append({
                'id':            r.id,
                'name':          r.display_name or r.name or '?',
                'avatar_url':    '/web/image/reviewer.profile/%d/avatar/64x64' % r.id,
                'level':         r.level or 'starter',
                'level_label':   level_labels.get(r.level or 'starter', {}).get(
                    'ar' if (request.env.context.get('lang') or 'en').startswith('ar') else 'en',
                    ''),
                'rating':        round(r.rating or 0, 1),
                'review_count':  r.review_count or 0,
                'is_online':     bool(r.is_online),
                'specialty_text': r.specialty_text or '',
            })
        return {
            'enabled':   True,
            'reviewers': out,
            'product_name': product.name,
        }

    @http.route('/tryon/reviewers/ask', type='json', auth='user', methods=['POST'], csrf=False)
    def ask_reviewers_group(self, **kw):
        """Create one review.request per selected reviewer. Returns the list
        of created request ids so the JS can poll for results."""
        if not self._feat_enabled('reviewer_opinion'):
            return {'success': False, 'error': 'feature_disabled'}

        image, err = self._require_image(kw.get('image_id'))
        if err:
            return err

        reviewer_ids = kw.get('reviewer_ids') or []
        try:
            reviewer_ids = [int(x) for x in reviewer_ids if x]
        except Exception:
            return {'success': False, 'error': 'bad_reviewer_ids'}
        if not reviewer_ids:
            return {'success': False, 'error': 'no_reviewers_selected'}

        ReviewReq = request.env.get('review.request')
        if ReviewReq is None:
            return {'success': False, 'error': 'reviewer_module_missing'}

        partner = self._logged_in_partner()
        product = image.product_id

        # Use a single batch_token so JS can later poll the aggregate view
        import uuid
        batch_token = uuid.uuid4().hex

        created_ids = []
        for rid in reviewer_ids:
            vals = {
                'product_id':  product.id,
                'customer_id': partner.id,
                'reviewer_id': rid,
                'state':       'pending',
            }
            if 'kind' in ReviewReq._fields:
                vals['kind'] = 'tryon_opinion'
            if 'batch_token' in ReviewReq._fields:
                vals['batch_token'] = batch_token
            if 'tryon_image_id' in ReviewReq._fields:
                vals['tryon_image_id'] = image.id
            try:
                rec = ReviewReq.sudo().create(vals)
                # Attach the try-on image
                if image.image:
                    request.env['ir.attachment'].sudo().create({
                        'name':      f'tryon-{image.id}.png',
                        'res_model': 'review.request',
                        'res_id':    rec.id,
                        'type':      'binary',
                        'datas':     image.image,
                        'mimetype':  'image/png',
                    })
                created_ids.append(rec.id)
            except Exception as e:
                _logger.warning('group reviewer ask failed for %s: %s', rid, e)
                continue

        # Persist the batch_token on the image so we can find the votes
        try:
            image.sudo().write({'reviewer_batch_token': batch_token})
        except Exception:
            pass

        return {
            'success':       True,
            'request_ids':   created_ids,
            'batch_token':   batch_token,
            'reviewer_count': len(created_ids),
        }

    @http.route('/tryon/reviewers/votes/<int:image_id>', type='json', auth='user', methods=['POST'], csrf=False)
    def reviewer_votes(self, image_id, **kw):
        """Return aggregated vote results for an image. Counts recommend/not
        and lists each reviewer's individual response (or 'pending')."""
        image, err = self._require_image(image_id)
        if err:
            return err

        ReviewReq = request.env.get('review.request')
        if ReviewReq is None:
            return {'success': True, 'votes': [], 'recommend': 0, 'not_recommend': 0, 'pending': 0}

        token = getattr(image, 'reviewer_batch_token', '') or ''
        domain = []
        if token and 'batch_token' in ReviewReq._fields:
            domain.append(('batch_token', '=', token))
        elif 'tryon_image_id' in ReviewReq._fields:
            domain.append(('tryon_image_id', '=', image.id))
        else:
            partner = self._logged_in_partner()
            domain.extend([('customer_id', '=', partner.id),
                          ('product_id',  '=', image.product_id.id)])

        rows = ReviewReq.sudo().search(domain)
        votes = []
        rec_count = no_count = pending = 0
        for r in rows:
            verdict = getattr(r, 'reviewer_verdict', '') or ''
            note    = getattr(r, 'reviewer_note', '')    or ''
            state   = r.state if hasattr(r, 'state') else 'pending'
            if verdict == 'recommend':
                rec_count += 1
            elif verdict in ('dont_recommend', 'reject', 'no'):
                no_count += 1
            else:
                pending += 1
            votes.append({
                'reviewer_id':   r.reviewer_id.id if hasattr(r, 'reviewer_id') else 0,
                'reviewer_name': r.reviewer_id.display_name if hasattr(r, 'reviewer_id') and r.reviewer_id else '',
                'avatar_url':    ('/web/image/reviewer.profile/%d/avatar/64x64' % r.reviewer_id.id) if hasattr(r, 'reviewer_id') and r.reviewer_id else '',
                'verdict':       verdict or 'pending',
                'note':          note,
                'state':         state,
            })
        return {
            'success':       True,
            'votes':         votes,
            'recommend':     rec_count,
            'not_recommend': no_count,
            'pending':       pending,
            'total':         len(votes),
        }

    # ─────────────────────────────────────────────────────────────────────
    # Feature 6: Background swap (FASHN restore_background flag)
    # ─────────────────────────────────────────────────────────────────────
    BACKGROUND_PRESETS = {
        'studio':    {'restore_background': False, 'label': 'Studio'},
        'natural':   {'restore_background': True,  'label': 'Keep my background'},
    }

    @http.route('/tryon/backgrounds', type='json', auth='user', methods=['POST'], csrf=False)
    def list_backgrounds(self, **kw):
        if not self._feat_enabled('background_swap'):
            return {'enabled': False}
        return {
            'enabled': True,
            'presets': [{'key': k, 'label': _t(v['label'], v['label'])}
                        for k, v in self.BACKGROUND_PRESETS.items()],
        }

    @http.route('/tryon/regenerate-background', type='json', auth='user', methods=['POST'], csrf=False)
    def regenerate_background(self, **kw):
        if not self._is_enabled():
            return {'success': False, 'error': 'tryon_disabled'}
        if not self._feat_enabled('background_swap'):
            return {'success': False, 'error': 'feature_disabled'}
        image_id = kw.get('image_id')
        preset   = kw.get('preset', 'studio')
        image, err = self._require_image(image_id)
        if err:
            return err
        if preset not in self.BACKGROUND_PRESETS:
            return {'success': False, 'error': 'invalid_preset'}

        partner = self._logged_in_partner()
        product = image.product_id
        profile = self._get_or_create_profile(partner)
        if not profile.tryon_photo:
            return {'success': False, 'error': 'no_photo'}

        ok, reason, info = self._check_caps(partner)
        if not ok:
            return {'success': False, 'error': reason, 'info': info}

        human_url   = self._binary_to_data_url(profile.tryon_photo)
        garment_url = self._binary_to_data_url(product.image_1920)

        # Only FASHN supports the parameter; force it for this flow
        token = self._fashn_token()
        if not (self._fashn_enabled() and token):
            return {'success': False, 'error': 'fashn_required_for_background_swap'}

        cfg = self.BACKGROUND_PRESETS[preset]
        payload = {
            'model_name': self._fashn_model(),
            'inputs': {
                'model_image':         human_url,
                'garment_image':       garment_url,
                'category':            self._fashn_category(product),
                'restore_background':  cfg['restore_background'],
            },
        }
        try:
            resp = requests.post(
                f'{FASHN_API_BASE}/run',
                headers={'Authorization': f'Bearer {token}',
                         'Content-Type':  'application/json'},
                json=payload, timeout=FASHN_TIMEOUT,
            )
        except requests.RequestException as e:
            return {'success': False, 'error': 'fashn_unreachable', 'detail': str(e)}
        if resp.status_code not in (200, 201, 202):
            return {'success': False, 'error': 'fashn_error',
                    'detail': resp.text[:300]}
        data = resp.json()
        if data.get('error') or not data.get('id'):
            return {'success': False, 'error': 'no_prediction_id',
                    'detail': str(data)[:300]}

        new_img = request.env['customer.tryon.image'].sudo().create({
            'session_id':             image.session_id.id,
            'provider':               'fashn',
            'provider_model':         self._fashn_model(),
            'provider_prediction_id': data['id'],
            'color_text':             f'BG: {cfg["label"]}',
            'status':                 'running',
            'cost_usd':               self._cost_per_call('fashn'),
            'started_at':             datetime.now(),
        })
        request.env.cr.commit()
        return {'success': True, 'image_id': new_img.id, 'prediction_id': data['id']}

    # ─────────────────────────────────────────────────────────────────────
    # Feature 7: Outfit composer (multi-product)
    # ─────────────────────────────────────────────────────────────────────
    @http.route('/tryon/compose-outfit', type='json', auth='user', methods=['POST'], csrf=False)
    def compose_outfit(self, **kw):
        """Sequentially layer 2-3 garments: result of step N becomes the
        model_image for step N+1. Returns the first prediction; client polls."""
        if not self._is_enabled():
            return {'success': False, 'error': 'tryon_disabled'}
        if not self._feat_enabled('outfit_composer'):
            return {'success': False, 'error': 'feature_disabled'}
        partner = self._logged_in_partner()
        if not partner:
            return {'success': False, 'error': 'login_required'}
        product_ids = kw.get('product_ids') or []
        if not isinstance(product_ids, list) or not product_ids:
            return {'success': False, 'error': 'no_products'}
        # Cap at 3 to bound cost
        product_ids = [int(x) for x in product_ids[:3]]

        # Eligibility gate — same as single generate(). Every garment must be an
        # eligible fashion item (category + min price); otherwise we'd burn
        # provider cost on ineligible SKUs (electronics, etc.).
        Product = request.env['product.template'].sudo()
        for pid in product_ids:
            p = Product.browse(pid)
            if not p.exists():
                return {'success': False, 'error': 'product_not_found', 'info': {'product_id': pid}}
            ok, reason, info = self._product_eligible(p)
            if not ok:
                return {'success': False, 'error': reason, 'info': info}

        profile = self._get_or_create_profile(partner)
        if not profile.tryon_photo:
            return {'success': False, 'error': 'no_photo'}

        # Caps check (we'll consume N generations)
        for _ in product_ids:
            ok, reason, info = self._check_caps(partner)
            if not ok:
                return {'success': False, 'error': reason, 'info': info}

        token = self._fashn_token()
        if not (self._fashn_enabled() and token):
            return {'success': False, 'error': 'fashn_required'}

        Session = request.env['customer.tryon.session'].sudo()
        Image   = request.env['customer.tryon.image'].sudo()

        # Create one session; one image per layer
        session = Session.create({
            'partner_id':            partner.id,
            'product_id':            product_ids[0],
            'source_photo':          profile.tryon_photo,
            'source_photo_filename': profile.tryon_photo_filename,
            'status':                'running',
        })

        # We only kick off the FIRST step. The status endpoint will chain
        # subsequent ones once each completes. To make this scalable we'd
        # need a cron / queue; for MVP we kick step 1 here and return.
        # Future steps are encoded in session.notes as JSON.
        product0 = request.env['product.template'].sudo().browse(product_ids[0])
        if not product0.exists() or not product0.image_1920:
            return {'success': False, 'error': 'product0_missing'}

        human_url   = self._binary_to_data_url(profile.tryon_photo)
        garment_url = self._binary_to_data_url(product0.image_1920)

        try:
            resp = requests.post(
                f'{FASHN_API_BASE}/run',
                headers={'Authorization': f'Bearer {token}',
                         'Content-Type':  'application/json'},
                json={
                    'model_name': self._fashn_model(),
                    'inputs': {
                        'model_image':   human_url,
                        'garment_image': garment_url,
                        'category':      self._fashn_category(product0),
                    },
                },
                timeout=FASHN_TIMEOUT,
            )
        except requests.RequestException as e:
            return {'success': False, 'error': 'fashn_unreachable', 'detail': str(e)}
        if resp.status_code not in (200, 201, 202) or not resp.json().get('id'):
            return {'success': False, 'error': 'fashn_error', 'detail': resp.text[:300]}
        pred_id = resp.json()['id']

        first_img = Image.create({
            'session_id':             session.id,
            'provider':               'fashn',
            'provider_model':         self._fashn_model(),
            'provider_prediction_id': pred_id,
            'status':                 'running',
            'cost_usd':               self._cost_per_call('fashn'),
            'started_at':             datetime.now(),
        })
        # Persist the remaining steps onto the session for the status worker
        # to pick up. (For now, the client polls status, finds 'done', and
        # calls a "next layer" endpoint.)
        remaining = product_ids[1:]
        request.env.cr.commit()
        return {
            'success':     True,
            'session_id':  session.id,
            'image_id':    first_img.id,
            'remaining':   remaining,
            'step':        1,
            'total_steps': len(product_ids),
        }

    @http.route('/tryon/compose-outfit/next', type='json', auth='user', methods=['POST'], csrf=False)
    def compose_next(self, **kw):
        """Layer the next product on top of a completed previous step."""
        if not self._is_enabled():
            return {'success': False, 'error': 'tryon_disabled'}
        if not self._feat_enabled('outfit_composer'):
            return {'success': False, 'error': 'feature_disabled'}
        partner   = self._logged_in_partner()
        session_id = kw.get('session_id')
        prev_image_id = kw.get('previous_image_id')
        next_product_id = kw.get('next_product_id')
        if not (partner and session_id and prev_image_id and next_product_id):
            return {'success': False, 'error': 'missing_params'}

        Image = request.env['customer.tryon.image'].sudo()
        prev = Image.browse(int(prev_image_id))
        if not prev.exists() or prev.partner_id.id != partner.id or prev.status != 'done':
            return {'success': False, 'error': 'previous_not_ready'}
        if not prev.image:
            return {'success': False, 'error': 'previous_image_missing'}
        # SECURITY: session_id is client-supplied — the new generation (and its
        # cost) must land in the CALLER's own session, not a victim's.
        session = request.env['customer.tryon.session'].sudo().browse(int(session_id))
        if not session.exists() or session.partner_id.id != partner.id:
            return {'success': False, 'error': 'session_not_owned'}

        nxt_product = request.env['product.template'].sudo().browse(int(next_product_id))
        if not nxt_product.exists() or not nxt_product.image_1920:
            return {'success': False, 'error': 'next_product_missing'}
        # Eligibility gate — the next layer must also be an eligible fashion item.
        ok, reason, info = self._product_eligible(nxt_product)
        if not ok:
            return {'success': False, 'error': reason, 'info': info}

        token = self._fashn_token()
        if not (self._fashn_enabled() and token):
            return {'success': False, 'error': 'fashn_required'}

        # Cost caps apply to EVERY layer. Each compose-next call fires a fresh
        # paid FASHN generation; without this gate the outfit composer's "next"
        # endpoint would bypass the monthly USD / monthly-count / daily-per-
        # customer caps that generate() and every other generator enforce.
        ok, reason, info = self._check_caps(partner)
        if not ok:
            return {'success': False, 'error': reason, 'info': info}

        # Use the previous result as the new model image
        human_url   = self._binary_to_data_url(prev.image)
        garment_url = self._binary_to_data_url(nxt_product.image_1920)
        try:
            resp = requests.post(
                f'{FASHN_API_BASE}/run',
                headers={'Authorization': f'Bearer {token}',
                         'Content-Type':  'application/json'},
                json={
                    'model_name': self._fashn_model(),
                    'inputs': {
                        'model_image':   human_url,
                        'garment_image': garment_url,
                        'category':      self._fashn_category(nxt_product),
                    },
                },
                timeout=FASHN_TIMEOUT,
            )
        except requests.RequestException as e:
            return {'success': False, 'error': 'fashn_unreachable', 'detail': str(e)}
        if resp.status_code not in (200, 201, 202) or not resp.json().get('id'):
            return {'success': False, 'error': 'fashn_error', 'detail': resp.text[:300]}
        pred_id = resp.json()['id']

        new_img = Image.create({
            'session_id':             int(session_id),
            'provider':               'fashn',
            'provider_model':         self._fashn_model(),
            'provider_prediction_id': pred_id,
            'color_text':             f'Layer: {nxt_product.name[:40]}',
            'status':                 'running',
            'cost_usd':               self._cost_per_call('fashn'),
            'started_at':             datetime.now(),
        })
        request.env.cr.commit()
        return {'success': True, 'image_id': new_img.id, 'prediction_id': pred_id}

    # ─────────────────────────────────────────────────────────────────────
    # Feature 8: Model comparison (alt FASHN model)
    # ─────────────────────────────────────────────────────────────────────
    @http.route('/tryon/compare-models', type='json', auth='user', methods=['POST'], csrf=False)
    def compare_models(self, **kw):
        if not self._is_enabled():
            return {'success': False, 'error': 'tryon_disabled'}
        if not self._feat_enabled('compare_models'):
            return {'success': False, 'error': 'feature_disabled'}
        image_id = kw.get('image_id')
        image, err = self._require_image(image_id)
        if err:
            return err

        partner = self._logged_in_partner()
        product = image.product_id
        profile = self._get_or_create_profile(partner)
        if not profile.tryon_photo:
            return {'success': False, 'error': 'no_photo'}

        # Pick the alternate FASHN model
        current = (image.provider_model or self._fashn_model()).strip()
        alt = 'tryon-v1' if 'v1.5' in current else 'tryon-v1.5'

        token = self._fashn_token()
        if not (self._fashn_enabled() and token):
            return {'success': False, 'error': 'fashn_required'}

        ok, reason, info = self._check_caps(partner)
        if not ok:
            return {'success': False, 'error': reason, 'info': info}

        human_url   = self._binary_to_data_url(profile.tryon_photo)
        garment_url = self._binary_to_data_url(product.image_1920)
        try:
            resp = requests.post(
                f'{FASHN_API_BASE}/run',
                headers={'Authorization': f'Bearer {token}',
                         'Content-Type':  'application/json'},
                json={
                    'model_name': alt,
                    'inputs': {
                        'model_image':   human_url,
                        'garment_image': garment_url,
                        'category':      self._fashn_category(product),
                    },
                },
                timeout=FASHN_TIMEOUT,
            )
        except requests.RequestException as e:
            return {'success': False, 'error': 'fashn_unreachable', 'detail': str(e)}
        if resp.status_code not in (200, 201, 202) or not resp.json().get('id'):
            return {'success': False, 'error': 'fashn_error', 'detail': resp.text[:300]}
        pred_id = resp.json()['id']

        new_img = request.env['customer.tryon.image'].sudo().create({
            'session_id':             image.session_id.id,
            'provider':               'fashn',
            'provider_model':         alt,
            'provider_prediction_id': pred_id,
            'color_text':             f'Compare: {alt}',
            'status':                 'running',
            'cost_usd':               self._cost_per_call('fashn'),
            'started_at':             datetime.now(),
        })
        request.env.cr.commit()
        return {'success': True, 'image_id': new_img.id, 'alt_model': alt,
                'original_model': current}
