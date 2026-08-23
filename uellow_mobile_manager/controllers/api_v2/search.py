"""Search — /api/mobile/v2/search

Hits the Flutter search bar. Uses the same fuzzy logic that Beena's
search uses (with EN/AR translation table) so results match the AI
chat's behaviour.
"""
import re
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, get_lang, paginate, current_session,
    img_url, bilingual,
)
from .products import (
    serialize_product_card, _domain_published_for_app,
    _norm_light, _norm_full, _syn_expand,
    _rank_by_relevance, _fuzzy_search,
)


def _norm_lang(lang):
    """Normalize any locale code to 'ar' or 'en' for language-scoped feeds."""
    return 'ar' if str(lang or '').lower().startswith('ar') else 'en'


# Arabic letter range U+0621–U+064A — a keyword containing any of these reads
# as an Arabic-script search; otherwise it's treated as Latin/English.
_AR_CHAR_RE = re.compile('[ء-ي]')


def _lang_script_clause():
    """SQL fragment (server-controlled, injection-safe) scoping keyword feeds
    to the current UI language by SCRIPT: Arabic-script terms only on the
    Arabic UI, non-Arabic terms only on the English UI."""
    if _norm_lang(get_lang()) == 'ar':
        return "AND keyword ~ '[ء-ي]'"
    return "AND keyword !~ '[ء-ي]'"


def _website_clause():
    """SQL fragment scoping keyword feeds to the CURRENT website, so each
    site (Kuwait, World/China, …) has its own trending/popular terms. The id
    is int-cast, so this is injection-safe. Rows with a NULL website match
    every site (legacy rows logged before per-site tagging existed)."""
    try:
        wid = int(get_website().id)
    except Exception:
        return ""
    return " AND (website_id = %d OR website_id IS NULL) " % wid


def _matches_ui_lang(keyword):
    """Python mirror of _lang_script_clause for in-memory (recent) filtering."""
    has_ar = bool(_AR_CHAR_RE.search(keyword or ''))
    return has_ar if _norm_lang(get_lang()) == 'ar' else not has_ar


def _log_search(q, results_count):
    """Best-effort analytic row (recent + trending feeds)."""
    try:
        sess = current_session()
        # v2.2.65 — tag the ORIGIN website so trending/popular are per-site
        # (World's trending must never mix in Kuwait search terms).
        try:
            wid = get_website().id
        except Exception:
            wid = False
        request.env['mobile.search.analytic'].sudo().create({
            'keyword': q,
            'results_count': results_count,
            'session_id': sess.id if sess else False,
            'platform': (sess.platform if sess else 'android'),
            'lang': _norm_lang(get_lang()),
            'website_id': wid,
        })
    except Exception:
        pass


# v2.2.16 — trending/popular hygiene -------------------------------------
_LETTER_RE = re.compile(r'[A-Za-z؀-ۿ]')


def _is_clear_keyword(k):
    """Only clear human words make the public trends. Rejects barcodes,
    product IDs, pure numbers and letterless garbage."""
    k = (k or '').strip()
    if len(k) < 3 or k.lower().startswith('[barcode]'):
        return False
    letters = len(_LETTER_RE.findall(k))
    if letters < 3:                       # "12", "a1", "....."
        return False
    if re.search(r'\d{5,}', k):           # embedded barcode / phone / ID
        return False
    if sum(c.isdigit() for c in k) > letters:   # mostly numeric
        return False
    return True


def _fold_incomplete(rows, limit):
    """rows = [(keyword, count)] sorted by count desc. Merges half-typed
    prefixes ("iphon", "سماع") into their most popular completed keyword
    ("iphone 15", "سماعة") so abandoned keystrokes never trend on their
    own, then returns the top `limit` clear keywords."""
    rows = [(k.strip(), int(c)) for k, c in rows if _is_clear_keyword(k)]
    # Each keyword's host = its most popular strictly-longer completion.
    hosts = []
    for i, (k, c) in enumerate(rows):
        kl = k.lower()
        best = None
        for j, (k2, c2) in enumerate(rows):
            if i != j and len(k2) > len(k) and k2.lower().startswith(kl):
                if best is None or c2 > rows[best][1]:
                    best = j
        hosts.append(best)
    folded = {}
    for i, (k, c) in enumerate(rows):
        # Follow the chain transitively (shi → shir → shirt) so every
        # half-typed prefix lands in the FINAL completed keyword. Chains
        # always terminate: each hop is strictly longer.
        j = i
        while hosts[j] is not None:
            j = hosts[j]
        key = rows[j][0].lower()
        if key not in folded:
            folded[key] = [rows[j][0], 0]
        folded[key][1] += c
    out = sorted(folded.values(), key=lambda t: -t[1])
    return [{'query': k, 'count': c} for k, c in out[:limit]]


