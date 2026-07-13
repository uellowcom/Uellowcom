# -*- coding: utf-8 -*-
"""AliExpress Dropshipping (DS) adapter.

Implements the AliExpress Open Platform "system tools" gateway:
  * Gateway:   https://api-sg.aliexpress.com/sync
  * OAuth:     https://api-sg.aliexpress.com/oauth/authorize (code)
               -> /auth/token/create      (code   -> access/refresh token)
               -> /auth/token/refresh      (refresh token -> new access token)
  * Signing:   HMAC-SHA256 over sorted "key+value" concatenation, upper-hex.
               (sign_method=sha256)

DS business methods:
  aliexpress.ds.product.get           - product detail
  aliexpress.ds.recommend.feed.get    - listing / feed
  aliexpress.ds.freight.query         - shipping / landed cost
  aliexpress.ds.order.create          - place dropship order
  aliexpress.ds.order.tracking.get    - tracking
  aliexpress.ds.category.get          - categories

Nothing here runs until a dropship.provider(code='aliexpress') has valid
credentials; the storefront/order flow calls these through the adapter registry.
"""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta

import requests

from odoo import _
from odoo.exceptions import UserError

from .base import DropshipAdapter, register

_logger = logging.getLogger(__name__)

# TOP gateway (dot-methods, e.g. aliexpress.ds.product.get) vs
# OP/REST gateway (slash-methods, e.g. /auth/token/create). See AliExpress
# system-tools spec (verified against the moh3a/ae_sdk reference client).
TOP_URL = "https://api-sg.aliexpress.com/sync"
OP_URL = "https://api-sg.aliexpress.com/rest"
OAUTH_AUTHORIZE = "https://api-sg.aliexpress.com/oauth/authorize"
TOKEN_CREATE = "/auth/token/create"
TOKEN_REFRESH = "/auth/token/refresh"
SIGN_METHOD = "sha256"
TIMEOUT = 30


