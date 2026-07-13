import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_SKIP_PAY = {'paypal', 'wire_transfer'}
_COD_PAY  = {'cod', 'COD', 'custom', 'cash_on_delivery'}

# Reuse the standard checkout's zone/free-shipping-aware, SHIP-GUARD-protected
# price helper so zorder charges the exact same shipping as /shop/checkout.
try:
    from odoo.addons.uellow_checkout.controllers.main import _uc_ship_price
except Exception:  # pragma: no cover - defensive on load order
    _uc_ship_price = None


def _zo_apply_shipping(order):
    """Resolve a default carrier and add the delivery line BEFORE confirm.

    zorder confirms a plain website cart that never passes through
    /shop/checkout/address/save, so without this it has no carrier and no
    shipping line — sub-threshold orders ship free by accident. This mirrors
    the SHIP-GUARD safety-net in uellow_checkout.save_address.
    """
    try:
        if order.carrier_id:
            return  # a delivery method is already set
    except Exception:
        pass
    partner = order.partner_shipping_id or order.partner_id
    dest_code = (partner.country_id.code or '') if partner and partner.country_id else ''
    carrier = None
    try:
        published = request.env['delivery.carrier'].sudo().search(
            [('website_published', '=', True)])
        # Prefer a carrier open right now (check_time=True), else any
        # location-valid one so the order still gets a correct shipping line.
        for _ct in (True, False):
            for c in published:
                try:
                    if not hasattr(c, 'available_for_order') or c.available_for_order(
                            order, website=request.website,
                            country_code=dest_code, channel='website',
                            check_time=_ct):
                        carrier = c
                        break
                except Exception:
                    continue
            if carrier is not None:
                break
    except Exception as e:
        _logger.warning('zorder default carrier: %s', e)
    if carrier is None:
        _logger.warning('zorder %s: no carrier resolved — no shipping line added', order.id)
        return
    try:
        price = _uc_ship_price(carrier, order) if _uc_ship_price else float(carrier.fixed_price or 0.0)
        order.sudo().set_delivery_line(carrier, price)
    except Exception as e:
        _logger.warning('zorder set_delivery_line: %s', e)
        try:
            order.sudo().write({'carrier_id': carrier.id})
        except Exception:
            pass


def _get_product_url(product):
    """Get product page URL safely across Odoo versions."""
    try:
        base = request.website.get_base_url()
        tmpl = product.product_tmpl_id
        # Try website_url (Odoo 17/18)
        url = getattr(tmpl, 'website_url', None)
        if url and isinstance(url, str):
            return base.rstrip('/') + url
        # Try website_slug (older)
        slug = getattr(tmpl, 'website_slug', None)
        if slug and isinstance(slug, str):
            return '%s/shop/product/%s' % (base, slug)
    except Exception:
        pass
    return ''


