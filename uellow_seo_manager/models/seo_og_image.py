# -*- coding: utf-8 -*-
"""Phase 5 — Open Graph image generator.

Auto-generates a 1200×630 OG image per product (Uellow brand layout +
product photo + name + price). Stored as an ir.attachment so it can be
served via /web/image/<attachment_id> and referenced in og:image.

Why bother:
  • Default WhatsApp/Twitter/Facebook previews look broken without an
    explicit og:image at 1200×630 (the recommended size).
  • Product photos alone aren't optimized for social — text overlay
    with price + CTA dramatically lifts share CTR.

Requires Pillow (already a base Odoo dependency).
"""
import base64
import logging
from io import BytesIO

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None


class ProductTemplateOG(models.Model):
    _inherit = 'product.template'

    seo_og_image_id = fields.Many2one('ir.attachment',
        string='Generated OG image (1200×630)',
        copy=False)

    def action_generate_og_image(self):
        """Build a 1200×630 OG card and store as attachment.
        Single-product call — fast (under 1s), no need to background it."""
        if Image is None:
            _logger.warning('Pillow not installed')
            return False
        ok_count = 0
        for r in self:
            try:
                png = r._build_og_image_png()
                if not png: continue
                Att = self.env['ir.attachment'].sudo()
                if r.seo_og_image_id:
                    r.seo_og_image_id.unlink()
                att = Att.create({
                    'name': f'og-product-{r.id}.png',
                    'datas': base64.b64encode(png),
                    'mimetype': 'image/png',
                    'res_model': 'product.template',
                    'res_id': r.id,
                    'public': True,
                })
                r.seo_og_image_id = att.id
                ok_count += 1
            except Exception:
                _logger.exception('OG gen failed for product %s', r.id)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': '🖼 OG image generated',
                       'message': f'Created {ok_count} OG image(s) (1200×630).',
                       'type': 'success', 'sticky': False},
        }

    def _build_og_image_png(self):
        """Compose: brand strip + product photo + name + price."""
        self.ensure_one()
        # Canvas
        W, H = 1200, 630
        bg = Image.new('RGB', (W, H), (250, 246, 235))  # Uellow cream
        # Brand dark strip on the left
        strip = Image.new('RGB', (W//3, H), (65, 36, 2))
        bg.paste(strip, (0, 0))

        # Product image
        if self.image_1920:
            try:
                pim = Image.open(BytesIO(base64.b64decode(self.image_1920))).convert('RGBA')
                pim.thumbnail((W - 480, H - 80))
                bg.paste(pim, (W//3 + 40, (H - pim.height) // 2),
                         pim if pim.mode == 'RGBA' else None)
            except Exception:
                pass

        # Text
        draw = ImageDraw.Draw(bg)
        try:
            ttl_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVu Sans-Bold.ttf', 56)
            sub_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 32)
            price_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVu Sans-Bold.ttf', 48)
        except Exception:
            # Fallback to default font
            ttl_font = ImageFont.load_default()
            sub_font = ttl_font; price_font = ttl_font

        # Logo / brand text top-left of strip
        draw.text((40, 60), 'Uellow', fill=(245, 195, 32), font=ttl_font)
        draw.text((40, 130), 'Marketplace', fill=(255, 255, 255), font=sub_font)

        # Product name centered-ish on strip
        name = (self.name or '')[:60]
        # Word wrap
        line, lines = '', []
        for w in name.split():
            test = (line + ' ' + w).strip()
            if len(test) > 18:
                lines.append(line)
                line = w
            else:
                line = test
        if line: lines.append(line)
        y = H // 2 - (len(lines) * 36) // 2
        for ln in lines[:4]:
            draw.text((40, y), ln, fill=(255, 255, 255), font=sub_font)
            y += 36

        # Price bottom
        if self.list_price:
            cur = self.currency_id.symbol if self.currency_id else 'KD'
            draw.text((40, H - 100), f'{self.list_price:.3f} {cur}',
                      fill=(245, 195, 32), font=price_font)

        buf = BytesIO()
        bg.save(buf, format='PNG', optimize=True)
        return buf.getvalue()

    @api.model
    def action_seo_og_generate_bulk(self, batch=50):
        """Generate OG images for products that don't have one."""
        recs = self.search([
            ('is_published', '=', True),
            ('seo_og_image_id', '=', False),
            ('image_1920', '!=', False),
        ], limit=batch)
        recs.action_generate_og_image()
        return len(recs)
