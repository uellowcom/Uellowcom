import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_SKIP = {'paypal', 'wire_transfer'}
_COD  = {'cod', 'COD', 'custom', 'cash_on_delivery'}


def _product_url(product, base):
    """Get product URL safely across Odoo versions."""
    try:
        tmpl = product.product_tmpl_id
        # Try website_url first (Odoo 17+), then website_slug (older)
        url = getattr(tmpl, 'website_url', None)
        if url:
            return base.rstrip('/') + url
        slug = getattr(tmpl, 'website_slug', None)
        if slug:
            return '%s/shop/product/%s' % (base, slug)
    except Exception:
        pass
    return ''


class FastBuy(http.Controller):

    @http.route(['/fb-debug'], type='http', auth='public', website=True)
    def fb_debug(self, **post):
        lines = ['<pre style="font:13px monospace;padding:20px">']
        lines.append('=== payment.method ===\n')
        try:
            for m in request.env['payment.method'].sudo().search([], order='id asc'):
                lines.append('id=%-3d  active=%-5s  code=%-30s  name=%s' % (
                    m.id, m.active, getattr(m, 'code', 'N/A'), m.name))
        except Exception as e:
            lines.append('ERROR: ' + str(e))
        lines.append('\n\n=== payment.provider ===\n')
        try:
            for p in request.env['payment.provider'].sudo().search([], order='id asc'):
                lines.append('id=%-3d  state=%-10s  code=%-30s  name=%s' % (
                    p.id, p.state, getattr(p, 'code', 'N/A'), p.name))
        except Exception as e:
            lines.append('ERROR: ' + str(e))
        lines.append('</pre>')
        return '\n'.join(lines)

    @http.route(['/shop/fb/payment_methods'], type='json', auth='public', website=True, csrf=False)
    def get_payment_methods(self, **post):
        result    = []
        cod_added = False
        try:
            methods = request.env['payment.method'].sudo().search(
                [('active', '=', True)], order='id asc'
            )
            for m in methods:
                code = getattr(m, 'code', None) or ('m%d' % m.id)
                if code in _SKIP:
                    continue
                if code in _COD:
                    if not cod_added:
                        cod_added = True
                        result.insert(0, {
                            'id': m.id, 'name': m.name, 'code': 'cod',
                            'image': '/web/image/payment.method/%d/image_128' % m.id,
                        })
                    continue
                result.append({
                    'id': m.id, 'name': m.name, 'code': code,
                    'image': '/web/image/payment.method/%d/image_128' % m.id,
                })
        except Exception as e:
            _logger.error('payment.method error: %s', e)
        if not result:
            result = [{'id': -1, 'name': 'Cash on Delivery', 'code': 'cod', 'image': ''}]
        return {'success': True, 'methods': result}

    @http.route(['/shop/fb/submit'], type='json', auth='public', website=True, csrf=False)
    def fb_submit(self, **post):
        order = request.website.sale_get_order()
        if not order or not order.order_line:
            return {'success': False, 'error': 'empty_cart'}

        partner_obj    = request.env['res.partner'].sudo()
        phone          = (post.get('phone') or '').strip()
        name           = (post.get('name') or '').strip()
        latitude       = post.get('latitude') or ''
        longitude      = post.get('longitude') or ''
        street         = (post.get('street') or '').strip()
        city           = (post.get('city') or '').strip()
        country_code   = (post.get('country_code') or '').strip().upper()
        full_address   = (post.get('full_address') or '').strip()
        payment_method = (post.get('payment_method') or 'cod').strip()

        if not name or not phone:
            return {'success': False, 'error': 'missing_fields'}

        country = request.env['res.country'].sudo().search(
            [('code', '=', country_code)], limit=1
        ) if country_code else request.env['res.country']

        partner_vals = {
            'name': name, 'phone': phone, 'customer_rank': 1,
            'street': street or full_address, 'city': city,
        }
        if country:
            partner_vals['country_id'] = country.id
        if latitude and longitude:
            try:
                partner_vals['partner_latitude']  = float(latitude)
                partner_vals['partner_longitude'] = float(longitude)
            except ValueError:
                pass

        existing = partner_obj.search([('phone', '=', phone)], limit=1)
        partner  = existing or partner_obj.create(partner_vals)
        if existing:
            existing.write(partner_vals)

        note = ''
        if full_address:
            note = 'Delivery Address: %s' % full_address
            if latitude and longitude:
                note += '\nCoordinates: %s, %s' % (latitude, longitude)
        note += ('\n' if note else '') + 'Payment: %s' % payment_method

        product_name = product_url_val = ''
        try:
            line         = order.order_line[0]
            product_name = line.product_id.name or ''
            base         = request.website.get_base_url()
            product_url_val = _product_url(line.product_id, base)
        except Exception:
            pass

        order.write({
            'partner_id': partner.id, 'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id, 'is_quick_checkout': True, 'note': note,
        })
        order.action_confirm()

        request.env.cr.execute('SELECT name, amount_total FROM sale_order WHERE id = %s', (order.id,))
        row          = request.env.cr.fetchone()
        order_name   = row[0] if row else ('SO-%d' % order.id)
        amount_total = float(row[1]) if row else 0.0

        currency_name = ''
        try:
            currency_name = request.env['sale.order'].sudo().browse(order.id).currency_id.name or ''
        except Exception:
            pass

        request.env['fast.buy'].sudo().create({
            'name': name, 'phone': phone,
            'sale_order_id': order.id, 'partner_id': partner.id,
        })
        request.website.sale_reset()

        return {
            'success': True, 'order_id': order.id,
            'order_name': order_name, 'amount_total': '%.3f' % amount_total,
            'currency': currency_name, 'product_name': product_name,
            'product_url': product_url_val,
        }

    @http.route(['/shop/fb/add/<int:pid>'], type='json', auth='public', website=True, csrf=False)
    def fb_add(self, pid, **post):
        """pid = product.template id (from data-template-id attribute)."""
        request.website.sale_reset()
        env     = request.env
        product = None

        # pid is template id — find first active variant
        try:
            tmpl = env['product.template'].sudo().with_context(active_test=False).browse(pid)
            if tmpl.exists():
                variants = tmpl.product_variant_ids.filtered(lambda v: v.active)
                if not variants:
                    variants = tmpl.product_variant_ids
                if variants:
                    product = variants[0]
        except Exception as e:
            _logger.warning('fb_add template pid=%s: %s', pid, e)

        # Fallback: try as product.product id
        if not product:
            try:
                pp = env['product.product'].sudo().with_context(active_test=False).browse(pid)
                if pp.exists():
                    product = pp
            except Exception as e:
                _logger.warning('fb_add product pid=%s: %s', pid, e)

        if not product:
            _logger.error('fb_add: pid=%s not found', pid)
            return {'success': False, 'error': 'not_found', 'pid': pid}

        try:
            order = request.website.sale_get_order(force_create=True)
            order._cart_update(product_id=product.id, add_qty=1)
            base = request.website.get_base_url()
            return {
                'success': True,
                'product_name': product.name,
                'product_id':   product.id,
                'product_url':  _product_url(product, base),
            }
        except Exception as e:
            _logger.error('fb_add cart_update pid=%s: %s', pid, e)
            return {'success': False, 'error': str(e)}
