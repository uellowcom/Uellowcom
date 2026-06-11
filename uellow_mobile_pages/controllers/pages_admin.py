# -*- coding: utf-8 -*-
"""Admin builder API — used by the in-browser builder at /uellow-builder.

All endpoints require an authenticated user with internal (group_user)
permissions. CSRF is disabled because we use JSON POST from JS; auth is
provided by the standard Odoo session cookie.

GET    /api/admin/v2/pages                 → list pages (incl. drafts)
POST   /api/admin/v2/pages                 → create
GET    /api/admin/v2/pages/<id>            → fetch one
PUT    /api/admin/v2/pages/<id>            → save (blocks/theme/meta)
POST   /api/admin/v2/pages/<id>/publish    → publish
POST   /api/admin/v2/pages/<id>/archive
POST   /api/admin/v2/pages/<id>/duplicate
POST   /api/admin/v2/pages/<id>/pin
GET    /api/admin/v2/themes
GET    /api/admin/v2/navbar
PUT    /api/admin/v2/navbar/<id>
"""
import json
import logging
import re

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _ok(data=None):
    return request.make_response(
        json.dumps({'success': True, 'data': data or {}}, default=str),
        headers=[('Content-Type', 'application/json')])


def _fail(code, msg, status=400):
    return request.make_response(
        json.dumps({'success': False, 'error': {'code': code, 'message': msg}}),
        status=status,
        headers=[('Content-Type', 'application/json')])


def _payload():
    raw = request.httprequest.get_data(as_text=True) or '{}'
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _require_internal():
    if not request.env.user or request.env.user._is_public():
        return _fail('AUTH', 'Login required', 401)
    if not request.env.user.has_group('base.group_user'):
        return _fail('FORBIDDEN', 'Admin access required', 403)
    return None


def _slugify(s):
    s = (s or '').strip().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-') or 'page'


