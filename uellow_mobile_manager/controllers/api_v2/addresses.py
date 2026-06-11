"""Addresses CRUD — /api/mobile/v2/addresses/*

Adds: lat/lng + country_code lookup + landmark photo (base64) saved as
a chatter attachment, plus address_label persisted in `name` prefix when
the field isn't on res.partner.
"""
import base64
from odoo import http, fields
from odoo.http import request

from ._common import (safe_endpoint, get_payload, ok, fail, current_partner,
                      require_auth, app_setting)
from .cart import _get_or_create_order
from .orders import _addr_dict


class MobileAddressesAPI(http.Controller):

    @http.route('/api/mobile/v2/addresses', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_addresses(self, **kw):
        partner = current_partner()
        # Newest first — so the address the user just added appears at
        # the top of the picker. The owner partner is always last (it's
        # the legacy default and rarely the right shipping address).
        addrs = request.env['res.partner'].sudo().search([
            ('parent_id', '=', partner.id),
            ('type', 'in', ('delivery', 'invoice')),
        ], order='is_default_shipping desc, create_date desc')
        return ok([*[_addr_dict(a) for a in addrs], _addr_dict(partner)])

    @http.route('/api/mobile/v2/addresses/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def create_address(self, **kw):
        p = get_payload()
        partner = current_partner()
        # v2.1.20 — GUEST checkout: when enabled (per-website setting) and
        # the client sent guest=1, the address becomes an ad-hoc partner
        # attached to the guest cart order (no account involved).
        if not partner:
            guest_flag = str(p.get('guest') or '') in ('1', 'true', 'True')
            enabled = bool(getattr(app_setting(), 'guest_checkout_enabled',
                                   False))
            if not (guest_flag and enabled):
                return fail('AUTH_REQUIRED', 'You must be logged in.', 401)
            order = _get_or_create_order(create=False)
            if not order:
                return fail('EMPTY_CART', 'Cart is empty', 400)
            vals = _validate_addr(p)
            if isinstance(vals, str):
                return fail('VALIDATION', vals)
            vals['type'] = 'contact'
            addr = request.env['res.partner'].sudo().create(vals)
            _attach_landmark_photo(addr, p)
            _save_lat_lng(addr, p)
            _save_address_label(addr, p)
            _save_structured(addr, p)
            order.sudo().write({
                'partner_id': addr.id,
                'partner_invoice_id': addr.id,
                'partner_shipping_id': addr.id,
            })
            return ok({'address': _addr_dict(addr)})
        vals = _validate_addr(p)
        if isinstance(vals, str):
            return fail('VALIDATION', vals)
        vals['parent_id'] = partner.id
        vals['type'] = p.get('type', 'delivery')
        addr = request.env['res.partner'].sudo().create(vals)
        _attach_landmark_photo(addr, p)
        _save_lat_lng(addr, p)
        _save_address_label(addr, p)
        _save_structured(addr, p)
        return ok({'address': _addr_dict(addr)})

    @http.route('/api/mobile/v2/addresses/<int:addr_id>/set-default',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def set_default_address(self, addr_id, **kw):
        """Mark ONE address as the primary/default delivery address."""
        partner = current_partner()
        addr = request.env['res.partner'].sudo().browse(addr_id)
        if not addr.exists() or (addr.parent_id != partner and addr != partner):
            return fail('NOT_FOUND', 'Address not found', 404)
        siblings = request.env['res.partner'].sudo().search([
            '|', ('id', '=', partner.id), ('parent_id', '=', partner.id),
            ('is_default_shipping', '=', True),
        ])
        siblings.write({'is_default_shipping': False})
        addr.write({'is_default_shipping': True})
        return ok({'address': _addr_dict(addr)})

    @http.route('/api/mobile/v2/addresses/<int:addr_id>/update', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def update_address(self, addr_id, **kw):
        p = get_payload()
        partner = current_partner()
        addr = request.env['res.partner'].sudo().browse(addr_id)
        if not partner:
            # v2.1.21 — guests may edit THEIR OWN cart's ad-hoc address.
            guest_flag = str(p.get('guest') or '') in ('1', 'true', 'True')
            enabled = bool(getattr(app_setting(), 'guest_checkout_enabled',
                                   False))
            order = _get_or_create_order(create=False) \
                if (guest_flag and enabled) else None
            owned = (order and addr.exists() and addr.id in
                     (order.partner_id.id, order.partner_shipping_id.id))
            if not owned:
                return fail('AUTH_REQUIRED', 'You must be logged in.', 401)
        elif not addr.exists() or (addr.parent_id != partner and addr != partner):
            return fail('NOT_FOUND', 'Address not found', 404)
        vals = _validate_addr(p, partial=True)
        if isinstance(vals, str):
            return fail('VALIDATION', vals)
        addr.write(vals)
        _attach_landmark_photo(addr, p)
        _save_lat_lng(addr, p)
        _save_address_label(addr, p)
        _save_structured(addr, p)
        return ok({'address': _addr_dict(addr)})

    @http.route('/api/mobile/v2/addresses/<int:addr_id>/delete', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def delete_address(self, addr_id, **kw):
        partner = current_partner()
        addr = request.env['res.partner'].sudo().browse(addr_id)
        if not addr.exists() or addr.parent_id != partner:
            return fail('NOT_FOUND', 'Address not found', 404)
        addr.active = False  # soft delete (Odoo may reference it from orders)
        return ok({'deleted': True})


def _validate_addr(p, partial=False):
    out = {}
    for k in ('name', 'phone', 'mobile', 'street', 'street2', 'city', 'zip', 'email'):
        if k in p:
            out[k] = p[k] or ''
    if 'country_id' in p:
        try: out['country_id'] = int(p['country_id'])
        except Exception: pass
    elif 'country_code' in p and p['country_code']:
        country = request.env['res.country'].sudo().search(
            [('code', '=', (p['country_code'] or '').upper())], limit=1)
        if country: out['country_id'] = country.id
    if 'state_id' in p:
        try: out['state_id'] = int(p['state_id'])
        except Exception: pass
    elif 'state' in p and p['state']:
        # Try to resolve by name within the chosen country
        country_id = out.get('country_id')
        domain = [('name', 'ilike', p['state'])]
        if country_id: domain.append(('country_id', '=', country_id))
        st = request.env['res.country.state'].sudo().search(domain, limit=1)
        if st: out['state_id'] = st.id
    # v2.1.99 — readable backend records: a digits-only street becomes
    # "Street 4 / شارع 4". (v2.2.00 — the governorate is no longer mashed
    # into city; it lives in the structured uellow_governorate_id field,
    # keeping `city` clean for the delivery-zone matcher.)
    st = (out.get('street') or '').strip()
    if st.isdigit():
        out['street'] = 'Street %s / شارع %s' % (st, st)
    # v2.2.00 — the COUNTRY was often left unset (orders showed no
    # country): default it from the current website's country mapping.
    if not out.get('country_id') and not partial:
        try:
            from ._common import get_website
            m = request.env['mobile.country.website'].sudo().search(
                [('website_id', '=', get_website().id),
                 ('active', '=', True)], limit=1)
            if m:
                out['country_id'] = m.country_id.id
        except Exception:
            pass
    if not partial:
        if not out.get('name'): return 'name required'
        if not (out.get('phone') or out.get('mobile')): return 'phone required'
        if not out.get('street'): return 'street required'
        if not out.get('city'): return 'city required'
    return out


def _norm_ar(s):
    """Light Arabic/text normalisation for name matching."""
    s = (s or '').strip().lower()
    s = s.replace('محافظة', '').replace('ال', '').replace('al ', '') \
         .replace('al-', '').replace('-', ' ').replace('  ', ' ').strip()
    return s


def _save_structured(addr, p):
    """v2.2.00 — mirror the app's detailed form into the structured
    backend fields (governorate/area M2O resolved by name incl. Arabic
    aliases, block/building/floor/apartment, label) so the partner form
    shows EXACTLY what the customer entered."""
    env = addr.env
    vals = {}
    try:
        for src, dst in (('block', 'uellow_block'),
                         ('building', 'uellow_building'),
                         ('floor', 'uellow_floor'),
                         ('apartment', 'uellow_apartment'),
                         ('address_label', 'uellow_address_label')):
            if (p.get(src) or '').strip():
                vals[dst] = p[src].strip()
        gov_txt = _norm_ar(p.get('state') or p.get('governorate') or '')
        if gov_txt and 'uellow_governorate_id' in addr._fields:
            for g in env['uellow.governorate'].sudo().search([]):
                if gov_txt in (_norm_ar(g.name), _norm_ar(g.name_ar)):
                    vals['uellow_governorate_id'] = g.id
                    break
        area_txt = _norm_ar(p.get('area') or p.get('city') or '')
        if area_txt and 'uellow_city_id' in addr._fields:
            dom = []
            if vals.get('uellow_governorate_id'):
                dom = [('governorate_id', '=', vals['uellow_governorate_id'])]
            for c in env['uellow.city'].sudo().search(dom):
                tokens = {_norm_ar(c.name), _norm_ar(c.name_ar)}
                tokens |= {_norm_ar(a) for a in (c.aliases or '').split(',')}
                if area_txt in tokens:
                    vals['uellow_city_id'] = c.id
                    break
        if vals:
            addr.sudo().write(vals)
    except Exception:
        pass


def _save_lat_lng(addr, p):
    """Persist GPS coords onto res.partner (Odoo's native partner_latitude /
    partner_longitude). Silent no-op if values aren't usable."""
    try:
        lat = p.get('lat'); lng = p.get('lng')
        if lat is None or lng is None: return
        addr.sudo().write({
            'partner_latitude':  float(lat),
            'partner_longitude': float(lng),
            'date_localization': fields.Date.today(),
        })
    except Exception:
        pass


def _save_address_label(addr, p):
    """Store the user-given label (Home / Office / Mum's) as a comment on
    the partner — visible in the back-office without needing a new column."""
    label = (p.get('address_label') or '').strip()
    notes = (p.get('notes') or '').strip()
    if not label and not notes: return
    try:
        # Comment field is universally present on res.partner.
        existing = (addr.comment or '').strip()
        bits = []
        if label: bits.append(f'Label: {label}')
        if notes: bits.append(f'Notes: {notes}')
        full = '\n'.join(bits)
        addr.sudo().write({
            'comment': full if not existing else f'{existing}\n{full}',
        })
    except Exception:
        pass


def _attach_landmark_photo(addr, p):
    """Save the optional landmark photo as an ir.attachment linked to the
    partner so it shows up in the chatter / back-office."""
    photo = p.get('landmark_photo')
    if not photo: return
    try:
        # Strip any "data:image/...,base64," prefix
        if isinstance(photo, str) and ',' in photo and photo.startswith('data:'):
            photo = photo.split(',', 1)[1]
        request.env['ir.attachment'].sudo().create({
            'name': f'Landmark photo — {addr.name or addr.id}.jpg',
            'type': 'binary',
            'datas': photo,
            'res_model': 'res.partner',
            'res_id': addr.id,
            'mimetype': 'image/jpeg',
        })
        # Touch the chatter so backoffice users see it surfaces
        try:
            addr.message_post(body='Landmark photo uploaded from mobile app.')
        except Exception:
            pass
    except Exception:
        pass
