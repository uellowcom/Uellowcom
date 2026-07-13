# -*- coding: utf-8 -*-
"""dropship.import.service — the auto-import engine (cron-driven, load-aware).

Design goals:
  * NEVER load the server: off-peak window, load-average guard, small batches
    with per-batch commits, a per-run time budget, and a rate-limit delay
    between provider calls.
  * Respect every eligibility/exclusion setting before a listing is stored.
  * Idempotent: re-running only upserts, it never duplicates.
"""
import logging
import os
import re
import time

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DropshipImportService(models.AbstractModel):
    _name = 'dropship.import.service'
    _description = 'Dropship Auto-import Service'

    # ------------------------------------------------------------------ #
    # cron entrypoint
    # ------------------------------------------------------------------ #
    @api.model
    def cron_auto_import(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.enabled') not in ('True', '1', 'true'):
            return
        if ICP.get_param('uellow_dropship.auto_import') not in ('True', '1', 'true'):
            return
        if not self._window_ok(ICP):
            _logger.info("dropship import: outside off-peak window, skipping")
            return
        if not self._load_ok(ICP):
            _logger.info("dropship import: server busy, skipping this run")
            return
        self._run(ICP)

    # ------------------------------------------------------------------ #
    # guards
    # ------------------------------------------------------------------ #
    def _window_ok(self, ICP):
        if ICP.get_param('uellow_dropship.offpeak_only') not in ('True', '1', 'true'):
            return True
        start = int(ICP.get_param('uellow_dropship.offpeak_start', 1) or 1)
        end = int(ICP.get_param('uellow_dropship.offpeak_end', 6) or 6)
        hour = fields.Datetime.context_timestamp(self, fields.Datetime.now()).hour
        # window may wrap past midnight
        return start <= hour < end if start <= end else (hour >= start or hour < end)

    def _load_ok(self, ICP):
        if ICP.get_param('uellow_dropship.pause_when_busy') not in ('True', '1', 'true'):
            return True
        try:
            load1 = os.getloadavg()[0]
        except (OSError, AttributeError):
            return True
        max_load = float(ICP.get_param('uellow_dropship.max_load', 4.0) or 4.0)
        return load1 <= max_load

    # ------------------------------------------------------------------ #
    # the run
    # ------------------------------------------------------------------ #
    def _cfg(self, ICP, opts=None):
        """Build the effective run config. ``opts`` (from the import wizard or a
        schedule) overrides the global settings for that one run; anything not
        supplied falls back to the module settings."""
        opts = opts or {}

        def _split(v):
            return [x.strip() for x in (v or '').split(',') if x.strip()]

        return {
            # NOTE: the extra `or DEFAULT` AFTER int() is deliberate — a param
            # stored as the STRING '0' (a past corruption) is truthy, so
            # `get_param() or DEFAULT` would keep '0' → int 0 and silently break
            # imports (0 scan = 0 results). The outer `or DEFAULT` catches int 0.
            'deadline': time.time() + (int(opts.get('time_budget') or ICP.get_param('uellow_dropship.cron_time_budget', 120) or 120) or 120),
            'batch': int(ICP.get_param('uellow_dropship.import_batch_size', 50) or 50) or 50,
            'rate_ms': int(ICP.get_param('uellow_dropship.rate_limit_ms', 300) or 300),
            'max_products': int(opts.get('max_products') or ICP.get_param('uellow_dropship.import_max_products', 500) or 500) or 500,
            'max_listings': int(ICP.get_param('uellow_dropship.max_listings', 0) or 0),
            'max_scan': int(opts.get('max_scan') or ICP.get_param('uellow_dropship.import_max_scan', 4000) or 4000) or 4000,
            'keywords': opts.get('keywords') if opts.get('keywords') is not None
                        else _split(ICP.get_param('uellow_dropship.import_keywords')),
            'categories': opts.get('categories') if opts.get('categories') is not None
                          else _split(ICP.get_param('uellow_dropship.import_categories')),
            'min_orders': int(opts.get('min_orders') or ICP.get_param('uellow_dropship.import_min_orders', 0) or 0),
            'min_rating': float(opts.get('min_rating') or ICP.get_param('uellow_dropship.import_min_rating', 0.0) or 0.0),
            'min_price': float(opts.get('min_price') or 0.0),
            'max_price': float(opts.get('max_price') or ICP.get_param('uellow_dropship.max_price', 0) or 0),
            'provider_ids': opts.get('provider_ids'),
            'source_ids': opts.get('source_ids'),
            # per-run behaviour flags (wizard / schedule)
            'skip_existing': bool(opts.get('skip_existing')),
            'require_video': bool(opts.get('require_video')),
            'mark_as_deal': bool(opts.get('mark_as_deal')),
            # fetch full detail (reviews/specs/shipping) inline while importing,
            # so listings are complete immediately. Default on; bounded by the
            # run deadline so a big batch still finishes.
            'enrich_on_import': (opts.get('enrich_on_import')
                                 if opts.get('enrich_on_import') is not None
                                 else ICP.get_param(
                                     'uellow_dropship.enrich_on_import', 'True')
                                     in ('True', '1', 'true')),
        }

    def _new_source_ids(self, Product, provider, items):
        """Return the subset of item source_ids not already stored for this
        provider — used to skip re-fetching products we already have."""
        sids = [str(u.get('source_id')) for u in items if u.get('source_id')]
        if not sids:
            return set()
        have = Product.search([('provider_id', '=', provider.id),
                               ('source_id', 'in', sids)]).mapped('source_id')
        return {str(s) for s in have}

    def _run(self, ICP, opts=None, hooks=None):
        """Pull products. Called by the auto-import cron (opts=None → global
        settings) and by the wizard / schedules (opts overrides).

        ``hooks`` (optional) = {'progress': fn(pulled, scanned, msg),
        'stop': fn()->bool} lets a background schedule stream progress and be
        cancelled mid-run.
        """
        hooks = hooks or {}
        progress = hooks.get('progress')
        should_stop = hooks.get('stop')
        cfg = self._cfg(ICP, opts)
        Product = self.env['dropship.product']
        pdom = [('active', '=', True), ('state', '=', 'connected'),
                ('code', '!=', 'manual')]
        if cfg['provider_ids']:
            pdom.append(('id', 'in', list(cfg['provider_ids'])))
        providers = self.env['dropship.provider'].search(pdom)

        # ── direct import: fetch specific products by id/URL ──────────────
        if cfg.get('source_ids'):
            prov = providers[:1] or self.env['dropship.provider'].search([
                ('code', '=', 'aliexpress'), ('state', '=', 'connected')], limit=1)
            pulled = 0
            target = len(cfg['source_ids']) or 1
            for provider in prov:
                adapter = provider._adapter()
                for sid in cfg['source_ids']:
                    if should_stop and should_stop():
                        self.env.cr.commit()
                        return pulled
                    if cfg['skip_existing'] and Product.search_count([
                            ('provider_id', '=', provider.id),
                            ('source_id', '=', str(sid))]):
                        continue
                    try:
                        unified = adapter.get_product(sid)
                    except Exception as e:  # noqa: BLE001
                        _logger.info("direct import %s failed: %s", sid, e)
                        continue
                    if not unified:
                        continue
                    unified['source_id'] = unified.get('source_id') or sid
                    if self._excluded(ICP, unified):
                        continue
                    if cfg['require_video'] and not unified.get('video_url'):
                        continue
                    rec = Product._upsert(provider, unified)
                    if cfg['mark_as_deal'] and rec:
                        rec.is_deal = True
                    # direct-by-ID import is deliberate → pull the full detail
                    # (reviews, specs, shipping) right away, not lazily on view.
                    try:
                        rec._enrich_detail(force=True)
                    except Exception:  # noqa: BLE001 - detail is best-effort
                        pass
                    pulled += 1
                    if progress:
                        progress(pulled, pulled, '%d imported' % pulled)
                self.env.cr.commit()
            return pulled

        keywords, categories = cfg['keywords'], cfg['categories']
        collect = hooks.get('collect')  # optional list to append imported ids
        # this provider API is FEED-based: it does not support keyword or
        # category server-side search, so we scan the promo feeds and filter
        # each item locally by title keyword / category. `max_scan` bounds how
        # many items we look through when a narrow filter matches few products.
        cat_ext_ids = self._expand_category_ext_ids(categories) if categories else set()
        kws = [k.lower() for k in (keywords or []) if k]
        pulled = 0
        scanned = 0
        for provider in providers:
            if cfg['max_listings'] and Product.search_count([]) >= cfg['max_listings']:
                _logger.info("dropship import: max_listings reached")
                break
            adapter = provider._adapter()
            feeds = provider._feed_list()
            if feeds:
                jobs = [{'feed_name': f} for f in feeds]
            else:
                # non-feed providers: fall back to real keyword/category search
                jobs = [{'query': kw, 'category': cat}
                        for kw in (keywords or [None]) for cat in (categories or [None])]

            for job in jobs:
                page = 1
                while True:
                    if (time.time() > cfg['deadline'] or pulled >= cfg['max_products']
                            or scanned >= cfg['max_scan']
                            or (should_stop and should_stop())):
                        provider.last_sync = fields.Datetime.now()
                        self.env.cr.commit()
                        return pulled
                    try:
                        items = adapter.search_feed(
                            page=page, page_size=cfg['batch'], **job)
                    except Exception as e:  # noqa: BLE001 - one feed failing must not kill the run
                        _logger.warning("dropship import: %s %s failed: %s", provider.name, job, e)
                        break
                    if not items:
                        break
                    scanned += len(items)
                    # dedup: don't re-fetch products already stored for this provider
                    existing = (self._new_source_ids(Product, provider, items)
                                if cfg['skip_existing'] else set())
                    for unified in items:
                        if pulled >= cfg['max_products']:
                            break
                        if cfg['skip_existing'] and str(unified.get('source_id')) in existing:
                            continue
                        # client-side keyword / category match (feed API can't)
                        if kws and not self._kw_match(kws, unified):
                            continue
                        if cat_ext_ids and str(unified.get('category') or '') not in cat_ext_ids:
                            continue
                        if self._excluded(ICP, unified):
                            continue
                        if cfg['require_video'] and not unified.get('video_url'):
                            continue
                        if self._below_thresholds(cfg, unified):
                            continue
                        rec = Product._upsert(provider, unified)
                        if cfg['mark_as_deal'] and rec:
                            rec.is_deal = True
                        # pull reviews/specs/shipping now so the listing is
                        # complete — but only while we still have time budget.
                        if cfg['enrich_on_import'] and time.time() < cfg['deadline']:
                            try:
                                rec._enrich_detail()
                            except Exception:  # noqa: BLE001 - detail is best-effort
                                pass
                        pulled += 1
                        if collect is not None:
                            collect.append(rec.id)
                    # commit each page so locks are short and memory stays flat
                    self.env.cr.commit()
                    if progress:
                        progress(pulled, scanned,
                                 '%d imported · scanned %d · %s'
                                 % (pulled, scanned,
                                    job.get('feed_name') or 'feed'))
                    if cfg['rate_ms']:
                        time.sleep(cfg['rate_ms'] / 1000.0)
                    if len(items) < cfg['batch']:
                        break  # last page of this feed
                    page += 1
            provider.last_sync = fields.Datetime.now()
            self.env.cr.commit()
        return pulled

    def preview(self, opts=None, limit=60):
        """Scan the provider feeds and RETURN matching products WITHOUT storing
        them — powers the backend 'Browse & Import' screen. Applies the same
        keyword / category / price / rating filters as a real import."""
        ICP = self.env['ir.config_parameter'].sudo()
        cfg = self._cfg(ICP, opts)
        kws = [k.lower() for k in (cfg['keywords'] or []) if k]
        cat_ext_ids = (self._expand_category_ext_ids(cfg['categories'])
                       if cfg['categories'] else set())
        pdom = [('active', '=', True), ('state', '=', 'connected'),
                ('code', '!=', 'manual')]
        if cfg['provider_ids']:
            pdom.append(('id', 'in', list(cfg['provider_ids'])))
        providers = self.env['dropship.provider'].search(pdom)
        Product = self.env['dropship.product'].sudo()
        out = []
        seen = set()
        scanned = 0
        max_scan = cfg['max_scan']
        for provider in providers:
            adapter = provider._adapter()
            feeds = provider._feed_list()
            jobs = ([{'feed_name': f} for f in feeds] if feeds
                    else [{'query': kw} for kw in (kws or [None])])
            for job in jobs:
                page = 1
                while len(out) < limit and scanned < max_scan:
                    try:
                        items = adapter.search_feed(
                            page=page, page_size=cfg['batch'], **job)
                    except Exception:  # noqa: BLE001
                        break
                    if not items:
                        break
                    scanned += len(items)
                    for u in items:
                        if len(out) >= limit:
                            break
                        sid = str(u.get('source_id') or '')
                        if not sid or sid in seen:
                            continue
                        if kws and not self._kw_match(kws, u):
                            continue
                        if cat_ext_ids and str(u.get('category') or '') not in cat_ext_ids:
                            continue
                        if self._excluded(ICP, u):
                            continue
                        if self._below_thresholds(cfg, u):
                            continue
                        seen.add(sid)
                        existing = Product.search(
                            [('provider_id', '=', provider.id),
                             ('source_id', '=', sid)], limit=1)
                        out.append({
                            'provider_id': provider.id,
                            'source_id': sid,
                            'title': u.get('title_en') or '',
                            'image_url': u.get('image_url') or '',
                            'price': u.get('price') or 0.0,
                            'currency': u.get('currency') or 'USD',
                            'orders_text': u.get('orders_text') or '',
                            'rating': self._safe_float(u.get('rating')),
                            'category_name': u.get('category_name') or '',
                            'existing_id': existing.id if existing else False,
                            'published': bool(existing and existing.product_tmpl_id
                                              and existing.product_tmpl_id.is_published),
                        })
                    if len(items) < cfg['batch']:
                        break
                    page += 1
                if len(out) >= limit:
                    break
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _safe_float(v):
        """Parse a provider rating that may be '92.8%', '4.7', '' or None."""
        try:
            return float(str(v).replace('%', '').strip()) if v else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _kw_match(kws, unified):
        """True if the product title (EN or AR) contains any of the keywords."""
        hay = ((unified.get('title_en') or '') + ' '
               + (unified.get('title_ar') or '')).lower()
        return any(k in hay for k in kws)

    def _expand_category_ext_ids(self, categories):
        """Resolve the picked categories (ext_id / code / name) to the FULL set
        of their descendant provider category ids, so picking a parent like
        “Watches” also matches “Men's Watches”, “Women's Watches”, etc.
        Our dropship.category tree mirrors AliExpress, so ext_id == provider id."""
        Cat = self.env['dropship.category'].sudo()
        roots = Cat.browse()
        for token in (categories or []):
            token = str(token).strip()
            if not token:
                continue
            hit = (Cat.search([('ext_id', '=', token)], limit=1)
                   or Cat.search([('code', '=', token)], limit=1)
                   or Cat.search([('name', '=ilike', token)], limit=1))
            if hit:
                roots |= hit
        if not roots:
            # nothing matched locally → fall back to matching the raw tokens
            return {str(t).strip() for t in (categories or []) if str(t).strip()}
        descendants = Cat.search([('id', 'child_of', roots.ids)])
        return {c.ext_id for c in descendants if c.ext_id}

    def _below_thresholds(self, cfg, unified):
        """Per-run quality gate (min orders / rating / price) from the wizard
        or schedule — the global _excluded rules still apply on top of this."""
        try:
            if cfg['min_price'] and (unified.get('price') or 0) < cfg['min_price']:
                return True
            if cfg['min_rating'] and self._safe_float(unified.get('rating')) < cfg['min_rating']:
                return True
            if cfg['min_orders']:
                import re as _re
                sold = int(_re.sub(r'[^\d]', '',
                           str(unified.get('orders_text') or '')) or 0)
                if sold < cfg['min_orders']:
                    return True
        except Exception:  # noqa: BLE001
            return False
        return False

    @api.model
    def run_now(self, opts=None, hooks=None):
        """Synchronous, bounded import used by the wizard 'Run now' button and
        by scheduled imports. Returns the number of products pulled.
        ``hooks`` streams progress / allows cancellation (see ``_run``)."""
        ICP = self.env['ir.config_parameter'].sudo()
        return self._run(ICP, opts=opts, hooks=hooks) or 0

    # ------------------------------------------------------------------ #
    # eligibility / exclusion
    # ------------------------------------------------------------------ #
    def _excluded(self, ICP, unified):
        title = (unified.get('title_en') or '').lower()
        catname = (unified.get('category_name') or '').lower()
        catparent = (unified.get('category_parent') or '').lower()

        def _list(param):
            return [w.strip().lower() for w in (ICP.get_param(param) or '').split(',') if w.strip()]

        # PROHIBITED terms — food / meds / supplements / cosmetics / weapons /
        # vape / alcohol / adult / counterfeit / Israeli goods, etc. Match the
        # title AND the category name/parent. Editable in Settings.
        if ICP.get_param('uellow_dropship.block_restricted', 'True') in ('True', '1', 'true'):
            hay = title + ' ' + catname + ' ' + catparent
            for w in _list('uellow_dropship.block_terms'):
                if not w:
                    continue
                # WHOLE-WORD / whole-phrase match — 'sex' must never hit
                # 'unisex', 'pill' never 'pillow', 'weed' never 'seaweed',
                # 'tablet' never a device, etc. (naive substring caused mass
                # false-positive blocking → "Imported 0").
                if re.search(r'(?<![a-z0-9])%s(?![a-z0-9])'
                             % re.escape(w), hay):
                    return True

        for w in _list('uellow_dropship.exclude_keywords'):
            if w in title:
                return True
        for b in _list('uellow_dropship.exclude_brands'):
            if b in title:
                return True
        if ICP.get_param('uellow_dropship.exclude_no_image') in ('True', '1', 'true') and not unified.get('image_url'):
            return True
        if ICP.get_param('uellow_dropship.exclude_no_video') in ('True', '1', 'true') and not unified.get('video_url'):
            return True
        max_price = float(ICP.get_param('uellow_dropship.max_price', 0) or 0)
        if max_price and (unified.get('price') or 0) > max_price:
            return True
        excat = _list('uellow_dropship.exclude_categories')
        if excat and str(unified.get('category') or '').lower() in excat:
            return True
        # ── flash / limited-time deal guard ──────────────────────────────
        # These provider prices are unstable (they expire), so a stored price
        # goes stale and the customer sees an out-of-date price. Skip them.
        if ICP.get_param('uellow_dropship.exclude_flash_deals') in ('True', '1', 'true'):
            blob = (str(unified.get('raw') or '')
                    + ' ' + str(unified.get('promo_type') or '')).lower()
            if any(m in blob for m in ('seckill', 'flash', 'limitedtimedeal',
                                       'limited_time', 'lightning')):
                return True
        # very large markdowns are almost always short-lived flash prices →
        # optionally skip anything discounted beyond a % ceiling.
        max_disc = float(ICP.get_param('uellow_dropship.max_discount_percent', 0) or 0)
        if max_disc:
            orig = unified.get('original_price') or 0
            price = unified.get('price') or 0
            if orig and price and orig > price:
                disc = (orig - price) / orig * 100.0
                if disc > max_disc:
                    return True
        return False