class PagesAdmin(http.Controller):

    # ─── PAGES ────────────────────────────────────────────────────────

    @http.route('/api/admin/v2/pages', type='http', auth='user',
                methods=['GET'], csrf=False)
    def list_pages(self, **kw):
        guard = _require_internal()
        if guard:
            return guard
        recs = request.env['mobile.page'].sudo().search([])
        return _ok({'pages': [r.to_admin_dict() for r in recs]})

    @http.route('/api/admin/v2/pages', type='http', auth='user',
                methods=['POST'], csrf=False)
    def create_page(self, **kw):
        guard = _require_internal()
        if guard:
            return guard
        p = _payload()
        name_in = p.get('name')
        name = _name_en(name_in)
        if not name:
            return _fail('BAD_REQUEST', 'name required')
        slug = p.get('slug') or _slugify(name)
        if request.env['mobile.page'].sudo().search([('slug', '=', slug)], limit=1):
            slug += '-' + str(request.env['mobile.page'].sudo().search_count([])+1)
        theme_id = False
        if p.get('theme_code'):
            t = request.env['mobile.theme.preset'].sudo().search(
                [('code', '=', p['theme_code'])], limit=1)
            theme_id = t.id if t else False
        vals = {
            'name': name,
            'slug': slug,
            'kind': p.get('kind', 'custom'),
            'theme_preset_id': theme_id,
            'blocks_json': json.dumps(p.get('blocks') or []),
            'lang_ids': [(6, 0, _lang_ids_from_codes(p.get('lang_codes') or ['en', 'ar']))],
            'website_ids': [(6, 0, p.get('website_ids') or [])],
        }
        en_code = _full_lang_code('en') or 'en_US'
        rec = request.env['mobile.page'].sudo().with_context(lang=en_code).create(vals)
        # Persist any non-English name translations supplied as a dict.
        if isinstance(name_in, dict):
            _apply_translations(rec, 'name', name_in)
        return _ok(rec.to_admin_dict())

    @http.route('/api/admin/v2/pages/<int:pid>', type='http', auth='user',
                methods=['GET'], csrf=False)
    def get_page(self, pid, **kw):
        guard = _require_internal()
        if guard:
            return guard
        rec = request.env['mobile.page'].sudo().browse(pid)
        if not rec.exists():
            return _fail('NOT_FOUND', 'Page missing', 404)
        return _ok(rec.to_admin_dict())

    @http.route('/api/admin/v2/pages/<int:pid>', type='http', auth='user',
                methods=['PUT', 'POST', 'PATCH'], csrf=False)
    def update_page(self, pid, **kw):
        guard = _require_internal()
        if guard:
            return guard
        rec = request.env['mobile.page'].sudo().browse(pid)
        if not rec.exists():
            return _fail('NOT_FOUND', 'Page missing', 404)
        p = _payload()
        vals = {}
        if 'name' in p:
            # Accept str (EN only) or {lang: text}. Write translations directly
            # so each language tab in the builder persists independently.
            if isinstance(p['name'], dict):
                _apply_translations(rec, 'name', {k: v for k, v in p['name'].items() if v})
            else:
                clean = (p['name'] or '').strip()
                if clean:
                    vals['name'] = clean
        if 'slug' in p and p['slug']: vals['slug'] = _slugify(p['slug'])
        if 'kind' in p: vals['kind'] = p['kind']
        if 'blocks' in p:
            vals['blocks_json'] = json.dumps(p['blocks'])
        if 'theme_code' in p:
            t = request.env['mobile.theme.preset'].sudo().search(
                [('code', '=', p['theme_code'])], limit=1)
            vals['theme_preset_id'] = t.id if t else False
        if 'theme_override' in p:
            vals['theme_override'] = json.dumps(p['theme_override'] or {})
        if 'website_ids' in p:
            vals['website_ids'] = [(6, 0, p['website_ids'] or [])]
        if 'country_codes' in p:
            ids = request.env['res.country'].sudo().search(
                [('code', 'in', p['country_codes'])]).ids
            vals['country_ids'] = [(6, 0, ids)]
        if 'lang_codes' in p:
            vals['lang_ids'] = [(6, 0, _lang_ids_from_codes(p['lang_codes']))]
        if 'seo' in p and isinstance(p['seo'], dict):
            seo = p['seo']
            if 'title' in seo: vals['seo_title'] = seo['title']
            if 'description' in seo: vals['seo_description'] = seo['description']
            if 'image' in seo: vals['seo_image'] = seo['image']
        # Snapshot a version on every explicit save
        rec.with_context(with_version_snapshot=True).write(vals)
        return _ok(rec.to_admin_dict())

    @http.route('/api/admin/v2/pages/<int:pid>/publish', type='http',
                auth='user', methods=['POST'], csrf=False)
    def publish_page(self, pid, **kw):
        guard = _require_internal()
        if guard:
            return guard
        rec = request.env['mobile.page'].sudo().browse(pid)
        if not rec.exists():
            return _fail('NOT_FOUND', 'Page missing', 404)
        rec.action_publish()
        return _ok(rec.to_admin_dict())

    @http.route('/api/admin/v2/pages/<int:pid>/archive', type='http',
                auth='user', methods=['POST'], csrf=False)
    def archive_page(self, pid, **kw):
        guard = _require_internal()
        if guard:
            return guard
        rec = request.env['mobile.page'].sudo().browse(pid)
        if not rec.exists():
            return _fail('NOT_FOUND', 'Page missing', 404)
        rec.action_archive()
        return _ok(rec.to_admin_dict())

    @http.route('/api/admin/v2/pages/<int:pid>/duplicate', type='http',
                auth='user', methods=['POST'], csrf=False)
    def duplicate_page(self, pid, **kw):
        guard = _require_internal()
        if guard:
            return guard
        rec = request.env['mobile.page'].sudo().browse(pid)
        if not rec.exists():
            return _fail('NOT_FOUND', 'Page missing', 404)
        new = rec.copy({'slug': rec.slug + '-copy',
                        'name': rec.name + ' (copy)',
                        'status': 'draft', 'pinned': False})
        return _ok(new.to_admin_dict())

    @http.route('/api/admin/v2/pages/<int:pid>/pin', type='http',
                auth='user', methods=['POST'], csrf=False)
    def pin_page(self, pid, **kw):
        guard = _require_internal()
        if guard:
            return guard
        rec = request.env['mobile.page'].sudo().browse(pid)
        if not rec.exists():
            return _fail('NOT_FOUND', 'Page missing', 404)
        rec.action_pin_as_home()
        return _ok(rec.to_admin_dict())

    @http.route('/api/admin/v2/pages/<int:pid>', type='http',
                auth='user', methods=['DELETE'], csrf=False)
    def delete_page(self, pid, **kw):
        guard = _require_internal()
        if guard:
            return guard
        rec = request.env['mobile.page'].sudo().browse(pid)
        if not rec.exists():
            return _fail('NOT_FOUND', 'Page missing', 404)
        rec.unlink()
        return _ok({'deleted': True})

    # ─── THEMES ──────────────────────────────────────────────────────

    @http.route('/api/admin/v2/themes', type='http', auth='user',
                methods=['GET'], csrf=False)
    def themes(self, **kw):
        guard = _require_internal()
        if guard:
            return guard
        recs = request.env['mobile.theme.preset'].sudo().search([])
        return _ok({'themes': [r.to_dict() for r in recs]})

    # ─── WEBSITES + LANGUAGES (lookup data for the builder) ─────────

    @http.route('/api/admin/v2/lookups', type='http', auth='user',
                methods=['GET'], csrf=False)
    def lookups(self, **kw):
        guard = _require_internal()
        if guard:
            return guard
        websites = request.env['website'].sudo().search([])
        langs = request.env['res.lang'].sudo().search([('active', '=', True)])
        # Map website → country code via mobile.country.website if present
        site_to_country = {}
        try:
            for m in request.env['mobile.country.website'].sudo().search([]):
                site_to_country[m.website_id.id] = (m.country_id.code, m.country_id.name)
        except Exception:
            pass
        return _ok({
            'websites': [{
                'id': w.id, 'name': w.name,
                'country_code': site_to_country.get(w.id, (None, None))[0],
                'country_name': site_to_country.get(w.id, (None, None))[1],
            } for w in websites],
            'languages': [{
                'code': l.code, 'short': l.code.split('_')[0],
                'name': l.name, 'iso': l.iso_code,
            } for l in langs],
            'countries': [{
                'code': c.code, 'name': c.name,
            } for c in request.env['res.country'].sudo().search([('code', 'in',
                ['KW','SA','AE','QA','EG','OM','BH','JO','LB','IQ','US','GB','FR','IN','PH'])])],
        })

    # ─── NAVBAR ──────────────────────────────────────────────────────

    @http.route('/api/admin/v2/navbar', type='http', auth='user',
                methods=['GET'], csrf=False)
    def list_navbars(self, **kw):
        guard = _require_internal()
        if guard:
            return guard
        recs = request.env['mobile.navbar'].sudo().search([])
        return _ok({'navbars': [r.to_admin_dict() for r in recs]})

    @http.route('/api/admin/v2/navbar/<int:nid>', type='http', auth='user',
                methods=['PUT', 'POST', 'PATCH'], csrf=False)
    def update_navbar(self, nid, **kw):
        guard = _require_internal()
        if guard:
            return guard
        rec = request.env['mobile.navbar'].sudo().browse(nid)
        if not rec.exists():
            return _fail('NOT_FOUND', 'Navbar missing', 404)
        p = _payload()
        vals = {}
        if 'items' in p:
            vals['items_json'] = json.dumps(p['items'])
        for k in ('name', 'active_color', 'inactive_color', 'floating_action'):
            if k in p:
                vals[k] = p[k]
        for k in ('show_labels', 'haptic', 'active'):
            if k in p:
                vals[k] = bool(p[k])
        if 'website_id' in p:
            vals['website_id'] = p['website_id'] or False
        rec.write(vals)
        return _ok(rec.to_admin_dict())