@register('aliexpress')
class AliExpressAdapter(DropshipAdapter):
    code = 'aliexpress'

    # ------------------------------------------------------------------ #
    # signing + low-level call
    # ------------------------------------------------------------------ #
    def _sign(self, params):
        """HMAC-SHA256 sign per AliExpress system-tools spec.

        Rules (verified against the reference client):
          * For OP/REST methods (name contains '/'), the method PATH is the
            prefix of the base string and is NOT signed as a key/value pair.
          * All other non-null params are sorted by key and concatenated as
            key+value (no separators).
          * HMAC-SHA256 with app_secret, UPPERCASE hex.
        """
        p = dict(params)
        base = ''
        method = p.get('method')
        if isinstance(method, str) and '/' in method:
            base = method
            p.pop('method', None)
        base += ''.join('%s%s' % (k, p[k]) for k in sorted(p) if p[k] is not None)
        secret = (self.provider.app_secret or '').encode('utf-8')
        return hmac.new(secret, base.encode('utf-8'), hashlib.sha256).hexdigest().upper()

    def _call(self, method, biz_params=None, is_token_api=False):
        """Call an AliExpress API method and return the parsed JSON dict.

        Assembles params into the query string and POSTs (empty body), choosing
        the TOP (/sync) or OP (/rest) gateway by the method name style.
        """
        if not self.provider.app_key or not self.provider.app_secret:
            raise UserError(_("AliExpress provider is missing app_key/app_secret."))

        params = {
            'app_key': self.provider.app_key,
            'timestamp': str(int(time.time() * 1000)),
            'sign_method': SIGN_METHOD,
            'simplify': 'true',
            'method': method,
        }
        # business APIs need a valid session; token APIs are called pre-session.
        if not is_token_api:
            self.authenticate()
            params['session'] = self.provider.access_token or ''
        params.update({k: self._stringify(v) for k, v in (biz_params or {}).items()})
        params['sign'] = self._sign(params)

        url = self._assemble(params)
        try:
            resp = requests.post(url, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            _logger.warning("AliExpress call %s failed: %s", method, e)
            raise UserError(_("AliExpress request failed: %s") % e)

        if isinstance(data, dict) and data.get('error_response'):
            err = data['error_response']
            raise UserError(_("AliExpress error %(code)s: %(msg)s") % {
                'code': err.get('code'), 'msg': err.get('msg') or err.get('sub_msg'),
            })
        return data

    @staticmethod
    def _assemble(params):
        """Build the request URL: OP base + path for slash-methods, else TOP."""
        from urllib.parse import quote
        p = dict(params)
        method = p.get('method')
        if isinstance(method, str) and '/' in method:
            base_url = OP_URL + method
            p.pop('method', None)
        else:
            base_url = TOP_URL
        query = '&'.join('%s=%s' % (k, quote(str(p[k]), safe=''))
                         for k in sorted(p) if p[k] is not None)
        return '%s?%s' % (base_url, query)

    @staticmethod
    def _stringify(v):
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if isinstance(v, (dict, list)):
            return json.dumps(v, separators=(',', ':'), ensure_ascii=False)
        return v if isinstance(v, str) else str(v)

    # ------------------------------------------------------------------ #
    # 1. auth
    # ------------------------------------------------------------------ #
    def authorize_url(self):
        """Build the consent URL the admin opens once to grant access.

        ``state`` carries the provider id so the callback can resolve which
        record to store tokens on.
        """
        redirect = self.provider.redirect_uri or ''
        return ("%s?response_type=code&force_auth=true&client_id=%s&redirect_uri=%s&state=%s"
                % (OAUTH_AUTHORIZE, self.provider.app_key or '', redirect, self.provider.id))

    def exchange_code(self, code):
        """Exchange an OAuth ``code`` for access + refresh tokens."""
        data = self._call(TOKEN_CREATE, {'code': code}, is_token_api=True)
        return self._store_token(data)

    def authenticate(self):
        """Ensure a non-expired access token; refresh if within 5 min of expiry."""
        p = self.provider
        if not p.access_token:
            raise UserError(_("AliExpress not authorized yet. Open the Authorize URL first."))
        if p.token_expiry and p.token_expiry <= datetime.now() + timedelta(minutes=5):
            if not p.refresh_token:
                raise UserError(_("AliExpress token expired and no refresh_token stored."))
            data = self._call(TOKEN_REFRESH, {'refresh_token': p.refresh_token}, is_token_api=True)
            self._store_token(data)
        return True

    def _store_token(self, data):
        # token payload keys vary slightly across gateway versions; be lenient.
        body = data.get('aliexpress_ds_token_create_response') or data
        if isinstance(body, dict) and 'result' in body:
            body = body['result']
        access = body.get('access_token')
        refresh = body.get('refresh_token')
        expires_in = int(body.get('expires_in') or body.get('expire_time') or 0)
        vals = {}
        if access:
            vals['access_token'] = access
        if refresh:
            vals['refresh_token'] = refresh
        if expires_in:
            # expires_in may be seconds or an absolute ms timestamp; treat >10^10 as ms epoch.
            if expires_in > 10 ** 10:
                vals['token_expiry'] = datetime.fromtimestamp(expires_in / 1000.0)
            else:
                vals['token_expiry'] = datetime.now() + timedelta(seconds=expires_in)
        if vals:
            self.provider.sudo().write(vals)
        return True

    # ------------------------------------------------------------------ #
    # 2-6. business methods
    # ------------------------------------------------------------------ #
    def get_feed_names(self):
        """List the promo feeds available to this DS account."""
        data = self._call('aliexpress.ds.feedname.get', {})
        promos = self._dig(data, 'promo') or []
        if isinstance(promos, dict):
            promos = [promos]
        return [{'name': p.get('promo_name'), 'count': p.get('product_num')} for p in promos]

    def _first_feed_name(self):
        names = self.get_feed_names()
        return names[0]['name'] if names else None

    def get_categories(self):
        """Return the FULL AliExpress category taxonomy as a flat list of
        {id, name, parent_id} dicts (parent_id=0/None for top level).

        Uses ``aliexpress.ds.category.get`` which returns every category in one
        call. Safe to call repeatedly — the importer upserts by id."""
        data = self._call('aliexpress.ds.category.get', {})
        cats = (self._dig(data, 'categories')
                or self._dig(data, 'resp_result')
                or self._dig(data, 'aeop_ae_category_dtos')
                or [])
        # unwrap the common {'category': [...]} / single-dict shapes
        if isinstance(cats, dict):
            cats = (cats.get('category') or cats.get('aeop_ae_category_d_t_o')
                    or cats.get('aeop_ae_category_dtos') or [cats])
        out = []
        for c in (cats or []):
            if not isinstance(c, dict):
                continue
            cid = c.get('category_id') or c.get('id')
            if cid is None:
                continue
            out.append({
                'id': str(cid),
                'name': (c.get('category_en_name') or c.get('category_name')
                         or c.get('name') or str(cid)),
                'parent_id': str(c.get('parent_category_id')
                                  or c.get('parent_id') or '0'),
            })
        return out

    def search_feed(self, query=None, category=None, page=1, page_size=20, feed_name=None):
        """Pull one page of a promo feed.

        AliExpress requires a mandatory ``feed_name`` (one of the promo feeds
        from :meth:`get_feed_names`). ``query`` is not supported by this endpoint;
        it is accepted for interface compatibility and ignored.
        """
        feed_name = feed_name or self.provider.feed_name or self._first_feed_name()
        if not feed_name:
            return []
        params = {
            'feed_name': feed_name,
            'page_no': page,
            'page_size': page_size,
            'target_currency': self.provider.currency or 'USD',
            'target_language': 'EN',
            'country': self.provider.default_country or 'KW',
        }
        if category:
            params['category_id'] = category
        data = self._call('aliexpress.ds.recommend.feed.get', params)
        products = self._dig(data, 'products') or {}
        if isinstance(products, dict):
            products = products.get('traffic_product_d_t_o') or []
        return [self.normalize(it) for it in (products or [])]

    def get_product(self, source_id):
        data = self._call('aliexpress.ds.product.get', {
            'product_id': source_id,
            'ship_to_country': self.provider.default_country or 'KW',
            'target_currency': self.provider.currency or 'USD',
            'target_language': 'en',
        })
        prod = self._dig(data, 'result') or data
        return self.normalize(prod)

    def get_freight(self, source_id, country_code, quantity=1, sku_id=None):
        """Query live shipping options to a country.

        AliExpress needs a ``selectedSkuId`` inside ``queryDeliveryReq`` plus a
        top-level ``locale``. If no sku is supplied we resolve the first one via
        product.get.
        """
        if not sku_id:
            sku_id = self._first_sku_id(source_id)
        req = {
            'productId': source_id,
            'selectedSkuId': str(sku_id or ''),
            'quantity': quantity,
            'shipToCountry': country_code,
            'language': 'en_US',
            'locale': 'en_US',
            'currency': self.provider.currency or 'USD',
        }
        data = self._call('aliexpress.ds.freight.query',
                          {'queryDeliveryReq': json.dumps(req), 'locale': 'en_US'})
        opts = self._dig(data, 'delivery_option_d_t_o') or []
        if isinstance(opts, dict):
            opts = [opts]
        out = []
        for o in opts:
            out.append({
                'service': o.get('company') or o.get('code'),
                'cost': float(o.get('shipping_fee_cent') or 0),
                'currency': o.get('shipping_fee_currency') or self.provider.currency or 'USD',
                'days_min': int(o.get('min_delivery_days') or 0),
                'days_max': int(o.get('max_delivery_days') or 0),
                'tracking': bool(o.get('tracking')),
                'free': bool(o.get('free_shipping')),
                'eta_text': o.get('delivery_date_desc'),
            })
        return out

    def _first_sku_id(self, source_id):
        """Return the first SKU id of a product (needed for freight/order)."""
        detail = self._call('aliexpress.ds.product.get', {
            'product_id': source_id,
            'ship_to_country': self.provider.default_country or 'KW',
            'target_currency': self.provider.currency or 'USD',
            'target_language': 'en',
        })
        skus = self._dig(detail, 'ae_item_sku_info_d_t_o') or []
        if isinstance(skus, dict):
            skus = [skus]
        return (skus[0].get('sku_id') or skus[0].get('id')) if skus else None

    def place_order(self, order_payload):
        """Place a DS order. Expects a normalized payload:

            {'address': {country, province, city, address, contact_person,
                          mobile_no, phone_country, zip, full_name},
             'items':   [{product_id, product_count, sku_attr,
                          logistics_service_name, order_memo}]}
        """
        dto = {
            'logistics_address': order_payload['address'],
            'product_items': order_payload['items'],
        }
        data = self._call('aliexpress.ds.order.create',
                          {'param_place_order_request4_open_api_d_t_o': json.dumps(dto)})
        res = self._dig(data, 'result') or {}
        order_ids = res.get('order_list') or res.get('order_id')
        if isinstance(order_ids, dict):
            order_ids = order_ids.get('number') or order_ids.get('string')
        if isinstance(order_ids, (list, tuple)):
            order_ids = ','.join(str(x) for x in order_ids)
        return {
            'provider_order_id': str(order_ids or ''),
            'status': 'placed' if res.get('is_success') else ('error:%s' % (res.get('error_code') or 'unknown')),
            'raw': data,
        }

    # public feedback endpoint (NOT part of the DS gateway — the DS toolkit has
    # no review-list method; this is the same public endpoint the AliExpress
    # product page calls over AJAX, so it needs no app_key/session).
    FEEDBACK_URL = 'https://feedback.aliexpress.com/pc/searchEvaluation.do'

    def get_reviews(self, source_id, page=1, page_size=20, country='US', lang='en_US'):
        """Fetch individual customer reviews + a rating breakdown.

        Returns {'reviews': [{name, country, stars(1-5), date, text, sku,
        has_image}], 'stats': {avg, total, five, four, three, negative,
        positive_rate}}. Fully fail-soft: any error -> empty lists.
        """
        params = {
            'productId': source_id, 'lang': lang, 'country': country,
            'page': page, 'pageSize': page_size,
            'filter': 'all', 'sort': 'complex_default',
        }
        try:
            resp = requests.get(self.FEEDBACK_URL, params=params, timeout=15, headers={
                'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/120.0 Safari/537.36'),
                'Referer': 'https://www.aliexpress.com/'})
            data = (resp.json() or {}).get('data') or {}
        except Exception as e:  # noqa: BLE001 - reviews are best-effort
            _logger.info("AliExpress reviews fetch failed for %s: %s", source_id, e)
            return {'reviews': [], 'stats': {}}

        reviews = []
        for r in (data.get('evaViewList') or []):
            text = (r.get('buyerFeedback') or r.get('buyerTranslationFeedback') or '').strip()
            if not text:
                continue
            try:
                stars = int(round(float(r.get('buyerEval') or 0) / 20.0))
            except (TypeError, ValueError):
                stars = 0
            # buyer "show" photos — the feedback endpoint returns them under
            # `images` (list of full URLs); keep up to 4 per review.
            raw_imgs = r.get('images') or r.get('buyerAddFbPics') or r.get('logImgList') or []
            imgs = []
            if isinstance(raw_imgs, (list, tuple)):
                for u in raw_imgs:
                    if isinstance(u, str) and u.startswith('http'):
                        imgs.append(u)
                    elif isinstance(u, dict):
                        u2 = u.get('imgUrl') or u.get('url') or u.get('image')
                        if isinstance(u2, str) and u2.startswith('http'):
                            imgs.append(u2)
            imgs = imgs[:4]
            reviews.append({
                'name': (r.get('buyerName') or 'AliExpress Shopper').strip(),
                'country': (r.get('buyerCountry') or '').strip(),
                'stars': max(1, min(5, stars)),
                'date': (r.get('evalDate') or '').strip(),
                'text': text[:600],
                'sku': (r.get('skuInfo') or '').strip(),
                'images': imgs,
                'has_image': bool(imgs),
            })
        stat = data.get('productEvaluationStatistic') or {}
        return {
            'reviews': reviews,
            'stats': {
                'avg': stat.get('evarageStar'),
                'total': data.get('totalNum'),
                'five': stat.get('fiveStarNum'),
                'four': stat.get('fourStarNum'),
                'three': stat.get('neutralNum'),
                'negative': stat.get('negativeNum'),
                'positive_rate': stat.get('evarageStarRage'),
            },
        }

    def get_tracking(self, provider_order_id):
        data = self._call('aliexpress.ds.order.tracking.get', {
            'ae_order_id': provider_order_id,
            'language': 'en',
        })
        res = self._dig(data, 'result') or {}
        details = res.get('details') or {}
        events = details.get('tracking_detail_line_list') or []
        return {
            'carrier': res.get('logistics_no') and res.get('carrier_name'),
            'tracking_no': res.get('mail_no') or res.get('logistics_no'),
            'status': res.get('official_website_status') or res.get('status'),
            'events': [{'time': e.get('event_date'), 'desc': e.get('event_desc')} for e in events],
        }

    # ------------------------------------------------------------------ #
    # normalizer: AliExpress payload -> unified schema
    # ------------------------------------------------------------------ #
    def normalize(self, raw):
        """Convert an AliExpress payload to the unified schema.

        Handles BOTH shapes with one path:
          * feed  (aliexpress.ds.recommend.feed.get) — flat keys
            (product_title, product_main_image_url, evaluate_rate, ...)
          * detail (aliexpress.ds.product.get)       — nested DTOs
            (ae_item_base_info_dto, ae_item_properties, ae_store_info, ...)
        The nested DTOs are flattened up-front so the rest reads uniformly.
        """
        if not isinstance(raw, dict):
            return super().normalize({})

        # ---- flatten the detail DTOs (absent on feed payloads) ----------- #
        base = raw.get('ae_item_base_info_dto') or {}
        mm = raw.get('ae_multimedia_info_dto') or {}
        store = raw.get('ae_store_info') or {}
        logi = raw.get('logistics_info_dto') or {}

        # images: feed = product_main_image_url + product_small_image_urls;
        # detail = ae_multimedia_info_dto.image_urls (semicolon-joined string)
        imgs = raw.get('product_main_image_url') or raw.get('image_url')
        gallery = raw.get('product_small_image_urls') or raw.get('image_urls') or {}
        if isinstance(gallery, dict):
            gallery = gallery.get('productSmallImageUrl') or gallery.get('string') or []
        detail_imgs = mm.get('image_urls')
        if detail_imgs and isinstance(detail_imgs, str):
            parts = [u for u in detail_imgs.split(';') if u.strip()]
            if parts:
                imgs = imgs or parts[0]
                gallery = parts
        price = (raw.get('target_sale_price') or raw.get('sale_price')
                 or raw.get('app_sale_price') or raw.get('original_price') or 0)
        original = (raw.get('target_original_price') or raw.get('original_price')
                    or raw.get('product_original_price') or 0)
        video = raw.get('product_video_url') or raw.get('video_url')
        vdtos = mm.get('ae_video_dtos')
        if not video and isinstance(vdtos, dict):
            v = vdtos.get('ae_video_d_t_o') or vdtos
            if isinstance(v, list):
                v = v[0] if v else {}
            video = v.get('media_url') if isinstance(v, dict) else None

        variants = []
        skus = (raw.get('ae_item_sku_info_dtos', {}) or {}).get('ae_item_sku_info_d_t_o', []) or []
        if isinstance(skus, dict):
            skus = [skus]
        for sku in skus:
            # readable option list (Color: Beige, Size: XL, ...) + per-option image
            props = (sku.get('ae_sku_property_dtos') or {}).get('ae_sku_property_d_t_o') or []
            if isinstance(props, dict):
                props = [props]
            options = []
            for pr in props:
                name = (pr.get('sku_property_name') or '').strip()
                value = (pr.get('sku_property_value')
                         or pr.get('property_value_definition_name') or '').strip()
                if not name or not value:
                    continue
                options.append({
                    'name': name,
                    'value': value,
                    'image': pr.get('sku_image') or None,
                })
            variants.append({
                'sku_id': sku.get('sku_id') or sku.get('id'),
                'sku': sku.get('sku_code') or sku.get('sku_id') or sku.get('id'),
                'attrs': sku.get('sku_attr'),
                'options': options,
                'price': float(sku.get('offer_sale_price') or sku.get('sku_price') or 0),
                'stock': int(sku.get('sku_available_stock') or 0),
            })

        # ---- specifications table (detail only) -------------------------- #
        props = (raw.get('ae_item_properties') or {}).get('ae_item_property') or []
        if isinstance(props, dict):
            props = [props]
        specs, seen = [], set()
        for p in props:
            if not isinstance(p, dict):
                continue
            name = (p.get('attr_name') or '').strip()
            value = (p.get('attr_value') or '').strip()
            if not name or not value or value.upper() == 'NONE':
                continue
            key = (name.lower(), value.lower())
            if key in seen:
                continue
            seen.add(key)
            specs.append({'name': name, 'value': value})

        # ---- review / seller-rating summary (detail only) ---------------- #
        store_info = None
        if store:
            store_info = {
                'name': store.get('store_name'),
                'country': store.get('store_country_code'),
                'shipping_rating': store.get('shipping_speed_rating'),
                'item_rating': store.get('item_as_described_rating'),
                'comm_rating': store.get('communication_rating'),
            }

        return {
            'source_id': str(raw.get('product_id') or raw.get('productId')
                             or base.get('product_id') or raw.get('id') or ''),
            'title_en': (base.get('subject') or raw.get('subject')
                         or raw.get('product_title') or raw.get('title') or ''),
            # rating: detail gives a 0-5 average; feed gives an "xx.x%" positive rate
            'rating': base.get('avg_evaluation_rating') or raw.get('evaluate_rate'),
            'review_count': base.get('evaluation_count'),
            'orders': base.get('sales_count') or raw.get('lastest_volume'),
            'orders_text': base.get('sales_count') or raw.get('lastest_volume'),
            'title_ar': None,
            'description_html': base.get('detail') or raw.get('detail') or raw.get('description'),
            'specs': specs,
            'store': store_info,
            'price': float(price or 0),
            'original_price': float(original or 0),
            'currency': (base.get('currency_code') or raw.get('target_sale_price_currency')
                         or raw.get('currency') or self.provider.currency or 'USD'),
            'image_url': imgs,
            'image_urls': list(gallery) if isinstance(gallery, (list, tuple)) else [],
            'video_url': video or None,
            'category': str(raw.get('category_id') or base.get('category_id')
                            or raw.get('second_level_category_id')
                            or raw.get('first_level_category_id') or '') or None,
            # readable category (name) so the storefront never shows a raw code
            'category_name': (raw.get('second_level_category_name')
                              or raw.get('first_level_category_name')
                              or raw.get('category_name') or None),
            'category_parent': raw.get('first_level_category_name') or None,
            'variants': variants,
            'shipping_days': logi.get('delivery_time') or None,
            'raw': raw,
        }

    @staticmethod
    def _dig(data, key):
        """Walk AliExpress' nested *_response wrappers to find ``key``."""
        if not isinstance(data, dict):
            return None
        if key in data:
            return data[key]
        for v in data.values():
            if isinstance(v, dict):
                found = AliExpressAdapter._dig(v, key)
                if found is not None:
                    return found
        return None
