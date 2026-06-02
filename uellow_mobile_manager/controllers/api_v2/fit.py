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
    prof = BP.sudo().search([('partner_id', '=', partner.id)], limit=1)
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
                vals[f] = v
        if vals:
            prof.sudo().write(vals)
        return ok({'profile': _to_dict(prof)})

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