def _norm_hit(name, ntoks, nq):
    """Relevance of a name to the query, normalized (ة/ه, hamza, tashkeel) and
    tokenized: exact-phrase (3) > all-tokens (2) > any-token (1) > none (0)."""
    n = _norm_full(name or '')
    if not n:
        return 0
    if nq and nq in n:
        return 3
    if ntoks and all(t in n for t in ntoks):
        return 2
    if ntoks and any(t in n for t in ntoks):
        return 1
    return 0


def _search_categories(ntoks, nq, ctx_lang, limit=8):
    """Categories matching the query — normalized + tokenized (so «سماعه»
    matches «سماعة …») and ranked. The catalogue has only a few hundred
    categories, so a scan + Python score is cheap and index-free."""
    Cat = request.env['product.public.category'].sudo() \
        .with_context(lang=ctx_lang)
    recs = Cat.search([], limit=2000)
    scored = []
    for c in recs:
        h = _norm_hit(c.name, ntoks, nq)
        if h:
            scored.append((h, c.id))
    if scored:
        scored.sort(key=lambda x: (-x[0], -x[1]))
        return Cat.browse([cid for _h, cid in scored[:limit]])
    # Fuzzy fallback (pg_trgm word-similarity) for Arabic singular/broken-plural
    # & typos a plain substring misses (سماعه↔سماعات).
    try:
        cr = request.env.cr
        cr.execute("SET LOCAL pg_trgm.word_similarity_threshold = 0.4")
        cr.execute(
            "SELECT id FROM product_public_category "
            "WHERE %s <%% coalesce(name->>%s, name->>'en_US', '') "
            "ORDER BY word_similarity("
            "  %s, coalesce(name->>%s, name->>'en_US', '')) DESC LIMIT %s",
            (nq, ctx_lang, nq, ctx_lang, limit))
        ids = [r[0] for r in cr.fetchall()]
        if ids:
            return Cat.browse(ids)
    except Exception:
        try:
            request.env.cr.rollback()
        except Exception:
            pass
    return Cat.browse()


def _search_brands(q, ntoks=None, limit=6):
    """Brand attribute values matching q → [{id, name, image,
    product_count}]. id is the attribute VALUE id (what the collection
    screen filters by)."""
    out = []
    try:
        Val = request.env['product.attribute.value'].sudo()
        _nl = [('name', 'ilike', t) for t in (ntoks or [q])]
        _name_dom = (['|'] * (len(_nl) - 1) + _nl) if len(_nl) > 1 else _nl
        vals = Val.search(_name_dom + [
            '|', '|',
            ('attribute_id.name', 'ilike', 'brand'),
            ('attribute_id.name', 'ilike', 'ماركة'),
            ('attribute_id.name', 'ilike', 'علامة'),
        ], limit=limit)
        # v2.1.60 — identical logo resolution to the product page +
        # /brands: value binary (dr_image/image) → normalized
        # product.brand name match.
        from .shop_config import _brand_dict
        Brand = None
        if 'product.brand' in request.env:
            Brand = request.env['product.brand'].sudo()
        Tmpl = request.env['product.template'].sudo()
        base = _domain_published_for_app(include_oos=True)
        for v in vals:
            d = _brand_dict(v, Brand, Tmpl, base)
            if d['product_count']:
                out.append({'id': d['value_id'], 'name': d['name'],
                            'image': d['image'],
                            'product_count': d['product_count']})
    except Exception:
        pass
    return out


