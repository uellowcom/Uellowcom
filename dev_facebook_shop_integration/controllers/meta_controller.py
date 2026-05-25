from odoo import http,fields
from odoo.http import request, Response
import csv
import io
import ast
from lxml import etree

class CsvExportController(http.Controller):

    @http.route('/<int:feed_id>/product/<string:file_type>', type='http', auth='public', csrf=False)
    def download_feed(self, feed_id, file_type, **kwargs):
        # Validate file_type
        if file_type not in ['csv', 'tsv']:
            return Response("Invalid file type", status=400)

        # Set mimetype and separator
        mimetype = 'text/csv;charset=utf-8' \
            if file_type == 'csv' \
            else 'text/tab-separated-values;charset=utf-8'
        separator = ',' if file_type == 'csv' else '\t'

        output = io.StringIO()
        writer = csv.writer(output, delimiter=separator)

        # 1. HEADER
        shop_fields = request.env['shop.fields'].sudo().search([])
        field_names = [field.name for field in shop_fields]
        writer.writerow(field_names)

        # 2. BODY
        feed_data = request.env['facebook.product.data.feed'].sudo().browse(feed_id)
        if not feed_data.exists():
            return Response("Feed data not found.", status=404)

        model_name = feed_data.shop_model_id.model
        domain = ast.literal_eval(feed_data.shop_model_domain or "[]")
        records = request.env[model_name].sudo().search(domain)
        is_variant_model = model_name == 'product.product'
        for rec in records:
            template = rec.product_tmpl_id if is_variant_model else rec
            variant = rec if is_variant_model else rec.product_variant_id
            fb_category_id = (
                                 rec.facebook_category_id.code if is_variant_model else template.facebook_category_id.code) or ''
            google_category_id = (
                                     rec.google_category_id.code if is_variant_model else template.google_category_id.code) or ''
            mpn = rec.mpn if is_variant_model else template.mpn
            gtin = rec.gtin if is_variant_model else template.gtin
            values = {
                'id': rec.id,
                'title': template.name or '',
                'description': template.description_sale or '',
                'availability': 'in stock' if hasattr(template,'qty_available') and template.qty_available > 0 else 'out of stock',
                'condition': template.condition or '',
                'price': (
                    f'{template.list_price:.2f}{template.currency_id.name}'
                    if template.list_price and template.currency_id else ''
                ),
                'link': f"{request.httprequest.scheme}://{request.httprequest.host}/shop/product/{template.id}",
                'image_link': f"{request.httprequest.scheme}://{request.httprequest.host}/web/image/product.template/{template.id}/image_1920",
                'brand': getattr(template.brand_id, 'name', ''),
                'fb_product_category': fb_category_id,
                'google_product_category': google_category_id,
                'mpn': mpn or '',
                'gtin': gtin or '',
                'rich_text_description' : template.description,
            }
            pricelist = feed_data.sale_pricelist_id
            if pricelist:
                new_price = pricelist._get_products_price(template, quantity=1.0, date_order=fields.Date.today()).get(
                    template.id)
                currency = pricelist.currency_id or template.currency_id
                values['sale_price'] = f'{new_price:.2f}{currency.name if currency else ""}'
                for item in pricelist.item_ids:
                    start_date = item.date_start
                    end_date = item.date_end
                    start_str = start_date.isoformat() if start_date else ''
                    end_str = end_date.isoformat() if end_date else ''
                    values['sale_price_effective_date'] = f"{start_str}/{end_str}"
            media_items = rec.product_variant_image_ids if is_variant_model else rec.product_template_image_ids
            image_links = []
            for media in media_items:
                if media.image_1920 and not media.video_url:
                    image_url = f"{request.httprequest.host_url.rstrip('/')}/web/image/product.image/{media.id}/image_1024"
                    image_links.append(image_url)
            values['additional_image_link'] = ','.join(image_links)
            video_links = {}
            video_raw_urls = []
            for idx, media in enumerate(media_items[:20]):
                if media.video_url:
                    video_links[f"video[{idx}].url"] = media.video_url
                    video_raw_urls.append(media.video_url)
            for field in field_names:
                if field.startswith("video[") and field.endswith("].url"):
                    values[field] = video_links.get(field, '')
            if 'video_url' in field_names and 'video_url' not in values:
                values['video_url'] = ','.join(video_raw_urls)
            for extra in field_names:
                if extra not in values:
                    try:
                        val = template[extra]
                        if hasattr(val, '_name'):
                            val = ','.join(val.mapped('name'))
                        values[extra] = val or ''
                    except Exception:
                        values[extra] = ''
            writer.writerow([values.get(col, '') for col in field_names])
        # 3. RESPONSE
        return Response(
            output.getvalue(),
            content_type=mimetype,
            headers=[('Content-Disposition', f'attachment; filename="product_feed_{feed_id}.{file_type}"')]
        )

    @http.route('/<int:feed_id>/product/xml', type='http', auth='public', csrf=False)
    def download_xml(self, feed_id, **kwargs):
        feed_data = request.env['facebook.product.data.feed'].sudo().browse(feed_id)
        if not feed_data.exists():
            return Response("Feed data not found.", status=404)
        model_name = feed_data.shop_model_id.model
        domain = ast.literal_eval(feed_data.shop_model_domain or "[]")
        records = request.env[model_name].sudo().search(domain)
        is_variant_model = model_name == 'product.product'
        shop_fields = request.env['shop.fields'].sudo().search([])
        field_names = [field.name for field in shop_fields]
        rss = etree.Element("rss", nsmap={"g": "http://base.google.com/ns/1.0"}, version="2.0")
        channel = etree.SubElement(rss, "channel")
        etree.SubElement(channel, "title").text = "Product Feed"
        etree.SubElement(channel, "link").text = request.httprequest.host_url.rstrip('/')
        etree.SubElement(channel, "description").text = "Feed for Facebook Catalog"
        for rec in records:
            template = rec.product_tmpl_id if is_variant_model else rec
            variant = rec if is_variant_model else rec.product_variant_id
            fb_category_id = (
                                 rec.facebook_category_id.code if is_variant_model else template.facebook_category_id.code) or ''
            google_category_id = (
                                     rec.google_category_id.code if is_variant_model else template.google_category_id.code) or ''
            mpn = rec.mpn if is_variant_model else template.mpn
            gtin = rec.gtin if is_variant_model else template.gtin

            values = {
                'id': rec.id,
                'title': template.name or '',
                'description': template.description_sale or '',
                'availability': 'in stock' if hasattr(template,'qty_available') and template.qty_available > 0 else 'out of stock',
               'condition': template.condition or '',
                'price': (
                    f'{template.list_price:.2f}{template.currency_id.name}'
                    if template.list_price and template.currency_id else ''
                ),
                'link': f"{request.httprequest.scheme}://{request.httprequest.host}/shop/product/{template.id}",
                'image_link': f"{request.httprequest.scheme}://{request.httprequest.host}/web/image/product.template/{template.id}/image_1920",
                'brand': getattr(template.brand_id, 'name', ''),
                'fb_product_category': fb_category_id,
                'google_product_category': google_category_id,
                'mpn': mpn or '',
                'gtin': gtin or '',
                'rich_text_description': template.description,
            }
            pricelist = feed_data.sale_pricelist_id
            if pricelist:
                new_price = pricelist._get_products_price(template, quantity=1.0, date_order=fields.Date.today()).get(
                    template.id)
                currency = pricelist.currency_id or template.currency_id
                values['sale_price'] = f'{new_price:.2f}{currency.name if currency else ""}'
                for item in pricelist.item_ids:
                    if item.date_start and item.date_end:
                        values[
                            'sale_price_effective_date'] = f"{item.date_start.isoformat()}/{item.date_end.isoformat()}"
            media_items = rec.product_variant_image_ids if is_variant_model else rec.product_template_image_ids
            image_links = []
            video_links = {}
            video_raw_urls = []
            for idx, media in enumerate(media_items):
                if media.image_1920 and not media.video_url:
                    image_url = f"{request.httprequest.host_url.rstrip('/')}/web/image/product.image/{media.id}/image_1024"
                    image_links.append(image_url)
                if media.video_url and idx < 20:
                    video_links[f"video[{idx}].url"] = media.video_url
                    video_raw_urls.append(media.video_url)

            values['additional_image_link'] = ','.join(image_links)
            for field in field_names:
                if field.startswith("video[") and field.endswith("].url"):
                    values[field] = video_links.get(field, '')
            if 'video_url' in field_names and 'video_url' not in values:
                values['video_url'] = ','.join(video_raw_urls)

            # Extra dynamic fields
            for extra in field_names:
                if extra not in values:
                    try:
                        val = template[extra]
                        if hasattr(val, '_name'):
                            val = ','.join(val.mapped('name'))
                        values[extra] = val or ''
                    except Exception:
                        values[extra] = ''

            item = etree.SubElement(channel, "item")
            for field in field_names:
                tag = f"{{http://base.google.com/ns/1.0}}{field}"
                etree.SubElement(item, tag).text = str(values.get(field, ''))

        xml_bytes = etree.tostring(rss, pretty_print=True, xml_declaration=True, encoding="UTF-8")
        return Response(xml_bytes, content_type='application/xml')