class AdminLookups(http.Controller):
    """Pickers for the builder UI — categories, products, vendors, sliders."""

    @http.route('/api/admin/v2/lookups/categories', type='http', auth='user',
                methods=['GET'], csrf=False)
    def categories(self, **kw):
        guard = _require_internal()
        if guard:
            return guard
        q = (kw.get('q') or '').strip()
        Cat = request.env['product.public.category'].sudo()
        dom = []
        if q:
            dom.append(('name', 'ilike', q))
        recs = Cat.search(dom, limit=80, order='parent_id, sequence, name')
        from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import img_url
        return _ok({'categories': [{
            'id': c.id,
            'name': c.name or '',
            'parent_id': c.parent_id.id if c.parent_id else None,
            'parent_name': c.parent_id.name if c.parent_id else None,
            'image': img_url('product.public.category', c.id, 'image_128',
                             unique=c.write_date) if c.image_128 else None,
        } for c in recs]})

    @http.route('/api/admin/v2/lookups/attributes', type='http', auth='user',
                methods=['GET'], csrf=False)
    def attributes(self, **kw):
        """v2.2.21 — product attributes + their values (colour swatches,
        sizes, specs, brand) for the filtered-link builder. Each value's
        `id` is the product.attribute.value id the storefront filters by
        (value_ids / brand_id)."""
        guard = _require_internal()
        if guard:
            return guard
        Attr = request.env['product.attribute'].sudo()
        recs = Attr.search([], order='sequence, name')
        out = []
        for a in recs:
            nm = (a.name or '').lower()
            kind = ('color' if ('color' in nm or 'لون' in nm)
                    else 'brand' if ('brand' in nm or 'ماركة' in nm
                                     or 'علامة' in nm)
                    else 'other')
            vals = []
            for v in a.value_ids[:200]:
                vals.append({
                    'id': v.id,
                    'name': v.name or '',
                    'html_color': v.html_color or '',
                })
            if vals:
                out.append({
                    'id': a.id, 'name': a.name or '',
                    'kind': kind, 'display_type': a.display_type,
                    'values': vals,
                })
        return _ok({'attributes': out})

    @http.route('/api/admin/v2/lookups/products', type='http', auth='user',
                methods=['GET'], csrf=False)
    def products(self, **kw):
        guard = _require_internal()
        if guard:
            return guard
        q = (kw.get('q') or '').strip()
        Tmpl = request.env['product.template'].sudo()
        dom = [('is_published', '=', True), ('sale_ok', '=', True)]
        if q:
            dom = ['&'] + dom + ['|', ('name', 'ilike', q), ('default_code', 'ilike', q)]
        recs = Tmpl.search(dom, limit=40, order='write_date desc')
        from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import img_url
        return _ok({'products': [{
            'id': p.id,
            'name': p.name or '',
            'sku': p.default_code or '',
            'price': float(p.list_price or 0),
            'currency': p.currency_id.symbol,
            'image': img_url('product.template', p.id, 'image_128',
                             unique=p.write_date),
        } for p in recs]})

    @http.route('/api/admin/v2/lookups/vendors', type='http', auth='user',
                methods=['GET'], csrf=False)
    def vendors(self, **kw):
        guard = _require_internal()
        if guard:
            return guard
        q = (kw.get('q') or '').strip()
        try:
            Vendor = request.env['uellow.vendor'].sudo()
        except KeyError:
            return _ok({'vendors': []})
        dom = []
        if q:
            dom.append(('name', 'ilike', q))
        recs = Vendor.search(dom, limit=40, order='write_date desc')
        from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import img_url
        out = []
        for v in recs:
            logo = None
            for field in ('logo_image', 'image_128', 'logo'):
                if field in v._fields and v[field]:
                    logo = img_url('uellow.vendor', v.id, field, unique=v.write_date)
                    break
            out.append({
                'id': v.id,
                'name': v.name if 'name' in v._fields else '',
                'logo': logo,
                'tier': getattr(v, 'tier', '') or '',
            })
        return _ok({'vendors': out})

    @http.route('/api/admin/v2/lookups/brands', type='http', auth='user',
                methods=['GET'], csrf=False)
    def brands(self, **kw):
        """v2.2.27 — product brands (product.brand) for the Category
        Showcase 'brand' source. Guarded → empty list if the brand module
        isn't installed."""
        guard = _require_internal()
        if guard:
            return guard
        q = (kw.get('q') or '').strip()
        Brand = request.env.get('product.brand')
        if Brand is None:
            return _ok({'brands': []})
        Brand = Brand.sudo()
        dom = [('name', 'ilike', q)] if q else []
        recs = Brand.search(dom, limit=80, order='name')
        from odoo.addons.uellow_mobile_manager.controllers.api_v2._common \
            import img_url
        out = []
        for b in recs:
            logo = None
            for field in ('logo', 'image_128', 'image_1920'):
                if field in b._fields and b[field]:
                    logo = img_url('product.brand', b.id, field,
                                   unique=b.write_date)
                    break
            out.append({'id': b.id, 'name': b.name or '', 'logo': logo})
        return _ok({'brands': out})

    @http.route('/api/admin/v2/lookups/tags', type='http', auth='user',
                methods=['GET'], csrf=False)
    def product_tags(self, **kw):
        """v2.2.27 — product tags (product.tag) for the Category Showcase
        'tag' source. Guarded → empty list if unavailable."""
        guard = _require_internal()
        if guard:
            return guard
        q = (kw.get('q') or '').strip()
        Tag = request.env.get('product.tag')
        if Tag is None:
            return _ok({'tags': []})
        Tag = Tag.sudo()
        dom = [('name', 'ilike', q)] if q else []
        recs = Tag.search(dom, limit=120, order='name')
        out = [{'id': t.id, 'name': t.name or '',
                'color': getattr(t, 'color', 0) or 0} for t in recs]
        return _ok({'tags': out})

    @http.route('/api/admin/v2/lookups/flash-sales', type='http',
                auth='user', methods=['GET'], csrf=False)
    def flash_sales(self, **kw):
        """v2.0.62 — surface vendor flash-sale records to the builder so
        the Flash Deal block can be linked to one (or many) of them.

        Query params:
          state=active|upcoming|all — default 'active' + upcoming
        """
        guard = _require_internal()
        if guard:
            return guard
        try:
            Fs = request.env['uellow.flash.sale'].sudo()
        except KeyError:
            return _ok({'flash_sales': []})
        from datetime import datetime
        now = datetime.utcnow()
        state = (kw.get('state') or 'active_upcoming').strip()
        dom = []
        if state == 'active':
            dom = [('state', '=', 'active')]
        elif state == 'all':
            dom = []
        else:
            # active + upcoming = state in (draft, active) AND end_datetime > now
            dom = ['|', ('state', '=', 'active'),
                   '&', ('state', '=', 'draft'), ('end_datetime', '>', now)]
        recs = Fs.search(dom, order='end_datetime asc', limit=200)
        out = []
        for s in recs:
            vendor_name = ''
            try:
                vendor_name = s.vendor_id.name if s.vendor_id else ''
            except Exception:
                pass
            remaining = 0
            if s.end_datetime and s.end_datetime > now:
                remaining = int((s.end_datetime - now).total_seconds())
            out.append({
                'id': s.id,
                'name': s.name,
                'name_ar': s.name_ar or '',
                'vendor_id': s.vendor_id.id if s.vendor_id else 0,
                'vendor_name': vendor_name,
                'state': s.state,
                'discount_pct': s.discount_pct,
                'start_datetime': s.start_datetime.isoformat()
                                 if s.start_datetime else '',
                'end_datetime': s.end_datetime.isoformat()
                               if s.end_datetime else '',
                'remaining_seconds': remaining,
                'units_sold': s.units_sold,
                'max_quantity': s.max_quantity,
                'product_count': len(s.product_ids),
            })
        return _ok({'flash_sales': out})

    @http.route('/api/admin/v2/lookups/promotions', type='http',
                auth='user', methods=['GET'], csrf=False)
    def promotions(self, **kw):
        """v2.1.37 — surface mobile.app.promotion campaigns to the builder
        so the Flash Deal block can be linked to one (timer + products
        come from the campaign)."""
        guard = _require_internal()
        if guard:
            return guard
        Promo = request.env.get('mobile.app.promotion')
        if Promo is None:
            return _ok({'promotions': []})
        from datetime import datetime
        now = datetime.utcnow()
        recs = Promo.sudo().search([
            ('active', '=', True),
            ('state', 'in', ('draft', 'open', 'running')),
        ], order='date_from asc', limit=200)
        out = []
        for p in recs:
            remaining = 0
            if p.date_to and p.date_to > now:
                remaining = int((p.date_to - now).total_seconds())
            approved = len(p.line_ids.filtered(
                lambda l: l.state == 'approved'))
            out.append({
                'id': p.id,
                'name': p.name,
                'label_en': p.label_en or '',
                'label_ar': p.label_ar or '',
                'emoji': p.emoji or '🎯',
                'state': p.state,
                'date_from': p.date_from.isoformat() if p.date_from else '',
                'date_to': p.date_to.isoformat() if p.date_to else '',
                'remaining_seconds': remaining,
                'product_count': approved,
            })
        return _ok({'promotions': out})

    @http.route('/api/admin/v2/lookups/coupons', type='http',
                auth='user', methods=['GET'], csrf=False)
    def coupons(self, **kw):
        """v2.2.11 — loyalty coupon/promo programs for the coupon block
        picker (multi-select)."""
        guard = _require_internal()
        if guard:
            return guard
        Prog = request.env.get('loyalty.program')
        if Prog is None:
            return _ok({'coupons': []})
        recs = Prog.sudo().search([
            ('active', '=', True),
            ('program_type', 'in',
             ('promotion', 'promo_code', 'coupons', 'buy_x_get_y',
              'next_order_coupons')),
        ], limit=200)
        out = []
        for pr in recs:
            rule = pr.rule_ids[:1]
            reward = pr.reward_ids[:1]
            disc = ''
            if reward and reward.reward_type == 'discount':
                disc = ('%d%%' % int(reward.discount or 0)) \
                    if reward.discount_mode == 'percent' \
                    else ('%g' % (reward.discount or 0))
            out.append({
                'id': pr.id,
                'name': pr.name or '',
                'code': (rule and rule.mode == 'with_code'
                         and rule.code) or '',
                'discount_text': disc,
                'program_type': pr.program_type,
                'date_to': pr.date_to.isoformat() if pr.date_to else '',
            })
        return _ok({'coupons': out})

    @http.route('/api/admin/v2/lookups/sliders', type='http', auth='user',
                methods=['GET'], csrf=False)
    def sliders(self, **kw):
        """Existing mobile.slider records — handy for reusing already-
        designed hero artwork."""
        guard = _require_internal()
        if guard:
            return guard
        try:
            recs = request.env['mobile.slider'].sudo().search([], limit=40)
        except KeyError:
            return _ok({'sliders': []})
        from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import img_url
        return _ok({'sliders': [{
            'id': s.id,
            'name': s.name if 'name' in s._fields else '',
            'image': img_url('mobile.slider', s.id, 'image_1920', unique=s.write_date),
        } for s in recs]})


