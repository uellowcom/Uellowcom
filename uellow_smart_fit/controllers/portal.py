from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64
import logging

_logger = logging.getLogger(__name__)


class SmartFitPortal(CustomerPortal):
    """Portal pages for body measurements, personal photos, and try-on history."""

    # ── Counters injected into portal_my_home ───────────────────────────
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'tryon_count' in counters:
            values['tryon_count'] = request.env['customer.tryon.session'].sudo().search_count(
                [('partner_id', '=', partner.id)]
            )
        if 'measurements_pct' in counters:
            profile = request.env['customer.body.profile'].sudo().search(
                [('partner_id', '=', partner.id)], limit=1)
            values['measurements_pct'] = int(profile.completion_pct or 0) if profile else 0
        return values

    # ── Body measurements page ─────────────────────────────────────────
    @http.route(['/my/measurements'], type='http', auth='user', website=True)
    def my_measurements(self, **kw):
        partner = request.env.user.partner_id
        Profile = request.env['customer.body.profile'].sudo()
        profile = Profile.search([('partner_id', '=', partner.id)], limit=1)
        if not profile:
            profile = Profile.create({'partner_id': partner.id})
        return request.render('uellow_smart_fit.portal_my_measurements', {
            'profile': profile,
            'partner': partner,
            'page_name': 'measurements',
        })

    @http.route(['/my/measurements/save'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def my_measurements_save(self, **post):
        partner = request.env.user.partner_id
        Profile = request.env['customer.body.profile'].sudo()
        profile = Profile.search([('partner_id', '=', partner.id)], limit=1)
        if not profile:
            profile = Profile.create({'partner_id': partner.id})

        def _f(name):
            v = (post.get(name) or '').strip()
            try:
                return float(v) if v else False
            except Exception:
                return False

        def _sel(name):
            """Return value only if it's a valid option for that Selection field."""
            v = (post.get(name) or '').strip()
            if not v:
                return False
            field = Profile._fields.get(name)
            if not field or field.type != 'selection':
                return False
            allowed = [opt[0] for opt in field.selection]
            return v if v in allowed else False

        vals = {
            'height': _f('height'), 'weight': _f('weight'),
            'shoulder': _f('shoulder'), 'chest': _f('chest'),
            'waist': _f('waist'), 'hip': _f('hip'),
            'arm_length': _f('arm_length'), 'inseam': _f('inseam'),
            'thigh': _f('thigh'),
            'shoe_size_eu': _f('shoe_size_eu'), 'shoe_size_us': _f('shoe_size_us'),
            'foot_length_cm': _f('foot_length_cm'),
            'body_type':     _sel('body_type'),
            'gender':        _sel('gender'),
            'age_range':     _sel('age_range'),
            'shoe_width':    _sel('shoe_width'),
            'preferred_fit': _sel('preferred_fit'),
            'preferred_unit': _sel('preferred_unit'),
        }
        vals = {k: v for k, v in vals.items() if v is not False}
        try:
            profile.write(vals)
        except Exception as e:
            _logger.warning('measurements save failed: %s | vals=%s', e, vals)
            return request.redirect('/my/measurements?error=1')
        return request.redirect('/my/measurements?saved=1')

    # ── Personal photos page (try-on source photo) ─────────────────────
    @http.route(['/my/photos'], type='http', auth='user', website=True)
    def my_photos(self, **kw):
        partner = request.env.user.partner_id
        Profile = request.env['customer.body.profile'].sudo()
        profile = Profile.search([('partner_id', '=', partner.id)], limit=1)
        if not profile:
            profile = Profile.create({'partner_id': partner.id})
        photo_url = ('/web/image/customer.body.profile/%d/tryon_photo' % profile.id) if profile.tryon_photo else ''
        return request.render('uellow_smart_fit.portal_my_photos', {
            'profile': profile,
            'partner': partner,
            'photo_url': photo_url,
            'page_name': 'photos',
        })

    @http.route(['/my/photos/upload'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def my_photos_upload(self, **post):
        partner = request.env.user.partner_id
        Profile = request.env['customer.body.profile'].sudo()
        profile = Profile.search([('partner_id', '=', partner.id)], limit=1)
        if not profile:
            profile = Profile.create({'partner_id': partner.id})

        uploaded = post.get('photo')
        if uploaded and hasattr(uploaded, 'read'):
            data = uploaded.read()
            if data:
                # Same validation as the JSON /tryon/upload-photo path: reject
                # non-image bytes and oversized files so garbage never lands in
                # tryon_photo (which is later shipped to the paid provider).
                from odoo.addons.uellow_smart_fit.controllers.tryon_controller import TryOnController
                validator = TryOnController()
                if len(data) > TryOnController._MAX_PHOTO_BYTES:
                    return request.redirect('/my/photos?error=too_large')
                if not validator._looks_like_image(data):
                    return request.redirect('/my/photos?error=invalid')
                from datetime import datetime
                profile.write({
                    'tryon_photo': base64.b64encode(data),
                    'tryon_photo_filename': uploaded.filename,
                    'tryon_photo_uploaded': datetime.now(),
                })
        return request.redirect('/my/photos?saved=1')

    @http.route(['/my/photos/delete'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def my_photos_delete(self, **post):
        partner = request.env.user.partner_id
        profile = request.env['customer.body.profile'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1)
        if profile:
            profile.write({
                'tryon_photo': False,
                'tryon_photo_filename': False,
                'tryon_photo_uploaded': False,
            })
        return request.redirect('/my/photos?deleted=1')

    # ── Fit-check history page ─────────────────────────────────────────
    @http.route(['/my/fit-history'], type='http', auth='user', website=True)
    def my_fit_history(self, **kw):
        partner = request.env.user.partner_id
        history = request.env['customer.fit.history'].sudo().search(
            [('partner_id', '=', partner.id)],
            order='create_date desc', limit=100,
        )
        return request.render('uellow_smart_fit.portal_my_fit_history', {
            'history': history,
            'partner': partner,
            'page_name': 'fit_history',
        })

    @http.route(['/my/fit-history/<int:check_id>'], type='http', auth='user', website=True)
    def my_fit_history_detail(self, check_id, **kw):
        partner = request.env.user.partner_id
        rec = request.env['customer.fit.history'].sudo().browse(check_id)
        if not rec.exists() or rec.partner_id.id != partner.id:
            return request.redirect('/my/fit-history')
        # Parse the details snapshot
        import json as _json
        try:
            details = _json.loads(rec.details_json or '{}')
        except Exception:
            details = {}
        return request.render('uellow_smart_fit.portal_fit_history_detail', {
            'check': rec,
            'details': details,
            'page_name': 'fit_history',
        })

    # ── Try-On history page ────────────────────────────────────────────
    @http.route(['/my/tryon-history'], type='http', auth='user', website=True)
    def my_tryon_history(self, **kw):
        partner = request.env.user.partner_id
        sessions = request.env['customer.tryon.session'].sudo().search(
            [('partner_id', '=', partner.id)], order='create_date desc', limit=50)
        return request.render('uellow_smart_fit.portal_my_tryon_history', {
            'sessions': sessions,
            'partner': partner,
            'page_name': 'tryon_history',
        })
