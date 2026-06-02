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
        name = (p.get('name') or '').strip()
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
        rec = request.env['mobile.page'].sudo().create(vals)
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
        if 'name' in p: vals['name'] = (p['name'] or '').strip() or rec.name
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