class AdminUploads(http.Controller):
    """Accept image uploads from the builder. Stores as a public
    ir.attachment so the URL works without auth on the mobile app."""

    @http.route('/api/admin/v2/uploads/image', type='http', auth='user',
                methods=['POST'], csrf=False)
    def upload_image(self, **kw):
        guard = _require_internal()
        if guard:
            return guard
        f = request.httprequest.files.get('file')
        if not f:
            return _fail('NO_FILE', 'No file part', 400)
        raw = f.read()
        if not raw:
            return _fail('EMPTY', 'Empty file', 400)
        # Cap at ~8 MB to avoid runaway uploads
        if len(raw) > 8 * 1024 * 1024:
            return _fail('TOO_LARGE', 'Image must be under 8 MB', 400)
        import base64
        Att = request.env['ir.attachment'].sudo()
        att = Att.create({
            'name': f.filename or 'builder-image.bin',
            'datas': base64.b64encode(raw),
            'public': True,
            'res_model': 'mobile.page',
            'mimetype': f.mimetype or 'image/png',
        })
        from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import base_url
        url = f'{base_url()}/web/image/{att.id}'
        return _ok({'attachment_id': att.id, 'url': url,
                    'name': att.name, 'size': len(raw)})


def _full_lang_code(short):
    """'en' -> 'en_US', 'ar' -> 'ar_001'. Returns an active res.lang code."""
    Lang = request.env['res.lang'].sudo()
    rec = Lang.search([('code', '=', short)], limit=1)
    if not rec:
        rec = Lang.search([('code', '=like', short + '%')], limit=1)
    return rec.code if rec else None


