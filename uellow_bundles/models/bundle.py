"""v2.2.20 — PRODUCT BUNDLES.

A bundle groups several products under ONE price. Publishing a bundle
creates (and keeps in sync) a real sellable `product.template`, so the
whole existing machinery works untouched: one cart line, one card in
every block, normal links, coupons, shipping, ranking…

Design highlights:
* pricing: fixed price OR percent-off the components' total — savings
  are computed and shown everywhere.
* availability FAILS CLOSED: the bundle is buyable only while EVERY
  component is buyable (in stock or allow-out-of-stock); checked again
  at add-to-cart time so a card cached seconds earlier can't oversell.
* the synced product carries the union of the components' categories so
  bundles surface naturally in category browsing.
* at order confirmation the components are written into the order log
  (and each bundle line keeps `uellow_bundle_id`) so fulfilment always
  knows exactly what to pick.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class UellowBundle(models.Model):
    _name = 'uellow.bundle'
    _description = 'Product Bundle'
    _order = 'sequence, id desc'

    name = fields.Char('Name (EN)', required=True)
    name_ar = fields.Char('Name (AR)')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    state = fields.Selection([
        ('draft', '📝 Draft'),
        ('published', '🟢 Published'),
    ], default='draft', required=True, copy=False)

    description_en = fields.Text('Description (EN)')
    description_ar = fields.Text('Description (AR)')
    image_1920 = fields.Image('Cover image', max_width=1920,
        help='Empty = the first component\'s image is used.')

    line_ids = fields.One2many('uellow.bundle.line', 'bundle_id',
                               string='Components', copy=True)

    # ── pricing ──────────────────────────────────────────────────────
    pricing_mode = fields.Selection([
        ('fixed', '💰 One fixed price'),
        ('percent', '🏷 Percent off the components total'),
    ], default='fixed', required=True)
    bundle_price = fields.Float('Bundle price')
    discount_pct = fields.Float('Discount %', default=15.0)
    components_total = fields.Float(compute='_compute_pricing', store=False,
                                    string='Components total')
    final_price = fields.Float(compute='_compute_pricing', store=False,
                               string='Final price')
    savings = fields.Float(compute='_compute_pricing', store=False)
    savings_pct = fields.Integer(compute='_compute_pricing', store=False,
                                 string='Savings %')

    # ── presentation ────────────────────────────────────────────────
    badge_en = fields.Char('Badge (EN)', default='Bundle')
    badge_ar = fields.Char('Badge (AR)', default='باقة')
    badge_color = fields.Char('Badge color', default='#7C3AED')
    show_components_price = fields.Boolean(
        'Show each component\'s own price', default=True,
        help='On the product page, components show their individual '
             '(struck-through) prices next to the bundle price.')

    # ── gallery (v2.2.21) ───────────────────────────────────────────
    gallery_mode = fields.Selection([
        ('merge', '🖼 Merge — cover + every component\'s photos & videos'),
        ('cover', '🎯 Cover only — just the bundle image'),
    ], default='merge', required=True, string='Gallery',
        help='Merge builds the bundle\'s gallery from all the components\' '
             'images AND videos, so the customer sees everything inside.')

    # ── out-of-stock behaviour (v2.2.21) ────────────────────────────
    oos_behavior = fields.Selection([
        ('badge', '🚫 Show "Unavailable" badge + block buying (stay listed)'),
        ('hide', '🙈 Hide & unpublish until back in stock'),
        ('sell', '✅ Keep selling anyway (backorder)'),
    ], default='badge', required=True, string='If a component runs out',
        help='What happens when ANY component is out of stock. '
             '"Badge" keeps the bundle visible but not buyable with a clear '
             'message; "Hide" pulls it from the app; "Keep selling" ignores '
             'stock (use only for made-to-order / backorder bundles).')
    unavailable_en = fields.Char('Unavailable message (EN)',
        default='Temporarily unavailable — an item in this bundle is out of '
                'stock.')
    unavailable_ar = fields.Char('Unavailable message (AR)',
        default='غير متوفر مؤقتاً — أحد منتجات الباقة نفد من المخزون.')

    # ── targeting / limits ──────────────────────────────────────────
    website_ids = fields.Many2many('website', string='Websites',
        help='Empty = every country site.')
    date_from = fields.Datetime('Starts')
    date_to = fields.Datetime('Ends')
    max_per_order = fields.Integer('Max qty per order',
        help='0 = unlimited.')

    product_tmpl_id = fields.Many2one('product.template',
        string='Sellable product', readonly=True, copy=False,
        help='Auto-created on publish; this is what customers buy.')
    available = fields.Boolean(compute='_compute_available', store=False,
        string='All components available')
    component_count = fields.Integer(compute='_compute_counts')
    items_total_qty = fields.Integer(compute='_compute_counts',
                                     string='Total pieces')

    _sql_constraints = [
        ('price_positive',
         'CHECK (bundle_price >= 0 AND discount_pct >= 0 '
         'AND discount_pct < 100)',
         'Bundle price must be ≥ 0 and discount below 100%.'),
    ]

    # ── computes ─────────────────────────────────────────────────────

    @api.depends('line_ids.product_tmpl_id', 'line_ids.qty',
                 'pricing_mode', 'bundle_price', 'discount_pct')
    def _compute_pricing(self):
        for b in self:
            total = sum((l.product_tmpl_id.list_price or 0) * (l.qty or 1)
                        for l in b.line_ids)
            b.components_total = total
            if b.pricing_mode == 'percent':
                b.final_price = round(total * (1 - (b.discount_pct or 0)
                                               / 100.0), 3)
            else:
                b.final_price = b.bundle_price or 0.0
            b.savings = max(0.0, total - b.final_price)
            b.savings_pct = int(round(b.savings / total * 100)) \
                if total else 0

    def _compute_counts(self):
        for b in self:
            b.component_count = len(b.line_ids)
            b.items_total_qty = int(sum(l.qty or 1 for l in b.line_ids))

    @api.depends('line_ids.product_tmpl_id')
    def _compute_available(self):
        for b in self:
            b.available = b._is_available()

    def _is_available(self):
        """FAIL CLOSED: every component must be buyable right now."""
        self.ensure_one()
        if not self.line_ids:
            return False
        for l in self.line_ids:
            t = l.product_tmpl_id
            if not t or not t.active or not t.is_published:
                return False
            if getattr(t, 'allow_out_of_stock_order', True):
                continue
            if getattr(t, 'is_storable', t.type == 'consu') \
                    and (t.qty_available or 0) < (l.qty or 1):
                return False
        return True

    def _window_open(self, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        if self.date_from and now < self.date_from:
            return False
        if self.date_to and now > self.date_to:
            return False
        return True

    def _buyable(self):
        """Can the customer actually add this bundle to the cart RIGHT NOW?
        'sell' bundles ignore component stock (backorder); the others need
        every component available + the schedule window open."""
        self.ensure_one()
        if not self._window_open():
            return False
        if self.oos_behavior == 'sell':
            return True
        return self._is_available()

    def _listing_state(self):
        """How feeds should treat this bundle:
        'ok' (show + buyable) / 'badge' (show, not buyable, unavailable
        message) / 'hidden' (drop from feeds)."""
        self.ensure_one()
        if self._buyable():
            return 'ok'
        if self.oos_behavior == 'hide':
            return 'hidden'
        return 'badge'

    # ── keep the synced product's published flag honest ──────────────

    def _sync_published_flag(self):
        """For 'hide' bundles, the sellable product is published only while
        buyable; others stay published (badge/sell handle availability in
        the UI). Run on stock moves (cron) + on write."""
        for b in self.filtered(lambda x: x.product_tmpl_id
                               and x.state == 'published'):
            should = b.active and (
                b.oos_behavior != 'hide' or b._buyable())
            if b.product_tmpl_id.is_published != should:
                b.product_tmpl_id.sudo().with_context(
                    bundle_no_sync=True).is_published = should

    @api.model
    def _cron_sync_availability(self):
        """Periodic: flip 'hide' bundles' published flag as component stock
        changes (stock moves don't write the bundle, so a cron keeps the
        storefront honest)."""
        self.sudo().search([('state', '=', 'published')]) \
            ._sync_published_flag()

    # ── publish / sync ───────────────────────────────────────────────

    def action_publish(self):
        for b in self:
            if not b.line_ids:
                raise UserError('Add at least one component first.')
            if b.pricing_mode == 'fixed' and b.bundle_price <= 0:
                raise UserError('Set the bundle price first.')
            b._sync_product()
            b.state = 'published'
            b._sync_published_flag()

    def action_unpublish(self):
        for b in self:
            if b.product_tmpl_id:
                b.product_tmpl_id.sudo().write({'is_published': False})
            b.state = 'draft'

    def write(self, vals):
        res = super().write(vals)
        # keep the synced product fresh on every relevant edit
        sync_keys = {'name', 'name_ar', 'line_ids', 'pricing_mode',
                     'bundle_price', 'discount_pct', 'image_1920',
                     'description_en', 'description_ar', 'website_ids',
                     'active', 'gallery_mode'}
        if sync_keys & set(vals) and not self.env.context.get(
                'bundle_no_sync'):
            for b in self.filtered(lambda x: x.state == 'published'
                                   and x.product_tmpl_id):
                b._sync_product()
        if not self.env.context.get('bundle_no_sync') and (
                sync_keys & set(vals) or 'oos_behavior' in vals
                or 'date_from' in vals or 'date_to' in vals):
            self._sync_published_flag()
        return res

    def _sync_product(self):
        """Create/update the sellable product behind this bundle."""
        self.ensure_one()
        Tmpl = self.env['product.template'].sudo()
        categs = self.line_ids.mapped(
            'product_tmpl_id.public_categ_ids')
        image = self.image_1920
        if not image and self.line_ids:
            image = self.line_ids[0].product_tmpl_id.image_1920
        desc = self.description_en or ''
        vals = {
            'name': self.name,
            'type': 'consu',
            'is_storable': False,        # stock lives on the components
            'list_price': self.final_price,
            'compare_list_price': self.components_total
                if self.components_total > self.final_price else 0,
            'is_published': bool(self.active),
            'website_id': False,
            'public_categ_ids': [(6, 0, categs.ids)],
            'description_sale': desc,
            'image_1920': image,
            'is_bundle': True,
            'uellow_bundle_id': self.id,
        }
        if self.product_tmpl_id:
            self.product_tmpl_id.write(vals)
        else:
            self.with_context(bundle_no_sync=True).product_tmpl_id = \
                Tmpl.create(vals)
        t = self.product_tmpl_id
        # AR translation for the product name (bilingual rule)
        try:
            if self.name_ar:
                t.with_context(lang='ar_001').name = self.name_ar
            if self.description_ar:
                t.with_context(lang='ar_001').description_sale = \
                    self.description_ar
        except Exception:
            pass
        return t

    # ── serialization for the mobile API / blocks ────────────────────

    def _oos_item_names(self):
        """Names of components currently out of stock (for the message)."""
        self.ensure_one()
        out = []
        for l in self.line_ids:
            t = l.product_tmpl_id
            if not t:
                continue
            if getattr(t, 'allow_out_of_stock_order', True):
                continue
            if getattr(t, 'is_storable', t.type == 'consu') \
                    and (t.qty_available or 0) < (l.qty or 1):
                out.append(t.name)
        return out

    def _gallery(self, lang='en_US'):
        """v2.2.21 — merged gallery: bundle cover first, then every
        component's main image, extra images AND videos, de-duplicated."""
        self.ensure_one()
        imgs, vids, seen = [], [], set()

        def add_img(model, rid, field, wd):
            key = (model, rid, field)
            if key in seen:
                return
            seen.add(key)
            imgs.append('/web/image/%s/%d/%s?unique=%s'
                        % (model, rid, field, wd))

        if self.image_1920:
            add_img('uellow.bundle', self.id, 'image_1920', self.write_date)
        for l in self.line_ids:
            t = l.product_tmpl_id
            if not t:
                continue
            add_img('product.template', t.id, 'image_1920', t.write_date)
            for extra in t.product_template_image_ids[:8]:
                add_img('product.image', extra.id, 'image_1920',
                        extra.write_date)
            # component videos — must mirror _serialize_product_videos so
            # Bunny Stream (HLS) and direct uploads actually PLAY in the
            # bundle gallery (the old dict left embed_url/file_url empty for
            # bunny videos → the player had nothing to load → "video doesn't
            # work in bundles").
            try:
                tvids = (getattr(t, 'video_ids', None)
                         or getattr(t, 'product_video_ids', None))
                for v in (tvids or []).filtered(
                        lambda x: getattr(x, 'active', True)):
                    vids.append(self._video_dict(v))
            except Exception:
                pass
        return {'images': imgs, 'videos': vids}

    def _video_dict(self, v):
        """Serialize a product.video the SAME way the mobile API does, incl.
        Bunny Stream playback URL + iframe embed and direct-upload file URL."""
        item = {
            'id': v.id,
            'title': v.name or '',
            'type': getattr(v, 'video_type', '') or 'youtube',
            'embed_url': getattr(v, 'embed_url', '') or '',
            'tiktok_url': getattr(v, 'tiktok_url', '') or '',
            'tiktok_video_id': getattr(v, 'tiktok_video_id', '') or '',
            'video_url': getattr(v, 'video_url', '') or '',
            'thumbnail': (
                '/web/image/product.video/%d/thumbnail?unique=%s'
                % (v.id, v.write_date)) if getattr(v, 'thumbnail', False) else '',
        }
        if getattr(v, 'video_type', '') == 'direct_upload' and getattr(v, 'video_file', False):
            fname = (getattr(v, 'video_filename', '') or 'video.mp4').replace('/', '-')
            item['file_url'] = '/web/content/product.video/%d/video_file/%s' % (v.id, fname)
            item['mime'] = getattr(v, 'video_mimetype', '') or 'video/mp4'
        if (getattr(v, 'video_type', '') == 'bunny_stream'
                and getattr(v, 'bunny_playback_url', '')):
            item['file_url'] = v.bunny_playback_url
            item['mime'] = 'application/vnd.apple.mpegurl'
            gid = (getattr(v, 'bunny_video_id', '') or '').strip()
            lib = (self.env['ir.config_parameter'].sudo()
                   .get_param('uellow_cdn_video.bunny_library_id') or '').strip()
            if gid and lib:
                item['embed_url'] = (
                    'https://iframe.mediadelivery.net/embed/%s/%s'
                    '?autoplay=true&preload=true' % (lib, gid))
            if (not item['thumbnail']) and getattr(v, 'bunny_thumb_auto', False):
                item['thumbnail'] = getattr(v, 'bunny_thumb_url', '') or ''
        return item

    def to_mobile_dict(self, lang='en_US', with_components=True):
        self.ensure_one()
        ar = str(lang).lower().startswith('ar')
        out = {
            'id': self.id,
            'product_id': self.product_tmpl_id.id
                if self.product_tmpl_id else None,
            'name': {'en': self.name or '',
                     'ar': self.name_ar or self.name or ''},
            'description': {'en': self.description_en or '',
                            'ar': self.description_ar
                                  or self.description_en or ''},
            'price': self.final_price,
            'components_total': self.components_total,
            'savings': round(self.savings, 3),
            'savings_pct': self.savings_pct,
            'badge': {'en': self.badge_en or 'Bundle',
                      'ar': self.badge_ar or 'باقة',
                      'color': self.badge_color or '#7C3AED'},
            'component_count': self.component_count,
            'items_total_qty': self.items_total_qty,
            'available': self._buyable(),
            'oos_behavior': self.oos_behavior,
            'listing_state': self._listing_state(),
            'unavailable_msg': {
                'en': self.unavailable_en or 'Temporarily unavailable.',
                'ar': self.unavailable_ar or 'غير متوفر مؤقتاً.',
            },
            'out_of_stock_items': self._oos_item_names(),
            'show_components_price': self.show_components_price,
            'ends_at': self.date_to.isoformat() if self.date_to else None,
        }
        if with_components:
            items = []
            for l in self.line_ids:
                t = l.product_tmpl_id
                items.append({
                    'product_id': t.id,
                    'name': {
                        'en': t.name or '',
                        'ar': t.with_context(lang='ar_001').name
                              or t.name or '',
                    },
                    'qty': int(l.qty or 1),
                    'unit_price': t.list_price or 0,
                    'line_total': (t.list_price or 0) * (l.qty or 1),
                    'image': '/web/image/product.template/%d/image_256'
                             '?unique=%s' % (t.id, t.write_date),
                })
            out['items'] = items
            # merged gallery only on the full payload (heavy for cards)
            if self.gallery_mode == 'merge':
                out['gallery'] = self._gallery(lang)
        return out


