"""Scans ir.attachment for image attachments above a size threshold and
records issues. Optionally auto-resizes them with PIL (downscale + JPEG
quality 85).
"""
import base64
import io
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PerfImageIssue(models.Model):
    _name = 'uellow.perf.image.issue'
    _description = 'Uellow Performance — oversized image'
    _order = 'size_kb desc'

    attachment_id = fields.Many2one('ir.attachment', ondelete='cascade',
        required=True, index=True)
    name = fields.Char(related='attachment_id.name', store=True)
    mimetype = fields.Char(related='attachment_id.mimetype', store=True)
    size_kb = fields.Integer(index=True)
    width = fields.Integer()
    height = fields.Integer()
    fixed = fields.Boolean(default=False, index=True)
    fixed_size_kb = fields.Integer()
    last_scanned = fields.Datetime(default=fields.Datetime.now)

    _sql_constraints = [
        ('attachment_unique', 'unique(attachment_id)',
         'One issue row per attachment.'),
    ]

    @api.model
    def cron_scan(self, limit=200):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        threshold_kb = max(50, int(cfg.image_size_threshold_kb or 500))

        # Fast SQL — only image MIME types not already flagged + fixed
        self.env.cr.execute("""
            SELECT a.id, COALESCE(a.file_size, 0) AS size
            FROM ir_attachment a
            LEFT JOIN uellow_perf_image_issue i
                ON i.attachment_id = a.id AND i.fixed = TRUE
            WHERE a.mimetype LIKE 'image/%%'
              AND COALESCE(a.file_size, 0) >= %s
              AND i.id IS NULL
            ORDER BY a.file_size DESC
            LIMIT %s
        """, [threshold_kb * 1024, limit])
        n = 0
        for row in self.env.cr.fetchall():
            att_id, size = row
            w, h = 0, 0
            try:
                from PIL import Image
                att = self.env['ir.attachment'].sudo().browse(att_id)
                if att.datas:
                    raw = base64.b64decode(att.datas)
                    im = Image.open(io.BytesIO(raw))
                    w, h = im.size
            except Exception:
                pass
            existing = self.sudo().search(
                [('attachment_id', '=', att_id)], limit=1)
            vals = {'attachment_id': att_id, 'size_kb': size // 1024,
                    'width': w, 'height': h, 'last_scanned': fields.Datetime.now()}
            if existing:
                existing.write(vals)
            else:
                self.create(vals)
            n += 1
        if n:
            self.env['uellow.perf.alert'].sudo().fire(
                'image', 'warning',
                f'{n} oversized images found (≥ {threshold_kb} KB)')
        return n

    def action_optimize(self):
        """Downscale + recompress as JPEG quality 85 in-place."""
        from PIL import Image
        for r in self:
            try:
                att = r.attachment_id
                if not att or not att.datas:
                    continue
                raw = base64.b64decode(att.datas)
                im = Image.open(io.BytesIO(raw))
                im = im.convert('RGB')
                # Downscale if either dimension > 1600
                max_side = 1600
                if max(im.size) > max_side:
                    im.thumbnail((max_side, max_side), Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, format='JPEG', quality=85, optimize=True)
                data = buf.getvalue()
                att.sudo().write({
                    'datas': base64.b64encode(data),
                    'mimetype': 'image/jpeg',
                })
                r.fixed = True
                r.fixed_size_kb = len(data) // 1024
                r.width, r.height = im.size
            except Exception as e:
                _logger.warning('image optimize failed for %s: %s', r.id, e)
        return True
