"""Search — /api/mobile/v2/search

Hits the Flutter search bar. Uses the same fuzzy logic that Beena's
search uses (with EN/AR translation table) so results match the AI
chat's behaviour.
"""
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from ._common import safe_endpoint, get_payload, ok, get_lang, paginate, current_session
from .products import serialize_product_card, _domain_published_for_app


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
                'suggestions': [],
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

        # Quick log to the same analytic store Beena uses (best-effort)
        try:
            sess = current_session()
            request.env['mobile.search.analytic'].sudo().create({
                'keyword': q,
                'results_count': len(records),
                'session_id': sess.id if sess else False,
                'platform': (sess.platform if sess else 'android'),
            })
        except Exception:
            pass

        items, meta = paginate(
            records, page=p.get('page', 1), per_page=p.get('per_page', 20),
            serializer=lambda r: serialize_product_card(r, lang),
        )

        # Matched categories + suggestions
        categories = request.env['product.public.category'].sudo().search(
            [('name', 'ilike', q)], limit=8)
        suggestions = [r.name for r in records[:8]] + [c.name for c in categories]

        return ok({
            'products': items,
            'categories': [{
                'id': c.id, 'name': c.name,
            } for c in categories],
            'brands': [],
            'suggestions': suggestions[:10],
        }, meta)

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
        beena_query = hint
        try:
            from odoo.addons.uellow_ai_engine.controllers.ai_controller import UellowAIController
            ctrl = UellowAIController()
            ai = ctrl._call_claude(
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text',
                         'text': 'Describe this product in ≤5 words for a shopping search. Reply with the search query only.'},
                        ({'type': 'image',
                          'source': {'type': 'base64', 'media_type': 'image/jpeg',
                                     'data': image_b64}} if image_b64
                         else {'type': 'image',
                               'source': {'type': 'url', 'url': image_url}}),
                    ],
                }],
                system_prompt='You translate product photos into short search queries.',
                model='claude-haiku-4-5',
                max_tokens=40,
            )
            text = (ai or '').strip().strip('"').strip("'")
            if text:
                beena_query = text
        except Exception:
            # Beena not wired or vision call failed — fall back to hint
            pass

        if not beena_query:
            return ok({'query': '', 'products': []})

        lang = get_lang()
        Tmpl = request.env['product.template'].sudo()
        recs = Tmpl.search(
            _domain_published_for_app() + ['|',
                ('name', 'ilike', beena_query),
                ('description_sale', 'ilike', beena_query),
            ],
            order='create_date desc', limit=24,
        )
        return ok({
            'query': beena_query,
            'products': [serialize_product_card(r, lang) for r in recs],
        })