def _apply_translations(rec, field, value):
    """Write a translatable Char/Text in every supplied language.
    `value` may be a plain string (EN only) or a {lang: text} dict.
    Empty values are skipped so a blank AR tab never wipes an existing one."""
    if isinstance(value, dict):
        # Write English first so it becomes the source term, then the rest.
        items = sorted(value.items(), key=lambda kv: 0 if kv[0] == 'en' else 1)
        for short, txt in items:
            if not txt:
                continue
            code = _full_lang_code(short)
            if code:
                rec.with_context(lang=code).write({field: txt})
    elif value is not None:
        rec.write({field: value})


def _name_en(value):
    """Extract the English/primary string from a str or {lang: text} dict."""
    if isinstance(value, dict):
        return (value.get('en') or value.get('ar') or
                next((v for v in value.values() if v), '') or '').strip()
    return (value or '').strip()


def _lang_ids_from_codes(codes):
    if not codes:
        return []
    # Accept short forms like ['en','ar'] OR full ['en_US','ar_001']
    Lang = request.env['res.lang'].sudo()
    ids = []
    for c in codes:
        # try exact match
        rec = Lang.search([('code', '=', c)], limit=1)
        if not rec:
            # try by prefix
            rec = Lang.search([('code', '=like', c + '%')], limit=1)
        if rec:
            ids.append(rec.id)
    return ids