class UellowBundleLine(models.Model):
    _name = 'uellow.bundle.line'
    _description = 'Bundle Component'
    _order = 'sequence, id'

    bundle_id = fields.Many2one('uellow.bundle', required=True,
                                ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    product_tmpl_id = fields.Many2one('product.template', required=True,
        string='Product', domain=[('is_bundle', '=', False)])
    qty = fields.Integer('Qty', default=1)
    unit_price = fields.Float(related='product_tmpl_id.list_price',
                              string='Unit price')
    line_total = fields.Float(compute='_compute_total', string='Total')

    _sql_constraints = [
        ('qty_positive', 'CHECK (qty > 0)', 'Quantity must be positive.'),
    ]

    @api.depends('product_tmpl_id.list_price', 'qty')
    def _compute_total(self):
        for l in self:
            l.line_total = (l.product_tmpl_id.list_price or 0) * (l.qty or 1)


class ProductTemplateBundle(models.Model):
    _inherit = 'product.template'

    is_bundle = fields.Boolean('Is a bundle', default=False, copy=False,
                               index=True)
    uellow_bundle_id = fields.Many2one('uellow.bundle', string='Bundle',
                                       copy=False, ondelete='set null')


class SaleOrderLineBundle(models.Model):
    _inherit = 'sale.order.line'

    uellow_bundle_id = fields.Many2one('uellow.bundle', string='Bundle',
                                       copy=False)


class SaleOrderBundle(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Stamp bundle lines + log the component breakdown so fulfilment
        always knows what to pick."""
        res = super().action_confirm()
        for order in self:
            notes = []
            for l in order.order_line:
                t = l.product_id.product_tmpl_id if l.product_id else None
                b = t and t.uellow_bundle_id
                if not (t and t.is_bundle and b):
                    continue
                if not l.uellow_bundle_id:
                    l.uellow_bundle_id = b.id
                parts = ', '.join('%d× %s' % (cl.qty,
                                              cl.product_tmpl_id.name)
                                  for cl in b.line_ids)
                notes.append('🎁 %s ×%d → %s' % (
                    b.name, int(l.product_uom_qty or 1), parts))
            if notes:
                try:
                    order.message_post(body='Bundle picking list:<br/>'
                                       + '<br/>'.join(notes))
                except Exception:
                    pass
        return res
