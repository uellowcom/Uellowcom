from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class UellowBrandsController(http.Controller):

    @http.route('/uellow/brands', type='json', auth='public', website=True, csrf=False)
    def get_brands(self, **kwargs):
        try:
            cr = request.env.cr

            # جلب البراندات مع access_token للصور الخاصة
            cr.execute("""
                SELECT
                    pav.id,
                    pav.name,
                    att.id           AS att_id,
                    att.access_token AS token,
                    att.public       AS is_public
                FROM product_attribute_value pav
                LEFT JOIN ir_attachment att
                    ON att.res_model = 'product.attribute.value'
                    AND att.res_id   = pav.id
                    AND att.name     = 'dr_image'
                WHERE pav.attribute_id = 1
                  AND pav.active = true
                ORDER BY pav.sequence, pav.id
            """)

            rows = cr.fetchall()
            brands = []

            for (val_id, name_trans, att_id, token, is_public) in rows:
                if not att_id:
                    continue

                if isinstance(name_trans, dict):
                    name = (name_trans.get('ar_001')
                            or name_trans.get('en_US')
                            or next(iter(name_trans.values()), ''))
                else:
                    name = str(name_trans or '')

                # بناء URL الصورة:
                # - إذا public: URL بسيط
                # - إذا private + access_token: URL مع token
                # - إذا private بدون token: نستخدم proxy endpoint
                if is_public:
                    image_url = '/web/image/%d' % att_id
                elif token:
                    image_url = '/web/image/%d?access_token=%s' % (att_id, token)
                else:
                    image_url = '/uellow/brand-image/%d' % val_id

                brands.append({
                    'id': val_id,
                    'name': name,
                    'image_url': image_url,
                    'shop_url': '/shop?attribute_value=1-%d' % val_id,
                })

            return {'brands': brands}

        except Exception as e:
            _logger.exception('[UellowBrands] Error: %s', e)
            return {'brands': [], 'error': str(e)}


class UellowBrandsImageProxy(http.Controller):
    """
    Proxy للصور الخاصة — يسمح للزوار برؤية صور البراندات
    بدون الحاجة لتغيير public في ir_attachment
    """

    @http.route('/uellow/brand-image/<int:val_id>', type='http', auth='public', website=True)
    def brand_image(self, val_id, **kwargs):
        cr = request.env.cr
        cr.execute("""
            SELECT att.id
            FROM ir_attachment att
            WHERE att.res_model = 'product.attribute.value'
              AND att.res_id = %s
              AND att.name = 'dr_image'
            LIMIT 1
        """, (val_id,))
        row = cr.fetchone()
        if not row:
            return request.not_found()

        attachment = request.env['ir.attachment'].sudo().browse(row[0])
        if not attachment.exists() or not attachment.raw:
            return request.not_found()

        return http.Response(
            attachment.raw,
            content_type=attachment.mimetype or 'image/png',
            headers=[
                ('Cache-Control', 'public, max-age=604800'),
                ('Content-Length', len(attachment.raw)),
            ]
        )
