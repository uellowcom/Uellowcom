# -*- coding: utf-8 -*-
"""Google Merchant Center product feeds (RSS 2.0 + g: namespace), bilingual.

14k+ products → generated in the BACKGROUND (cron) to per-language files; the
controller just streams them so neither users nor the Merchant crawler wait."""
import html
import os
import tempfile

from odoo import api, models

GMC_DIR = '/tmp/uc_gmc'
GMC_FILES = {
    'ar_001': GMC_DIR + '/google-merchant-ar.xml',
    'en_US': GMC_DIR + '/google-merchant-en.xml',
}
# Back-compat: /google-merchant.xml serves the Arabic feed (site default).
GMC_FILE = GMC_FILES['ar_001']


def _esc(s):
    return html.escape(s or '', quote=False)


class ProductTemplateGMC(models.Model):
    _inherit = 'product.template'

    @api.model
    def _uc_build_gmc_feed(self, lang='ar_001'):
        out = GMC_FILES.get(lang, GMC_FILE)
        icp = self.env['ir.config_parameter'].sudo()
        base = (icp.get_param('web.base.url') or '').rstrip('/').replace('http://', 'https://')
        cur = self.env.company.currency_id.name or 'KWD'
        dom = [('is_published', '=', True), ('sale_ok', '=', True),
               ('website_published', '=', True), ('list_price', '>', 0)]
        P = self.sudo().with_context(lang=lang)
        ids = P.search(dom).ids
        os.makedirs(GMC_DIR, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=GMC_DIR)
        count = 0
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n<channel>\n'
                    '<title>Uellow يلو</title><link>%s/</link>'
                    '<description>Uellow product feed</description>\n' % base)
            for i in range(0, len(ids), 800):
                chunk = P.browse(ids[i:i + 800])
                for t in chunk:
                    try:
                        price = float(t.list_price or 0)
                        name = _esc((t.name or '').strip())
                        if not name or price <= 0:
                            continue
                        url = base + (t.website_url or ('/shop/%s' % t.id))
                        wd = t.write_date or t.create_date
                        uq = wd.strftime('%Y%m%d%H%M%S') if wd else ''
                        img = '%s/web/image/product.template/%s/image_1920?unique=%s' % (base, t.id, uq)
                        cmp_ = float(getattr(t, 'compare_list_price', 0) or 0)
                        desc = _esc((t.description_sale or t.name or '').strip()[:4900])
                        brand = _esc(getattr(t.dr_brand_value_id, 'name', '') or '')
                        bc = (t.barcode or '').strip()
                        gtin = bc if (bc.isdigit() and len(bc) in (8, 12, 13, 14)) else ''
                        mpn = _esc((t.default_code or '').strip())
                        pc = t.public_categ_ids[:1]
                        ptype = _esc((pc.display_name or '').replace(' / ', ' > ')) if pc else ''
                        parts = ['<item>',
                                 '<g:id>%s</g:id>' % t.id,
                                 '<title>%s</title>' % name,
                                 '<description>%s</description>' % desc,
                                 '<link>%s</link>' % _esc(url),
                                 '<g:image_link>%s</g:image_link>' % _esc(img),
                                 '<g:availability>in_stock</g:availability>',
                                 '<g:condition>new</g:condition>']
                        if cmp_ > price:
                            parts.append('<g:price>%.3f %s</g:price>' % (cmp_, cur))
                            parts.append('<g:sale_price>%.3f %s</g:sale_price>' % (price, cur))
                        else:
                            parts.append('<g:price>%.3f %s</g:price>' % (price, cur))
                        if brand:
                            parts.append('<g:brand>%s</g:brand>' % brand)
                        if gtin:
                            parts.append('<g:gtin>%s</g:gtin>' % gtin)
                        if mpn:
                            parts.append('<g:mpn>%s</g:mpn>' % mpn)
                        if ptype:
                            parts.append('<g:product_type>%s</g:product_type>' % ptype)
                        if not gtin and not mpn and not brand:
                            parts.append('<g:identifier_exists>no</g:identifier_exists>')
                        parts.append('</item>\n')
                        f.write(''.join(parts))
                        count += 1
                    except Exception:
                        continue
                self.env.invalidate_all()
            f.write('</channel>\n</rss>\n')
        os.replace(tmp, out)
        return count

    @api.model
    def _uc_build_gmc_feeds(self):
        """Build every language feed (called by cron)."""
        total = 0
        for lang in ('ar_001', 'en_US'):
            try:
                total += self._uc_build_gmc_feed(lang)
            except Exception:
                pass
        return total
