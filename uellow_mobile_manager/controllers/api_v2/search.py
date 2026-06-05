"""Search — /api/mobile/v2/search

Hits the Flutter search bar. Uses the same fuzzy logic that Beena's
search uses (with EN/AR translation table) so results match the AI
chat's behaviour.
"""
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, get_lang, paginate, current_session,
    img_url, bilingual,
)
from .products import serialize_product_card, _domain_published_for_app


def _log_search(q, results_count):
    """Best-effort analytic row (recent + trending feeds)."""
    try:
        sess = current_session()
        request.env['mobile.search.analytic'].sudo().create({
            'keyword': q,
            'results_count': results_count,
            'session_id': sess.id if sess else False,
            'platform': (sess.platform if sess else 'android'),
        })
    except Exception:
        pass


def _search_brands(q, limit=6):
    """Brand attribute values matching q → [{id, name, image,
    product_count}]. id is the attribute VALUE id (what the collection
    screen filters by)."""
    out = []
    try:
        Val = request.env['product.attribute.value'].sudo()
        vals = Val.search([
            ('name', 'ilike', q),
            '|', '|',
            ('attribute_id.name', 'ilike', 'brand'),
            ('attribute_id.name', 'ilike', 'ماركة'),
            ('attribute_id.name', 'ilike', 'علامة'),
        ], limit=limit)
        Brand = None
        if 'product.brand' in request.env:
            Brand = request.env['product.brand'].sudo()
        Tmpl = request.env['product.template'].sudo()
        base = _domain_published_for_app(include_oos=True)
        for v in vals:
            logo = None
            if Brand is not None:
                b = Brand.search([('name', '=ilike', v.name)], limit=1) \
                    or Brand.search([('name', 'ilike', v.name)], limit=1)
                if b and getattr(b, 'image_1024', False):
                    logo = img_url('product.brand', b.id, 'image_1024',
                                   unique=b.write_date)
            n = Tmpl.search_count(
                base + [('attribute_line_ids.value_ids', 'in', [v.id])])
            if n:
                out.append({'id': v.id, 'name': v.name,
                            'image': logo, 'product_count': n})
    except Exception:
        pass
    return out


def _search_vendors(q, limit=6):
    """Marketplace sellers matching q → [{id, name{en,ar}, logo,
    product_count}]."""
    out = []
    try:
        if 'uellow.vendor' not in request.env:
            return out
        Vendor = request.env['uellow.vendor'].sudo()
        vs = Vendor.search([
            '|', '|',
            ('store_name_en', 'ilike', q),
            ('store_name_ar', 'ilike', q),
            ('name', 'ilike', q),
        ], limit=limit)
        Tmpl = request.env['product.template'].sudo()
        for v in vs:
            n = 0
            try:
                n = Tmpl.search_count([
                    ('vendor_id', '=', v.id), ('is_published', '=', True)])
            except Exception:
                pass
            out.append({
                'id': v.id,
                'name': {
                    'en': v.store_name_en or v.display_name or '',
                    'ar': v.store_name_ar or v.store_name_en
                          or v.display_name or '',
                },
                'logo': img_url('uellow.vendor', v.id, 'logo_image',
                                unique=v.write_date)
                        if 'logo_image' in v._fields else None,
                'product_count': n,
            })
    except Exception:
        pass
    return out


