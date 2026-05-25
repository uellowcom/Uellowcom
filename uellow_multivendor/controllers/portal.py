import json
import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class VendorPortalController(http.Controller):

    def _get_vendor(self):
        if request.env.user._is_public():
            return False
        vendor = request.env['uellow.vendor'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not vendor:
            vendor = request.env['uellow.vendor'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)
        return vendor

    # ── Dashboard ──────────────────────────────────────────────────
    @http.route('/my/vendor', type='http', auth='user', website=True)
    def vendor_dashboard(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        recent_orders = request.env['sale.order'].sudo().search([
            ('vendor_id', '=', vendor.id)
        ], limit=5, order='date_order desc')
        products = request.env['product.template'].sudo().search([('vendor_id', '=', vendor.id)])
        total_products = len(products)
        pending_products = len(products.filtered(lambda p: p.vendor_approval_state == 'pending'))
        approved_products = len(products.filtered(lambda p: p.vendor_approval_state == 'approved'))
        all_variants = request.env['product.product'].sudo().search([('product_tmpl_id', 'in', products.ids)])
        low_stock_count = len(all_variants.filtered(lambda p: 0 <= (p.qty_available or 0) <= 5))
        flash_sales = request.env['uellow.flash.sale'].sudo().search([('vendor_id', '=', vendor.id)])
        active_flash_sales = len(flash_sales.filtered(lambda f: f.state == 'active'))
        recent_products = products[:5]
        return request.render('uellow_multivendor.portal_vendor_dashboard', {
            'vendor': vendor,
            'recent_orders': recent_orders,
            'total_products': total_products,
            'pending_products': pending_products,
            'approved_products': approved_products,
            'low_stock_count': low_stock_count,
            'active_flash_sales': active_flash_sales,
            'total_flash_sales': len(flash_sales),
            'recent_products': recent_products,
            'page_name': 'vendor_dashboard',
        })

    # ── Orders ─────────────────────────────────────────────────────
    @http.route('/my/vendor/orders', type='http', auth='user', website=True)
    def vendor_orders(self, search='', state='all', page=1, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        domain = [('vendor_id', '=', vendor.id)]
        if state != 'all':
            domain += [('state', '=', state)]
        if search:
            domain += [('name', 'ilike', search)]
        orders = request.env['sale.order'].sudo().search(
            domain, limit=20, offset=(int(page)-1)*20, order='date_order desc')
        return request.render('uellow_multivendor.portal_vendor_orders', {
            'vendor': vendor,
            'orders': orders,
            'search': search,
            'state': state,
            'page_name': 'vendor_orders',
        })

    @http.route('/my/vendor/orders/validate/<int:picking_id>', type='http',
                auth='user', website=True, methods=['POST'])
    def validate_picking(self, picking_id, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists():
            return request.redirect('/my/vendor/orders')
        if picking.sale_id and picking.sale_id.vendor_id.id != vendor.id:
            return request.redirect('/my/vendor/orders')
        try:
            if picking.state == 'assigned':
                picking.with_context(skip_immediate=True).button_validate()
        except Exception as e:
            _logger.error('Validate picking error: %s', e)
        return request.redirect('/my/vendor/orders')

    @http.route('/my/vendor/orders/prepare/<int:picking_id>', type='http',
                auth='user', website=True)
    def prepare_shipment(self, picking_id, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists():
            return request.redirect('/my/vendor/orders')
        carriers = request.env['delivery.carrier'].sudo().search([
            ('active', '=', True)], limit=20)
        return request.render('uellow_multivendor.portal_vendor_prepare', {
            'picking': picking,
            'carriers': carriers,
            'vendor': vendor,
            'page_name': 'vendor_orders',
        })

    @http.route('/my/vendor/orders/prepare/<int:picking_id>/save', type='http',
                auth='user', website=True, methods=['POST'])
    def prepare_shipment_save(self, picking_id, carrier_id=None, tracking_ref='', **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if picking.exists() and carrier_id:
            picking.write({
                'carrier_id': int(carrier_id),
                'carrier_tracking_ref': tracking_ref or '',
            })
        if picking.exists() and picking.carrier_id:
            return request.redirect('/delivery_label/print/%d' % picking_id)
        return request.redirect('/my/vendor/orders')

    # ── Products ───────────────────────────────────────────────────
    @http.route('/my/vendor/products', type='http', auth='user', website=True)
    def vendor_products(self, search='', state='all', page=1, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        domain = [('vendor_id', '=', vendor.id)]
        if search:
            domain += [('name', 'ilike', search)]
        products = request.env['product.template'].sudo().search(
            domain, limit=40, offset=(int(page)-1)*40, order='name asc')
        view_mode = kw.get('view', 'list')
        return request.render('uellow_multivendor.portal_vendor_products', {
            'vendor': vendor,
            'products': products,
            'search': search,
            'view_mode': view_mode,
            'page_name': 'vendor_products',
        })

    # ── Stock / FBU ────────────────────────────────────────────────
    @http.route('/my/vendor/stock', type='http', auth='user', website=True)
    def vendor_stock(self, filter='all', **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        domain = [('vendor_id', '=', vendor.id)]
        if filter == 'low':
            domain += [('fbu_state', '=', 'low_stock')]
        elif filter == 'out':
            domain += [('fbu_state', '=', 'out_of_stock')]
        products = request.env['product.product'].sudo().search(domain, limit=100)
        all_products = request.env['product.product'].sudo().search([
            ('vendor_id', '=', vendor.id)], limit=200)
        return request.render('uellow_multivendor.portal_vendor_stock', {
            'vendor': vendor,
            'products': products,
            'filter': filter,
            'total_products': len(all_products),
            'fbu_count': len(all_products.filtered(lambda p: (p.qty_available or 0) > 0)),
            'low_count': len(all_products.filtered(lambda p: (p.qty_available or 0) > 0 and (p.qty_available or 0) <= 5)),
            'out_count': len(all_products.filtered(lambda p: (p.qty_available or 0) == 0)),
            'page_name': 'vendor_stock',
        })

    @http.route('/my/vendor/stock/restock', type='http', auth='user', website=True)
    def vendor_restock(self, product_id=None, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        products = request.env['product.product'].sudo().search([
            ('vendor_id', '=', vendor.id)], limit=100)
        selected_product = False
        if product_id:
            selected_product = request.env['product.product'].sudo().browse(int(product_id))
        return request.render('uellow_multivendor.portal_vendor_restock', {
            'vendor': vendor,
            'products': products,
            'selected_product': selected_product,
            'page_name': 'vendor_stock',
        })

    @http.route('/my/vendor/stock/restock/submit', type='http',
                auth='user', website=True, methods=['POST'])
    def vendor_restock_submit(self, product_id=None, qty=0, priority='normal', notes='', **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        try:
            if product_id and int(qty) > 0:
                request.env['uellow.restock.request'].sudo().create({
                    'vendor_id': vendor.id,
                    'product_id': int(product_id),
                    'qty': int(qty),
                    'priority': priority,
                    'notes': notes,
                })
        except Exception as e:
            _logger.error('Restock submit error: %s', e)
        return request.redirect('/my/vendor/stock')

    # ── Wallet ─────────────────────────────────────────────────────
    @http.route('/my/vendor/wallet', type='http', auth='user', website=True)
    def vendor_wallet(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        transactions = []
        if vendor.wallet_id:
            transactions = request.env['uellow.wallet.transaction'].sudo().search([
                ('wallet_id', '=', vendor.wallet_id.id)
            ], limit=30, order='date desc')
        return request.render('uellow_multivendor.portal_vendor_wallet', {
            'vendor': vendor,
            'transactions': transactions,
            'page_name': 'vendor_wallet',
        })

    @http.route('/my/vendor/wallet/payout', type='http', auth='user', website=True)
    def vendor_payout(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        return request.render('uellow_multivendor.portal_vendor_payout', {
            'vendor': vendor,
            'page_name': 'vendor_wallet',
        })

    @http.route('/my/vendor/wallet/payout/submit', type='http',
                auth='user', website=True, methods=['POST'])
    def vendor_payout_submit(self, amount=0, bank_name='', iban='', account_name='', **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        try:
            amt = float(amount)
            if amt > 0 and amt <= (vendor.wallet_balance or 0):
                request.env['uellow.payout.request'].sudo().create({
                    'vendor_id': vendor.id,
                    'amount': amt,
                    'bank_name': bank_name,
                    'bank_iban': iban,
                    'account_name': account_name,
                })
        except Exception as e:
            _logger.error('Payout submit error: %s', e)
        return request.redirect('/my/vendor/wallet')

    # ── Flash Sales ────────────────────────────────────────────────
    @http.route('/my/vendor/flash-sale', type='http', auth='user', website=True)
    def vendor_flash_sale(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        flash_sales = request.env['uellow.flash.sale'].sudo().search([
            ('vendor_id', '=', vendor.id)
        ], order='start_datetime desc', limit=20)
        return request.render('uellow_multivendor.portal_vendor_flash_sale', {
            'vendor': vendor,
            'flash_sales': flash_sales,
            'page_name': 'vendor_flash',
        })

    @http.route('/my/vendor/flash-sale/new', type='http', auth='user', website=True)
    def vendor_flash_sale_new(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        products = request.env['product.template'].sudo().search([
            ('vendor_id', '=', vendor.id)
        ], limit=100)
        return request.render('uellow_multivendor.portal_vendor_flash_sale_form', {
            'vendor': vendor,
            'products': products,
            'page_name': 'vendor_flash',
        })

    @http.route('/my/vendor/flash-sale/create', type='http',
                auth='user', website=True, methods=['POST'])
    def vendor_flash_sale_create(self, **post):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        try:
            product_ids = request.httprequest.form.getlist('product_ids')
            request.env['uellow.flash.sale'].sudo().create({
                'vendor_id': vendor.id,
                'name': post.get('name_en', '') or post.get('name', ''),
                'name_ar': post.get('name_ar', ''),
                'discount_pct': float(post.get('discount_pct', 0)),
                'start_datetime': post.get('start_date', '').replace('T', ' '),
                'end_datetime': post.get('end_date', '').replace('T', ' '),
                'product_ids': [(6, 0, [int(p) for p in product_ids if p])],
            })
        except Exception as e:
            _logger.error('Flash sale create error: %s', e)
        return request.redirect('/my/vendor/flash-sale')

    # ── Settings ───────────────────────────────────────────────────
    @http.route('/my/vendor/settings', type='http', auth='user', website=True)
    def vendor_settings(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        return request.render('uellow_multivendor.portal_vendor_settings', {
            'vendor': vendor,
            'page_name': 'vendor_settings',
        })

    @http.route('/my/vendor/settings/save', type='http',
                auth='user', website=True, methods=['POST'])
    def vendor_settings_save(self, **post):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        try:
            vals = {}
            for field in ['store_name_en', 'store_name_ar', 'store_tagline_en',
                          'store_tagline_ar', 'contact_phone', 'contact_email',
                          'brand_color']:
                if post.get(field) is not None:
                    vals[field] = post.get(field, '')
            for field in ['desc_en', 'desc_ar']:
                if post.get(field) is not None:
                    key = 'store_description_en' if field == 'desc_en' else 'store_description_ar'
                    vals[key] = post.get(field, '')
            if vals:
                vendor.sudo().write(vals)
        except Exception as e:
            _logger.error('Settings save error: %s', e)
        return request.redirect('/my/vendor/settings')


    # ── Notifications page ────────────────────────────────────────
    @http.route('/my/vendor/notifications', type='http', auth='user', website=True)
    def vendor_notifications(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        return request.render('uellow_multivendor.portal_vendor_notifications', {
            'vendor': vendor,
            'page_name': 'vendor_notifications',
        })

    # ── Notifications poll ─────────────────────────────────────────
    @http.route('/my/vendor/notifications/poll', type='http',
                auth='user', website=True)
    def notifications_poll(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.make_response(
                json.dumps({'count': 0, 'items': []}),
                headers=[('Content-Type', 'application/json')]
            )
        # Check for new orders in last 30 seconds
        from odoo import fields
        import datetime
        cutoff = fields.Datetime.now() - datetime.timedelta(seconds=35)
        new_orders = request.env['sale.order'].sudo().search([
            ('vendor_id', '=', vendor.id),
            ('create_date', '>=', cutoff),
            ('state', 'in', ['sale', 'done']),
        ], limit=5)
        items = []
        for order in new_orders:
            items.append({
                'title': 'New Order %s' % order.name,
                'body': '%s · %.3f KD' % (order.partner_id.name, order.amount_total),
                'icon': 'fa-shopping-bag',
                'bg': '#faeeda', 'color': '#854f0b',
                'time': 'now',
                'unread': True,
            })
        return request.make_response(
            json.dumps({'count': len(items), 'items': items}),
            headers=[('Content-Type', 'application/json')]
        )

    # ── Follow vendor ──────────────────────────────────────────────
    @http.route('/my/vendor/follow/<int:vendor_id>', type='json', auth='user')
    def follow_vendor(self, vendor_id):
        vendor = request.env['uellow.vendor'].sudo().browse(vendor_id)
        if vendor.exists():
            try:
                vendor.sudo().action_follow(request.env.user.partner_id.id)
            except Exception:
                pass
        return {'ok': True}


    # ── Products new/import (placeholder) ─────────────────────────
    @http.route('/my/vendor/products/new', type='http', auth='user', website=True)
    def vendor_product_new(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        return request.render('uellow_multivendor.portal_vendor_product_new', {
            'vendor': vendor,
            'page_name': 'vendor_products',
        })

    @http.route('/my/vendor/products/import', type='http', auth='user', website=True)
    def vendor_product_import(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        return request.render('uellow_multivendor.portal_vendor_import', {
            'vendor': vendor,
            'page_name': 'vendor_products',
        })

    @http.route('/my/vendor/products/import/submit', type='http',
                auth='user', website=True, methods=['POST'])
    def vendor_product_import_submit(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        # File upload handled here
        import_file = request.httprequest.files.get('import_file')
        if import_file:
            try:
                import base64
                file_data = base64.b64encode(import_file.read()).decode()
                # Use uellow_smart_connector logic
                request.env['uellow.product.import'].sudo().create({
                    'vendor_id': vendor.id,
                    'file_data': file_data,
                    'file_name': import_file.filename,
                })
            except Exception as e:
                _logger.error('Import error: %s', e)
        return request.redirect('/my/vendor/products')


    # ── Product Manual Add ─────────────────────────────────────────
    @http.route('/my/vendor/products/manual', type='http', auth='user', website=True)
    def vendor_product_manual(self, product_id=None, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        # Get categories
        categories = request.env['product.public.category'].sudo().search([], order='name asc', limit=100)
        # Get attribute values (brands, colors, etc.)
        attributes = request.env['product.attribute'].sudo().search([], order='name asc', limit=50)
        # Edit mode
        product = False
        if product_id:
            product = request.env['product.template'].sudo().browse(int(product_id))
            if not product.exists() or product.vendor_id.id != vendor.id:
                product = False
        return request.render('uellow_multivendor.portal_vendor_product_manual', {
            'vendor': vendor,
            'categories': categories,
            'attributes': attributes,
            'product': product,
            'page_name': 'vendor_products',
        })

    @http.route('/my/vendor/products/manual/submit', type='http',
                auth='user', website=True, methods=['POST'])
    def vendor_product_manual_submit(self, **post):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        try:
            import base64
            vals = {
                'name': post.get('name_en', '').strip(),
                'description_sale': post.get('description_en', ''),
                'list_price': float(post.get('list_price', 0) or 0),
                'standard_price': float(post.get('standard_price', 0) or 0),
                'barcode': post.get('barcode', '') or False,
                'detailed_type': 'storable',
                'website_published': False,  # Not published until admin approves
                'vendor_id': vendor.id,
                'vendor_approval_state': 'pending',
                'vendor_submitted_by': request.env.user.id,
                'vendor_submitted_date': fields.Datetime.now(),
            }
            # Arabic name in description if provided
            if post.get('description_ar'):
                vals['description'] = post.get('description_ar')

            # Image upload
            image_file = request.httprequest.files.get('image')
            if image_file and image_file.filename:
                vals['image_1920'] = base64.b64encode(image_file.read())

            product = request.env['product.template'].sudo().create(vals)

            # Set initial stock if qty provided
            qty = int(post.get('qty', 0) or 0)
            if qty > 0:
                location = False
                if location:
                    request.env['stock.quant'].sudo().with_context(inventory_mode=True).create({
                        'product_id': product.product_variant_id.id,
                        'location_id': location.lot_stock_id.id,
                        'inventory_quantity': qty,
                    })._apply_inventory()

        except Exception as e:
            _logger.error('Manual product create error: %s', e)
        return request.redirect('/my/vendor/products')

    # ── Product URL Import ─────────────────────────────────────────
    @http.route('/my/vendor/products/url', type='http', auth='user', website=True)
    def vendor_product_url(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        return request.render('uellow_multivendor.portal_vendor_product_url', {
            'vendor': vendor,
            'page_name': 'vendor_products',
        })

    @http.route('/my/vendor/products/url/submit', type='http',
                auth='user', website=True, methods=['POST'])
    def vendor_product_url_submit(self, source_url='', enable_ai=None, auto_publish=None, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        if source_url:
            try:
                # Create Smart Connector job for this vendor
                job = request.env['uellow.import.job'].sudo().create({
                    'job_type': 'url_import',
                    'source_url': source_url.strip(),
                    'enable_translation': bool(enable_ai),
                    'enable_seo': bool(enable_ai),
                    'max_products_per_run': 1,
                })
                job.sudo().action_run()
            except Exception as e:
                _logger.error('URL import error: %s', e)
        return request.redirect('/my/vendor/products')

    # ── Product Revoke (vendor withdraws product) ─────────────────
    @http.route('/my/vendor/products/revoke/<int:product_id>', type='http',
                auth='user', website=True, methods=['POST'])
    def vendor_product_revoke(self, product_id, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        product = request.env['product.template'].sudo().browse(product_id)
        if product.exists() and product.vendor_id.id == vendor.id:
            product.sudo().write({
                'vendor_approval_state': 'pending',
                'website_published': False,
            })
        return request.redirect('/my/vendor/products')

    # ── Product Edit (reset to draft) ─────────────────────────────
    @http.route('/my/vendor/products/edit/<int:product_id>', type='http',
                auth='user', website=True)
    def vendor_product_edit(self, product_id, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists() or product.vendor_id.id != vendor.id:
            return request.redirect('/my/vendor/products')
        categories = request.env['product.public.category'].sudo().search([], order='name asc', limit=100)
        attributes = request.env['product.attribute'].sudo().search([], order='name asc', limit=50)
        return request.render('uellow_multivendor.portal_vendor_product_manual', {
            'vendor': vendor,
            'categories': categories,
            'attributes': attributes,
            'product': product,
            'page_name': 'vendor_products',
        })

    @http.route('/my/vendor/products/edit/<int:product_id>/submit', type='http',
                auth='user', website=True, methods=['POST'])
    def vendor_product_edit_submit(self, product_id, **post):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists() or product.vendor_id.id != vendor.id:
            return request.redirect('/my/vendor/products')
        try:
            import base64
            vals = {
                'name': post.get('name_en', '').strip() or post.get('name_ar', '').strip(),
                'description_sale': post.get('description_en', ''),
                'description': post.get('description_ar', ''),
                'list_price': float(post.get('list_price', 0) or 0),
                'standard_price': float(post.get('standard_price', 0) or 0),
                'barcode': post.get('barcode', '') or False,
                'vendor_approval_state': 'pending',
                'website_published': False,
                'vendor_submitted_date': fields.Datetime.now(),
            }
            categ_id = post.get('categ_id')
            if categ_id:
                vals['categ_id'] = int(categ_id)
            public_categ = request.httprequest.form.getlist('public_categ_ids')
            if public_categ:
                vals['public_categ_ids'] = [(6, 0, [int(c) for c in public_categ if c])]
            # Main image
            image_file = request.httprequest.files.get('image')
            if image_file and image_file.filename:
                vals['image_1920'] = base64.b64encode(image_file.read())
            product.sudo().write(vals)
            # Additional images
            extra_images = request.httprequest.files.getlist('extra_images')
            for img in extra_images:
                if img and img.filename:
                    request.env['product.image'].sudo().create({
                        'product_tmpl_id': product.id,
                        'image_1920': base64.b64encode(img.read()),
                        'name': img.filename,
                    })
        except Exception as e:
            _logger.error('Product edit error: %s', e)
        return request.redirect('/my/vendor/products')

    # ── Reviews ────────────────────────────────────────────────────
    @http.route('/my/vendor/reviews', type='http', auth='user', website=True)
    def vendor_reviews(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        reviews = request.env['rating.rating'].sudo().search([
            ('res_model', '=', 'uellow.vendor'),
            ('res_id', '=', vendor.id),
        ], limit=30, order='create_date desc')
        return request.render('uellow_multivendor.portal_vendor_reviews', {
            'vendor': vendor,
            'reviews': reviews,
            'page_name': 'vendor_reviews',
        })

    # ── Wallet statement ───────────────────────────────────────────
    @http.route('/my/vendor/wallet/statement', type='http', auth='user', website=True)
    def vendor_wallet_statement(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        transactions = []
        if vendor.wallet_id:
            transactions = request.env['uellow.wallet.transaction'].sudo().search([
                ('wallet_id', '=', vendor.wallet_id.id)
            ], limit=100, order='date desc')
        return request.render('uellow_multivendor.portal_vendor_statement', {
            'vendor': vendor,
            'transactions': transactions,
            'page_name': 'vendor_wallet',
        })

    # ── Public store page ──────────────────────────────────────────
    @http.route('/store/<string:slug>', type='http', auth='public', website=True)
    def store_page(self, slug, **kw):
        vendor = request.env['uellow.vendor'].sudo().search([
            ('store_slug', '=', slug),
            ('state', '=', 'active'),
        ], limit=1)
        if not vendor:
            return request.not_found()
        store_rec = request.env['uellow.vendor.store'].sudo().search([
            ('vendor_id', '=', vendor.id)], limit=1)
        if store_rec and hasattr(store_rec, 'store_page_enabled') and not store_rec.store_page_enabled:
            return request.not_found()
        products = request.env['product.template'].sudo().search([
            ('vendor_id', '=', vendor.id),
            ('website_published', '=', True),
        ], limit=60)
        return request.render('uellow_multivendor.store_page', {
            'vendor': vendor,
            'products': products,
        })
