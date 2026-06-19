# -*- coding: utf-8 -*-
"""Vendor marketing & ops — sponsored listings + order disputes (app side)."""
from datetime import datetime

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_vendor, fmt_price,
    img_url,
)

REASONS = [
    ('out_of_stock', 'Out of stock', 'نفاد المخزون'),
    ('customer_unreachable', 'Customer unreachable', 'تعذّر الوصول للعميل'),
    ('damaged', 'Item damaged', 'تلف المنتج'),
    ('wrong_item', 'Wrong item', 'منتج خاطئ'),
    ('not_received', 'Not received', 'لم يصل'),
    ('return_request', 'Customer return request', 'طلب استرجاع'),
    ('other', 'Other', 'أخرى'),
]


_AD_FORMATS = {
    'product_boost': {'en': 'Product boost', 'ar': 'إبراز منتج'},
    'banner':        {'en': 'Banner ad',     'ar': 'إعلان بانر'},
    'infeed':        {'en': 'In-feed card',  'ar': 'بطاقة ضمن القائمة'},
}
_AD_PLACEMENTS = {
    'home':     {'en': 'Home',     'ar': 'الرئيسية'},
    'category': {'en': 'Category', 'ar': 'القسم'},
    'search':   {'en': 'Search',   'ar': 'البحث'},
    'all':      {'en': 'Everywhere', 'ar': 'كل الأماكن'},
}


def _ser_ad(c):
    return {
        'id': c.id, 'name': c.name,
        'product_id': c.product_tmpl_id.id if c.product_tmpl_id else 0,
        'product': c.product_tmpl_id.name if c.product_tmpl_id else '',
        'ad_format': c.ad_format,
        'ad_format_label': _AD_FORMATS.get(c.ad_format, {'en': c.ad_format, 'ar': c.ad_format}),
        'placement': c.placement,
        'placement_label': _AD_PLACEMENTS.get(c.placement, {'en': c.placement, 'ar': c.placement}),
        'headline': c.headline or '',
        'has_banner': bool(c.banner_image),
        'start': c.start_date.isoformat() if c.start_date else '',
        'end': c.end_date.isoformat() if c.end_date else '',
        'days': c.days, 'daily_rate': c.daily_rate, 'total_cost': c.total_cost,
        'state': c.state, 'impressions': c.impressions, 'clicks': c.clicks,
    }


_DISPUTE_REASONS = {
    'out_of_stock':        {'en': 'Out of stock',            'ar': 'نفاد المخزون'},
    'customer_unreachable':{'en': 'Customer unreachable',    'ar': 'تعذّر الوصول للعميل'},
    'damaged':             {'en': 'Item damaged',            'ar': 'المنتج تالف'},
    'wrong_item':          {'en': 'Wrong item',              'ar': 'منتج خاطئ'},
    'not_received':        {'en': 'Not received',            'ar': 'لم يُستلم'},
    'return_request':      {'en': 'Customer return request', 'ar': 'طلب إرجاع من العميل'},
    'other':               {'en': 'Other',                   'ar': 'أخرى'},
}
_DISPUTE_STATES = {
    'open':      {'en': 'Open',      'ar': 'مفتوح'},
    'in_review': {'en': 'In review', 'ar': 'قيد المراجعة'},
    'resolved':  {'en': 'Resolved',  'ar': 'تم الحل'},
    'rejected':  {'en': 'Rejected',  'ar': 'مرفوض'},
}


def _ser_dispute(d):
    return {
        'id': d.id, 'name': d.name, 'order_id': d.order_id.id,
        'order': d.order_id.name, 'customer': d.partner_id.name or '',
        'reason': d.reason, 'reason_label': _DISPUTE_REASONS.get(d.reason, {'en': d.reason, 'ar': d.reason}),
        'state': d.state, 'state_label': _DISPUTE_STATES.get(d.state, {'en': d.state, 'ar': d.state}),
        'description': d.description or '', 'resolution': d.resolution or '',
        'when': d.create_date.isoformat() if d.create_date else '',
    }