class ZOrderController(http.Controller):

    # ── payment methods ──────────────────────────────────────────
    @http.route(['/zorder/payments'], type='json', auth='public', website=True, csrf=False)
    def zorder_payments(self, **kw):
        methods = []
        try:
            website   = request.website
            providers = request.env['payment.provider'].sudo().search([
                ('state', 'in', ('enabled', 'test')),
                '|', ('website_id', '=', False),
                     ('website_id', '=', website.id),
            ])
            seen = set()
            for p in providers:
                try:
                    p_id   = int(p.id)
                    p_name = str(p.name or '')
                    p_code = str(getattr(p, 'code', '') or '')
                    for m in p.payment_method_ids.filtered('active'):
                        m_id = int(m.id)
                        if m_id not in seen:
                            seen.add(m_id)
                            methods.append({
                                'id':            m_id,
                                'name':          str(m.name or ''),
                                'code':          str(getattr(m, 'code', '') or ''),
                                'icon':          '/web/image/payment.method/%d/image_128' % m_id,
                                'provider_id':   p_id,
                                'provider_name': p_name,
                                'provider_code': p_code,
                                'is_cod':        bool(p_code == 'custom'),
                            })
                except Exception as e:
                    _logger.debug('zorder payment iter: %s', e)
        except Exception as e:
            _logger.warning('zorder payments: %s', e)

        if not methods:
            methods = [{'id': -1, 'name': 'Cash on Delivery', 'code': 'cod',
                        'icon': '', 'provider_id': 0, 'provider_name': '',
                        'provider_code': 'custom', 'is_cod': True}]
        return {'ok': True, 'methods': methods}

    # ── add product to cart ──────────────────────────────────────
    @http.route(['/zorder/add/<int:tmpl_id>'], type='json', auth='public', website=True, csrf=False)
    def zorder_add(self, tmpl_id, **kw):
        """tmpl_id = product.template id (always sent from data-template-id)."""
        request.website.sale_reset()
        env     = request.env
        product = None

        # Find first active variant of the template
        try:
            tmpl = env['product.template'].sudo().with_context(active_test=False).browse(tmpl_id)
            if tmpl.exists():
                variants = tmpl.product_variant_ids.filtered(lambda v: v.active)
                if not variants:
                    variants = tmpl.product_variant_ids
                if variants:
                    product = variants[0]
        except Exception as e:
            _logger.error('zorder_add tmpl %s: %s', tmpl_id, e)

        if not product:
            _logger.error('zorder_add: tmpl_id=%s not found', tmpl_id)
            return {'ok': False, 'error': 'not_found'}

        try:
            order = request.website.sale_get_order(force_create=True)
            order._cart_update(product_id=product.id, add_qty=1)
            return {
                'ok':           True,
                'product_name': product.name,
                'product_id':   product.id,
                'product_url':  _get_product_url(product),
            }
        except Exception as e:
            _logger.error('zorder_add cart_update %s: %s', tmpl_id, e)
            return {'ok': False, 'error': str(e)}

    # ── submit order ─────────────────────────────────────────────
    @http.route(['/zorder/submit'], type='json', auth='public', website=True, csrf=False)
    def zorder_submit(self, **kw):
        order = request.website.sale_get_order()
        if not order or not order.order_line:
            return {'ok': False, 'error': 'empty_cart'}

        name           = (kw.get('name') or '').strip()
        phone          = (kw.get('phone') or '').strip()
        email          = (kw.get('email') or '').strip()
        full_address   = (kw.get('full_address') or '').strip()
        street         = (kw.get('street') or '').strip()
        city           = (kw.get('city') or '').strip()
        country_code   = (kw.get('country_code') or '').strip().upper()
        latitude       = kw.get('latitude') or ''
        longitude      = kw.get('longitude') or ''
        payment_method = (kw.get('payment_method') or 'cod').strip()

        if not name or not phone:
            return {'ok': False, 'error': 'missing_fields'}

        env = request.env
        country = env['res.country'].sudo().search([('code', '=', country_code)], limit=1) if country_code else env['res.country']

        partner_vals = {'name': name, 'phone': phone, 'customer_rank': 1,
                        'street': street or full_address, 'city': city}
        if email:
            partner_vals['email'] = email
        if country:
            partner_vals['country_id'] = country.id
        if latitude and longitude:
            try:
                partner_vals['partner_latitude']  = float(latitude)
                partner_vals['partner_longitude'] = float(longitude)
            except ValueError:
                pass

        partner_obj = env['res.partner'].sudo()
        existing    = partner_obj.search([('phone', '=', phone)], limit=1)
        partner     = existing or partner_obj.create(partner_vals)
        if existing:
            existing.write(partner_vals)

        note = ('Delivery: %s' % full_address) if full_address else ''
        if latitude and longitude:
            note += '\nCoords: %s,%s' % (latitude, longitude)
        note += ('\n' if note else '') + 'Payment: %s' % payment_method

        # Collect product info before confirm
        product_name = product_url_val = ''
        try:
            prod = order.order_line[0].product_id
            product_name  = prod.name or ''
            product_url_val = _get_product_url(prod)
        except Exception:
            pass

        order.write({'partner_id': partner.id, 'partner_invoice_id': partner.id,
                     'partner_shipping_id': partner.id, 'is_zorder': True, 'note': note})
        # Resolve carrier + add shipping line before confirming (zorder bypasses
        # the standard checkout, so this is where the SHIP-GUARD must run).
        _zo_apply_shipping(order)
        order.action_confirm()

        # Read confirmed order data directly from DB
        env.cr.execute('SELECT name, amount_total FROM sale_order WHERE id = %s', (order.id,))
        row          = env.cr.fetchone()
        order_name   = row[0] if row else ('S-%d' % order.id)
        amount_total = float(row[1]) if row else 0.0

        currency = ''
        try:
            currency = env['sale.order'].sudo().browse(order.id).currency_id.name or ''
        except Exception:
            pass

        request.env['z.order'].sudo().create({'name': name, 'phone': phone,
                                      'sale_order_id': order.id, 'partner_id': partner.id})
        request.website.sale_reset()

        # Get access_token for payment transaction
        access_token = ''
        currency_id  = 0
        partner_id_val = partner.id
        try:
            order_sudo   = request.env['sale.order'].sudo().browse(order.id)
            access_token = order_sudo.access_token or ''
            currency_id  = order_sudo.currency_id.id or 0
        except Exception:
            pass

        return {'ok': True, 'order_id': order.id, 'order_name': order_name,
                'amount_total': '%.3f' % amount_total, 'currency': currency,
                'currency_id': currency_id, 'partner_id': partner_id_val,
                'access_token': access_token,
                'product_name': product_name, 'product_url': product_url_val}