def _search_vendors(q, ntoks=None, limit=6):
    """Marketplace sellers matching q → [{id, name{en,ar}, logo,
    product_count}]."""
    out = []
    try:
        if 'uellow.vendor' not in request.env:
            return out
        Vendor = request.env['uellow.vendor'].sudo()
        _vd = []
        for _t in (ntoks or [q]):
            _vd += ['|', '|',
                    ('store_name_en', 'ilike', _t),
                    ('store_name_ar', 'ilike', _t),
                    ('name', 'ilike', _t)]
        vs = Vendor.search(_vd, limit=limit)
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

        # v2.1.60 — searches run in the requester's LANGUAGE context so
        # Arabic queries match the Arabic translations (they previously
        # only matched the en_US base names).
        ctx_lang = 'ar_001' if str(lang).startswith('ar') else 'en_US'
        Tmpl = request.env['product.template'].sudo() \
            .with_context(lang=ctx_lang)
        # Search surfaces out-of-stock items so the user can still find
        # a specific product they're looking for, even when it's not
        # listed elsewhere in the app.
        # v2.2.16 — digit-only query also matches the product ID and the
        # exact barcode (admins/support paste IDs straight into search).
        if q.isdigit():
            ors = [('id', '=', int(q)), ('barcode', '=', q),
                   ('default_code', 'ilike', q), ('name', 'ilike', q)]
            domain = _domain_published_for_app(include_oos=True) + \
                ['|'] * (len(ors) - 1) + ors
            records = Tmpl.search(domain, order='create_date desc', limit=100)
        else:
            # v2.2.116 — SAME engine as /products: tokenized + Arabic-normalized
            # (stored x_search_norm index) + synonym expansion + relevance rank,
            # with a pg_trgm word-similarity fuzzy fallback. This is the endpoint
            # the app's live search bar hits, so the whole app search benefits.
            _toks = [t for t in _norm_light(q).split(' ') if len(t) >= 2] \
                or [_norm_light(q)]
            _nq = _norm_full(q)
            _base = _domain_published_for_app(include_oos=True)
            domain = list(_base)
            _fields = Tmpl._fields
            _or_leaves = []
            for _tok in _toks:
                _lv = [('x_search_norm', 'ilike', _norm_full(_tok)),
                       ('name', 'ilike', _tok),
                       ('description_sale', 'ilike', _tok),
                       ('default_code', 'ilike', _tok),
                       ('public_categ_ids.name', 'ilike', _tok)]
                for _sy in _syn_expand(_tok):
                    _lv.append(('x_search_norm', 'ilike', _sy))
                if 'brand_id' in _fields:
                    _lv.append(('brand_id.name', 'ilike', _tok))
                if 'product_tag_ids' in _fields:
                    _lv.append(('product_tag_ids.name', 'ilike', _tok))
                domain += ['|'] * (len(_lv) - 1) + _lv
                _or_leaves += _lv
            records = Tmpl.search(domain, order='create_date desc', limit=300)
            if not records and len(_or_leaves) > 1:
                records = Tmpl.search(
                    _base + ['|'] * (len(_or_leaves) - 1) + _or_leaves,
                    order='create_date desc', limit=200)
            if records:
                records = _rank_by_relevance(records, _toks, _nq)
            else:
                records = _fuzzy_search(request.env, _base, _nq, limit=100)

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

        # Matched categories (normalized + tokenized) + brands + sellers
        _cntoks = [t for t in _norm_light(q).split(' ') if len(t) >= 2] \
            or [_norm_light(q)]
        _cnq = _norm_full(q)
        categories = _search_categories(_cntoks, _cnq, ctx_lang, limit=8)
        brands = _search_brands(q, _cntoks)
        vendors = _search_vendors(q, _cntoks)
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
        # v2.2.16 — over-fetch then clean: only clear words (no barcodes /
        # numbers / half-typed prefixes) and only searches that found
        # something at least once.
        # v2.2.40 — language-scoped by SCRIPT: Arabic-script terms only on the
        # Arabic UI, Latin terms only on the English UI (covers legacy rows too).
        request.env.cr.execute("""
            SELECT keyword, COUNT(*) AS cnt
            FROM mobile_search_analytic
            WHERE keyword IS NOT NULL AND keyword NOT LIKE '[barcode]%%'
            """ + _lang_script_clause() + _website_clause() + """
            GROUP BY keyword
            HAVING MAX(results_count) > 0
            ORDER BY cnt DESC
            LIMIT 80
        """)
        rows = request.env.cr.fetchall()
        return ok(_fold_incomplete(rows, 12))

    @http.route('/api/mobile/v2/search/trending', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def trending_today(self, **kw):
        """Top searched keywords in the last 24h. Falls back to last
        7d / 30d if today is empty."""
        for days in (1, 7, 30):
            since = datetime.utcnow() - timedelta(days=days)
            # v2.2.16 — over-fetch then clean: only clear words (no
            # barcodes / numbers / half-typed prefixes) and only searches
            # that found something at least once.
            request.env.cr.execute("""
                SELECT keyword, COUNT(*) AS cnt
                FROM mobile_search_analytic
                WHERE create_date >= %s
                  AND keyword IS NOT NULL
                  AND keyword NOT LIKE '[barcode]%%'
                  """ + _lang_script_clause() + _website_clause() + """
                GROUP BY keyword
                HAVING MAX(results_count) > 0
                ORDER BY cnt DESC
                LIMIT 80
            """, (since,))
            rows = request.env.cr.fetchall()
            cleaned = _fold_incomplete(rows, 10)
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
            # v2.2.40 — recent feed is language-scoped by script too.
            if not _matches_ui_lang(kw):
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