class MobileSearchAPI(http.Controller):

    @http.route('/api/mobile/v2/search', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def search(self, **kw):
        p = get_payload()
        lang = get_lang()
        q = (p.get('q') or p.get('search') or '').strip()
        if not q or len(q) < 2:
            return ok({
                'products': [], 'categories': [], 'brands': [],
                'vendors': [], 'suggestions': [],
            })

        Tmpl = request.env['product.template'].sudo()
        # Search surfaces out-of-stock items so the user can still find
        # a specific product they're looking for, even when it's not
        # listed elsewhere in the app.
        domain = _domain_published_for_app(include_oos=True) + [
            '|', '|',
            ('name', 'ilike', q),
            ('default_code', 'ilike', q),
            ('description_sale', 'ilike', q),
        ]
        records = Tmpl.search(domain, order='create_date desc', limit=100)

        # v2.1.56 — the app passes log=0 for as-you-type suggestion calls
        # so half-typed words no longer pollute recent/trending. Only the
        # FINAL submitted search is recorded (default stays on for
        # backward compatibility).
        log = str(p.get('log', '1')).strip().lower() not in (
            '0', 'false', 'no')
        if log:
            _log_search(q, len(records))

        items, meta = paginate(
            records, page=p.get('page', 1), per_page=p.get('per_page', 20),
            serializer=lambda r: serialize_product_card(r, lang),
        )

        # Matched categories (with image) + brands + sellers + suggestions
        categories = request.env['product.public.category'].sudo().search(
            [('name', 'ilike', q)], limit=8)
        brands = _search_brands(q)
        vendors = _search_vendors(q)
        suggestions = [r.name for r in records[:8]] + [c.name for c in categories]

        return ok({
            'products': items,
            'categories': [{
                'id': c.id,
                'name': bilingual(c, 'name'),
                'image': img_url('product.public.category', c.id,
                                 'image_1920', unique=c.write_date)
                         if c.image_1920 else None,
                'product_count': len(c.product_tmpl_ids),
            } for c in categories],
            'brands': brands,
            'vendors': vendors,
            'suggestions': suggestions[:10],
        }, meta)

    @http.route('/api/mobile/v2/search/record', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def record_search(self, **kw):
        """v2.1.56 — explicit search-term recording. Called by the app
        when the user FINISHES a search (submit / taps a result), instead
        of logging every typing pause."""
        p = get_payload()
        q = (p.get('q') or '').strip()
        if len(q) >= 2:
            _log_search(q, int(p.get('results_count') or 0))
        return ok({'recorded': len(q) >= 2})

    @http.route('/api/mobile/v2/search/popular', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def popular_queries(self, **kw):
        # Odoo 18: read_group no longer exposes __count by default. Use
        # raw SQL — also faster for a top-N aggregation.
        request.env.cr.execute("""
            SELECT keyword, COUNT(*) AS cnt
            FROM mobile_search_analytic
            WHERE keyword IS NOT NULL AND keyword NOT LIKE '[barcode]%%'
            GROUP BY keyword
            ORDER BY cnt DESC
            LIMIT 12
        """)
        rows = request.env.cr.fetchall()
        return ok([{'query': r[0], 'count': int(r[1])} for r in rows])

    @http.route('/api/mobile/v2/search/trending', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def trending_today(self, **kw):
        """Top searched keywords in the last 24h. Falls back to last
        7d / 30d if today is empty."""
        for days in (1, 7, 30):
            since = datetime.utcnow() - timedelta(days=days)
            request.env.cr.execute("""
                SELECT keyword, COUNT(*) AS cnt
                FROM mobile_search_analytic
                WHERE create_date >= %s
                  AND keyword IS NOT NULL
                  AND keyword NOT LIKE '[barcode]%%'
                GROUP BY keyword
                ORDER BY cnt DESC
                LIMIT 10
            """, (since,))
            rows = request.env.cr.fetchall()
            cleaned = [{'query': r[0], 'count': int(r[1])} for r in rows]
            if cleaned:
                return ok({'trending': cleaned, 'window_days': days})
        return ok({'trending': [], 'window_days': 0})

    @http.route('/api/mobile/v2/search/recent', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def recent_queries(self, **kw):
        """Recent searches for the current user/session."""
        sess = current_session()
        Analytic = request.env['mobile.search.analytic'].sudo()
        domain = []
        if sess:
            domain.append(('session_id', '=', sess.id))
        else:
            return ok({'recent': []})
        rows = Analytic.search(domain, order='create_date desc', limit=30)
        seen = set(); recent = []
        for r in rows:
            kw = (r.keyword or '').strip()
            if not kw or kw.startswith('[barcode]') or kw.lower() in seen:
                continue
            seen.add(kw.lower())
            recent.append({
                'query': kw,
                'when': r.create_date.isoformat() if r.create_date else None,
                'results_count': r.results_count,
            })
            if len(recent) >= 10:
                break
        return ok({'recent': recent})

    @http.route('/api/mobile/v2/search/recent/clear', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def recent_clear(self, **kw):
        sess = current_session()
        if not sess:
            return ok({'cleared': 0})
        rows = request.env['mobile.search.analytic'].sudo().search([
            ('session_id', '=', sess.id),
        ])
        n = len(rows)
        rows.unlink()
        return ok({'cleared': n})

    # ─── Barcode search ─────────────────────────────────────────────
    @http.route('/api/mobile/v2/search/barcode', type='http', auth='public',
                methods=['POST', 'GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def search_barcode(self, **kw):
        """Lookup by EAN/UPC barcode. Matches on either the template
        barcode OR a variant barcode, and resolves to the template."""
        from ._common import get_payload, fail
        from .products import serialize_product_card, serialize_product_full
        p = get_payload()
        code = (p.get('barcode') or p.get('code') or '').strip()
        if not code:
            return fail('BAD_REQUEST', 'barcode required')
        lang = get_lang()

        # 1) Template barcode
        Tmpl = request.env['product.template'].sudo()
        tmpl = Tmpl.search([
            ('barcode', '=', code), ('is_published', '=', True),
        ], limit=1)
        # 2) Variant barcode → template
        if not tmpl:
            v = request.env['product.product'].sudo().search([
                ('barcode', '=', code),
            ], limit=1)
            if v and v.product_tmpl_id.is_published:
                tmpl = v.product_tmpl_id

        if not tmpl:
            # Record the miss so admins can see "demanded but not in catalog"
            try:
                request.env['mobile.search.analytic'].sudo().create({
                    'query': f'[barcode] {code}',
                    'result_count': 0,
                })
            except Exception:
                pass
            return fail('NOT_FOUND',
                        'No product matches that barcode in our catalog.', 404)
        return ok({
            'matched': True,
            'product': serialize_product_full(tmpl, lang),
        })

    # ─── Image search ───────────────────────────────────────────────
    @http.route('/api/mobile/v2/search/image', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def search_image(self, **kw):
        """Image search. We delegate to Beena AI (Claude vision) when a
        photo is uploaded; Beena returns a search query that we then
        run as a text search. Returns top matching products.

        Body (multipart OR JSON):
          image_base64 = '<base64 jpeg/png>'
          OR  image_url = 'https://...'
          OR  query_hint = 'red sneakers'   (fallback if no image)
        """
        from ._common import get_payload, fail
        from .products import serialize_product_card, _domain_published_for_app
        p = get_payload()
        image_b64 = (p.get('image_base64') or '').strip()
        image_url = (p.get('image_url') or '').strip()
        hint      = (p.get('query_hint') or '').strip()

        if not (image_b64 or image_url or hint):
            return fail('BAD_REQUEST', 'Provide image_base64 / image_url / query_hint')

        # Ask Beena (Claude vision) to describe the image — try/except so
        # broken AI never breaks the search.
        # v2.1.56 — quality rebuild: Claude now returns structured
        # keywords (brand / type / color, EN + AR), and matching runs a
        # per-keyword OR search with word-hit scoring instead of one
        # 5-word phrase ILIKE (which almost never matched anything).
        import json as _json
        beena_query = hint
        keywords = []
        try:
            from odoo.addons.uellow_ai_engine.controllers.ai_controller import UellowAIController
            ctrl = UellowAIController()
            ai = ctrl._call_claude(
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text',
                         'text': ('Identify the product in this photo for a '
                                  'shopping search. Reply with ONLY JSON: '
                                  '{"query": "<2-4 word search>", '
                                  '"keywords": ["brand if visible", '
                                  '"product type", "product type in Arabic", '
                                  '"color"]} — no prose.')},
                        ({'type': 'image',
                          'source': {'type': 'base64', 'media_type': 'image/jpeg',
                                     'data': image_b64}} if image_b64
                         else {'type': 'image',
                               'source': {'type': 'url', 'url': image_url}}),
                    ],
                }],
                system_prompt='You translate product photos into short search queries. Reply with JSON only.',
                model='claude-haiku-4-5',
                max_tokens=120,
            )
            text = (ai or '').strip()
            if '{' in text:
                text = text[text.find('{'):text.rfind('}') + 1]
                parsed = _json.loads(text)
                beena_query = (parsed.get('query') or '').strip() or beena_query
                keywords = [str(k).strip() for k in
                            (parsed.get('keywords') or []) if str(k).strip()]
            elif text:
                beena_query = text.strip('"').strip("'")
        except Exception:
            # Beena not wired or vision call failed — fall back to hint
            pass

        if not (beena_query or keywords):
            return ok({'query': '', 'products': []})

        lang = get_lang()
        Tmpl = request.env['product.template'].sudo()
        base = _domain_published_for_app()

        # Pass 1 — exact phrase.
        recs = Tmpl.search(
            base + ['|',
                ('name', 'ilike', beena_query),
                ('description_sale', 'ilike', beena_query),
            ],
            order='create_date desc', limit=24,
        ) if beena_query else Tmpl.browse()

        # Pass 2 — keyword OR search with hit scoring when the phrase
        # found too little. Every distinct word from query + keywords
        # becomes an OR leaf; results rank by how many words they match.
        if len(recs) < 3:
            words = set()
            for chunk in [beena_query] + keywords:
                for w in chunk.replace('-', ' ').split():
                    if len(w) >= 3:
                        words.add(w)
            words = list(words)[:10]
            if words:
                dom = base + ['|'] * (len(words) - 1)
                for w in words:
                    dom.append(('name', 'ilike', w))
                cands = Tmpl.search(dom, limit=120)

                def score(r):
                    name = (r.name or '').lower()
                    return sum(1 for w in words if w.lower() in name)
                ranked = sorted(cands, key=score, reverse=True)
                extra = [r for r in ranked if r not in recs][:24 - len(recs)]
                recs = recs | Tmpl.browse([r.id for r in extra]) \
                    if extra else recs

        return ok({
            'query': beena_query or ' '.join(keywords[:3]),
            'products': [serialize_product_card(r, lang) for r in recs[:24]],
        })