class VendorMarketingController(http.Controller):

    # ══ SPONSORED LISTINGS ═══════════════════════════════════════
    @http.route('/api/vendor/v1/ads', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_ads(self, **kw):
        v = current_vendor()
        rate = float(request.env['ir.config_parameter'].sudo().get_param(
            'uellow.vendor_api.ad_daily_rate', '1.0') or 1.0)
        ads = request.env['vendor.ad.campaign'].sudo().search([('vendor_id', '=', v.id)])
        return ok({
            'campaigns': [_ser_ad(c) for c in ads],
            'daily_rate': rate,
            'wallet_balance': v.wallet_id.balance if v.wallet_id else 0.0,
        })

    @http.route('/api/vendor/v1/ads/<int:cid>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def ad_detail(self, cid, **kw):
        """Openable sponsored-ad record: full config + live performance."""
        v = current_vendor()
        c = request.env['vendor.ad.campaign'].sudo().browse(cid)
        if not c.exists() or c.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Campaign not found', 404)
        imp = c.impressions or 0
        clk = c.clicks or 0
        out = _ser_ad(c)
        out.update({
            'ctr': round((clk / imp * 100), 2) if imp else 0.0,
            'cpc': round((c.total_cost / clk), 3) if clk else 0.0,
            'product_image': (img_url('product.template', c.product_tmpl_id.id,
                                      'image_256', unique=c.product_tmpl_id.write_date)
                              if c.product_tmpl_id and c.product_tmpl_id.image_256 else None),
            'banner_url': (img_url('vendor.ad.campaign', c.id, 'banner_image',
                                   unique=c.write_date) if c.banner_image else None),
        })
        return ok(out)

    @http.route('/api/vendor/v1/ads/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_ad(self, **kw):
        v = current_vendor()
        p = get_payload()
        ad_format = p.get('ad_format') if p.get('ad_format') in _AD_FORMATS else 'product_boost'
        placement = p.get('placement') if p.get('placement') in _AD_PLACEMENTS else 'home'
        # Product is required for product_boost; optional for banner/infeed.
        t = None
        if p.get('product_id'):
            try:
                t = request.env['product.template'].sudo().browse(int(p['product_id']))
            except (TypeError, ValueError):
                t = None
            if not t or not t.exists() or t.vendor_id.id != v.id:
                return fail('NOT_FOUND', 'Product not found', 404)
        if ad_format == 'product_boost' and not t:
            return fail('BAD_PRODUCT', 'product_id required for product boost')
        try:
            start = datetime.strptime(p.get('start'), '%Y-%m-%d').date()
            end = datetime.strptime(p.get('end'), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return fail('BAD_DATE', 'start and end (YYYY-MM-DD) required')
        if end < start:
            return fail('BAD_RANGE', 'end must be on/after start')
        vals = {
            'name': p.get('name') or ('Sponsored: %s' % (t.name if t else ad_format)),
            'vendor_id': v.id,
            'product_tmpl_id': t.id if t else False,
            'ad_format': ad_format, 'placement': placement,
            'headline': (p.get('headline') or '').strip(),
            'start_date': start, 'end_date': end,
        }
        if p.get('banner_base64'):
            try:
                vals['banner_image'] = p['banner_base64'].split(',', 1)[-1]
            except Exception:
                pass
        if ad_format in ('banner', 'infeed') and not (vals.get('banner_image') or t):
            return fail('NO_CREATIVE', 'Add a banner image or pick a product.')
        camp = request.env['vendor.ad.campaign'].sudo().create(vals)
        try:
            camp.action_activate()
        except Exception as e:
            camp.unlink()
            return fail('CHARGE_FAILED', str(e))
        return ok(_ser_ad(camp))

    @http.route('/api/vendor/v1/ads/quote', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def ad_quote(self, **kw):
        """Daily rate per format so the app can preview cost before paying."""
        current_vendor()
        Camp = request.env['vendor.ad.campaign'].sudo()
        rates = {}
        for fmt in _AD_FORMATS:
            rates[fmt] = Camp.new({'ad_format': fmt})._quote_rate()
        return ok({'rates': rates, 'formats': [{'code': c, **lbl} for c, lbl in _AD_FORMATS.items()],
                   'placements': [{'code': c, **lbl} for c, lbl in _AD_PLACEMENTS.items()]})

    @http.route('/api/vendor/v1/ads/<int:cid>/cancel', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def cancel_ad(self, cid, **kw):
        v = current_vendor()
        c = request.env['vendor.ad.campaign'].sudo().browse(cid)
        if not c.exists() or c.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Campaign not found', 404)
        c.action_cancel()
        return ok(_ser_ad(c))

    # ══ ORDER DISPUTES / ISSUES ══════════════════════════════════
    @http.route('/api/vendor/v1/disputes', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_disputes(self, **kw):
        v = current_vendor()
        ds = request.env['vendor.order.dispute'].sudo().search([('vendor_id', '=', v.id)])
        return ok({
            'disputes': [_ser_dispute(d) for d in ds],
            'reasons': [{'code': c, 'en': en, 'ar': ar} for c, en, ar in REASONS],
        })

    @http.route('/api/vendor/v1/disputes/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_dispute(self, **kw):
        v = current_vendor()
        p = get_payload()
        try:
            oid = int(p.get('order_id'))
        except (TypeError, ValueError):
            return fail('BAD_ORDER', 'order_id required')
        o = request.env['sale.order'].sudo().browse(oid)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        reason = p.get('reason')
        if reason not in {c for c, _e, _a in REASONS}:
            reason = 'other'
        d = request.env['vendor.order.dispute'].sudo().create({
            'vendor_id': v.id, 'order_id': o.id, 'reason': reason,
            'description': (p.get('description') or '').strip(),
        })
        return ok(_ser_dispute(d))

    @http.route('/api/vendor/v1/disputes/<int:did>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def dispute_detail(self, did, **kw):
        v = current_vendor()
        d = request.env['vendor.order.dispute'].sudo().browse(did)
        if not d.exists() or d.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Dispute not found', 404)
        data = _ser_dispute(d)
        o = d.order_id
        data['order_detail'] = {
            'id': o.id, 'name': o.name, 'state': o.state,
            'amount': fmt_price(o.amount_total, o.currency_id),
            'item_count': len(o.order_line.filtered(lambda l: not l.display_type)),
            'when': (o.date_order or o.create_date).isoformat()
                    if (o.date_order or o.create_date) else '',
        }
        # Message / status timeline from the chatter.
        msgs = d.message_ids.sorted('id')
        data['timeline'] = [{
            'id': m.id,
            'body': (m.body or '').strip(),
            'author': m.author_id.name or 'System',
            'when': m.date.isoformat() if m.date else '',
            'is_note': m.message_type == 'comment' and not m.subtype_id.internal if m.subtype_id else False,
        } for m in msgs if (m.body or '').strip()]
        return ok(data)

    @http.route('/api/vendor/v1/disputes/<int:did>/comment', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def dispute_comment(self, did, **kw):
        """Vendor adds a comment/update to an open dispute."""
        v = current_vendor()
        d = request.env['vendor.order.dispute'].sudo().browse(did)
        if not d.exists() or d.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Dispute not found', 404)
        body = (get_payload().get('body') or '').strip()
        if not body:
            return fail('EMPTY', 'body required')
        d.message_post(body=body, author_id=v.partner_id.id or False)
        request.env.cr.commit()
        return ok({'posted': True})
