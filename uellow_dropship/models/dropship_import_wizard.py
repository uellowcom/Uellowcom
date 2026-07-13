# -*- coding: utf-8 -*-
"""Professional import interface + scheduled imports.

* ``dropship.import.wizard`` — a rich, one-off import UI (provider, keywords,
  categories, price / orders / rating gates, caps). "Run now" pulls
  immediately; "Save as schedule" turns the same options into a recurring job.
* ``dropship.import.schedule`` — a saved recurring import. A master cron runs
  every due schedule with its OWN options, so you can have e.g. "Jewelry deals
  daily" and "Electronics weekly" side by side.
"""
import re
from datetime import timedelta

from odoo import api, fields, models


def _ids_from(txt):
    """Extract AliExpress product ids from a free-text blob of ids and/or URLs
    (e.g. 'https://www.aliexpress.com/item/1005001322196508.html, 400500...')."""
    out = []
    for tok in re.split(r'[\s,]+', txt or ''):
        tok = tok.strip()
        if not tok:
            continue
        m = re.search(r'(\d{8,})', tok)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


FREQ = [
    ('hours', 'Hours'),
    ('days', 'Days'),
    ('weeks', 'Weeks'),
]


class DropshipImportWizard(models.TransientModel):
    _name = 'dropship.import.wizard'
    _description = 'Import Products'

    provider_ids = fields.Many2many(
        'dropship.provider', string="Providers",
        domain=[('active', '=', True), ('state', '=', 'connected')],
        help="Leave empty to use every connected provider.")
    import_mode = fields.Selection([
        ('search', 'By keywords / categories'),
        ('direct', 'By product ID / URL'),
    ], string="Import Mode", default='search', required=True)
    source_ids = fields.Text(
        string="Product IDs / URLs",
        help="Paste one or more AliExpress product IDs or product URLs "
             "(comma or newline separated) to import those exact products.")
    keywords = fields.Char(
        string="Keywords",
        help="Comma-separated search terms (e.g. 'smart watch, led strip').")
    category_ids = fields.Many2many(
        'dropship.category', string="Categories",
        help="Pick categories to import from (instead of typing names).")
    categories = fields.Char(
        string="Extra Category Codes",
        help="Optional extra provider category codes (comma-separated).")
    min_price = fields.Float(string="Min Price (USD)")
    max_price = fields.Float(string="Max Price (USD)")
    min_orders = fields.Integer(
        string="Min Units Sold",
        help="Only import items the provider has sold at least this many times.")
    min_rating = fields.Float(string="Min Rating (0-5)")
    max_products = fields.Integer(string="Max Products", default=100)
    require_video = fields.Boolean(string="Only With Video")
    skip_existing = fields.Boolean(
        string="Skip Already-imported", default=True,
        help="Don't re-fetch products already in the catalog — each run brings "
             "genuinely new products only.")
    mark_as_deal = fields.Boolean(
        string="Mark Imported as Deals",
        help="Flag every product this run brings in as a deal/offer.")
    enrich_on_import = fields.Boolean(
        string="Fetch Full Detail", default=True,
        help="Pull reviews, specifications and shipping while importing so each "
             "listing is complete immediately (slightly slower).")
    save_as_schedule = fields.Boolean(string="Save as recurring schedule")
    schedule_name = fields.Char(string="Schedule Name")
    interval_number = fields.Integer(string="Every", default=1)
    interval_type = fields.Selection(FREQ, string="Frequency", default='days')

    def _opts(self):
        self.ensure_one()

        def _split(v):
            return [x.strip() for x in (v or '').split(',') if x.strip()]

        # categories from the picker use the provider category id (ext_id) when
        # known, else the readable code/name — both accepted by the feed filter.
        cat_codes = [c.ext_id or c.code or c.name for c in self.category_ids]
        cat_codes += _split(self.categories)

        opts = {
            'provider_ids': self.provider_ids.ids or None,
            'keywords': _split(self.keywords) or None,
            'categories': cat_codes or None,
            'min_price': self.min_price or 0.0,
            'max_price': self.max_price or 0.0,
            'min_orders': self.min_orders or 0,
            'min_rating': self.min_rating or 0.0,
            'max_products': self.max_products or 100,
            'require_video': self.require_video,
            'skip_existing': self.skip_existing,
            'mark_as_deal': self.mark_as_deal,
            'enrich_on_import': self.enrich_on_import,
        }
        if self.import_mode == 'direct':
            opts['source_ids'] = _ids_from(self.source_ids) or None
        return opts

    def action_run(self):
        self.ensure_one()
        if self.save_as_schedule:
            self._create_schedule()
        pulled = self.env['dropship.import.service'].run_now(self._opts())
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import finished',
                'message': '%d product(s) pulled into the source catalog.' % pulled,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'dropship.product',
                    'views': [[False, 'list'], [False, 'form']],
                    'view_mode': 'list,form',
                    'target': 'main',
                },
            },
        }

    def action_save_schedule(self):
        self.ensure_one()
        sched = self._create_schedule()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dropship.import.schedule',
            'res_id': sched.id,
            'views': [[False, 'form']],
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_schedule(self):
        return self.env['dropship.import.schedule'].create({
            'name': self.schedule_name or (self.keywords or 'Import') + ' schedule',
            'provider_ids': [(6, 0, self.provider_ids.ids)],
            'category_ids': [(6, 0, self.category_ids.ids)],
            'keywords': self.keywords,
            'categories': self.categories or False,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'min_orders': self.min_orders,
            'min_rating': self.min_rating,
            'max_products': self.max_products,
            'require_video': self.require_video,
            'skip_existing': self.skip_existing,
            'mark_as_deal': self.mark_as_deal,
            'enrich_on_import': self.enrich_on_import,
            'interval_number': self.interval_number or 1,
            'interval_type': self.interval_type or 'days',
        })


class DropshipImportSchedule(models.Model):
    _name = 'dropship.import.schedule'
    _description = 'Scheduled Import'
    _order = 'next_run'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    provider_ids = fields.Many2many('dropship.provider', string="Providers")
    category_ids = fields.Many2many(
        'dropship.category', string="Categories",
        help="Pick AliExpress categories to import from (no need to type codes).")
    keywords = fields.Char()
    categories = fields.Char(
        string="Extra Category Codes",
        help="Optional extra provider category codes (comma-separated).")
    min_price = fields.Float(string="Min Price (USD)")
    max_price = fields.Float(string="Max Price (USD)")
    min_orders = fields.Integer(string="Min Units Sold")
    min_rating = fields.Float(string="Min Rating")
    max_products = fields.Integer(string="Max Products / Run", default=100)
    require_video = fields.Boolean(string="Only With Video")
    skip_existing = fields.Boolean(
        string="Skip Already-imported", default=True,
        help="Don't re-fetch products already in the catalog — each run brings "
             "genuinely new products only.")
    mark_as_deal = fields.Boolean(string="Mark Imported as Deals")
    enrich_on_import = fields.Boolean(
        string="Fetch Full Detail", default=True,
        help="Pull reviews, specs and shipping while importing so each listing "
             "is complete immediately (slightly slower).")

    interval_number = fields.Integer(string="Every", default=1, required=True)
    interval_type = fields.Selection(FREQ, string="Frequency",
                                     default='days', required=True)
    next_run = fields.Datetime(
        string="Next Run", default=lambda s: fields.Datetime.now())
    last_run = fields.Datetime(string="Last Run", readonly=True)
    run_count = fields.Integer(string="Runs", readonly=True, default=0)
    imported_total = fields.Integer(string="Imported (total)",
                                    readonly=True, default=0)
    last_imported = fields.Integer(string="Last Batch", readonly=True, default=0)
    last_scanned = fields.Integer(string="Last Scanned", readonly=True, default=0)
    last_imported_ids = fields.Many2many(
        'dropship.product', 'ds_schedule_last_import_rel',
        'schedule_id', 'product_id', string="Last Imported Products",
        readonly=True, copy=False,
        help="The exact products the most recent run brought in.")

    # ── live run status (for the progress bar + stop button) ──────────────
    state = fields.Selection([
        ('idle', 'Idle'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    ], default='idle', readonly=True, copy=False)
    progress = fields.Float(string="Progress %", readonly=True, copy=False)
    progress_text = fields.Char(string="Status", readonly=True, copy=False)
    stop_requested = fields.Boolean(readonly=True, copy=False)
    last_error = fields.Char(readonly=True, copy=False)

    def _opts(self):
        self.ensure_one()

        def _split(v):
            return [x.strip() for x in (v or '').split(',') if x.strip()]

        cat_codes = [c.ext_id or c.code or c.name for c in self.category_ids]
        cat_codes += _split(self.categories)
        return {
            'provider_ids': self.provider_ids.ids or None,
            'keywords': _split(self.keywords) or None,
            'categories': cat_codes or None,
            'min_price': self.min_price or 0.0,
            'max_price': self.max_price or 0.0,
            'min_orders': self.min_orders or 0,
            'min_rating': self.min_rating or 0.0,
            'max_products': self.max_products or 100,
            'require_video': self.require_video,
            'skip_existing': self.skip_existing,
            'mark_as_deal': self.mark_as_deal,
            'enrich_on_import': self.enrich_on_import,
            # keyword/category scans need more time than the short cron budget
            'time_budget': 300,
        }

    def _bump_next(self):
        self.ensure_one()
        delta = {self.interval_type: max(1, self.interval_number)}
        self.next_run = fields.Datetime.now() + timedelta(**delta)

    # ------------------------------------------------------------------ #
    # background run with live progress + stop
    # ------------------------------------------------------------------ #
    def action_run_now(self):
        """Kick off the import in a background thread so the UI stays live and
        the run can report progress / be stopped."""
        import threading
        for rec in self:
            if rec.state == 'running':
                return rec._notify('Already running',
                                   'This schedule is already importing.', 'warning')
            rec.write({'state': 'running', 'progress': 0.0,
                       'progress_text': 'Starting…', 'stop_requested': False,
                       'last_error': False})
            rec.env.cr.commit()
            uid = rec.env.uid
            sid = rec.id
            dbname = rec.env.cr.dbname
            threading.Thread(
                target=rec._threaded_run, args=(dbname, sid, uid),
                name='ds-import-%s' % sid, daemon=True).start()
        return self._notify(
            'Import started',
            'Running in the background — the progress bar updates as it goes. '
            'Use “Refresh” to see progress and “Stop” to cancel.', 'success')

    def _threaded_run(self, dbname, sched_id, uid):
        """Runs in its own thread + cursor; streams progress into the record."""
        from odoo import registry, api as _api
        from odoo import SUPERUSER_ID  # noqa: F401
        db_registry = registry(dbname)
        with db_registry.cursor() as cr:
            env = _api.Environment(cr, uid, {})
            sched = env['dropship.import.schedule'].browse(sched_id)
            try:
                opts = sched._opts()
                target = float(opts.get('max_products') or 100)
                stats = {'scanned': 0}

                def _progress(pulled, scanned, msg=''):
                    stats['scanned'] = scanned
                    sched.write({
                        'progress': min(100.0, round(pulled * 100.0 / max(1.0, target), 1)),
                        'progress_text': msg or ('%d imported' % pulled)})
                    cr.commit()

                def _stop():
                    cr.commit()  # end txn so the next read sees a committed flag
                    sched.invalidate_recordset(['stop_requested'])
                    return bool(sched.stop_requested)

                collected = []
                pulled = env['dropship.import.service'].run_now(
                    opts, hooks={'progress': _progress, 'stop': _stop,
                                 'collect': collected})
                stopped = bool(sched.stop_requested)
                sched.write({
                    'state': 'stopped' if stopped else 'done',
                    'progress': 100.0 if not stopped else sched.progress,
                    'progress_text': ('Stopped · %d imported' if stopped
                                      else 'Done · %d imported') % pulled,
                    'last_run': fields.Datetime.now(),
                    'run_count': sched.run_count + 1,
                    'imported_total': sched.imported_total + pulled,
                    'last_imported': pulled,
                    'last_scanned': stats['scanned'],
                    'last_imported_ids': [(6, 0, collected)],
                    'stop_requested': False,
                })
                sched._bump_next()
                cr.commit()
            except Exception as e:  # noqa: BLE001
                cr.rollback()
                sched.write({'state': 'error', 'last_error': str(e)[:500],
                             'progress_text': 'Error — see log'})
                cr.commit()

    def action_stop(self):
        """Request the running import to stop at the next checkpoint."""
        self.write({'stop_requested': True, 'progress_text': 'Stopping…'})
        return self._notify('Stopping', 'The import will stop shortly.', 'info')

    def action_refresh(self):
        """Reload the form so the latest progress shows."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'views': [[False, 'form']],
            'view_mode': 'form',
            'target': 'current',
        }

    def _notify(self, title, message, kind='info'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': title, 'message': message,
                       'type': kind, 'sticky': False},
        }

    @api.model
    def _cron_run_schedules(self):
        """Master cron: run every schedule whose next_run is due. Runs inline
        (not threaded) inside the cron worker, honouring the same options."""
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.enabled') not in ('True', '1', 'true'):
            return
        now = fields.Datetime.now()
        due = self.search([('active', '=', True), ('next_run', '<=', now),
                          ('state', '!=', 'running')])
        for sched in due:
            try:
                collected = []
                pulled = self.env['dropship.import.service'].run_now(
                    sched._opts(), hooks={'collect': collected})
                sched.write({
                    'last_run': fields.Datetime.now(),
                    'run_count': sched.run_count + 1,
                    'imported_total': sched.imported_total + pulled,
                    'last_imported': pulled,
                    'last_imported_ids': [(6, 0, collected)],
                    'state': 'done',
                    'progress': 100.0,
                    'progress_text': 'Done · %d imported' % pulled,
                })
                sched._bump_next()
                self.env.cr.commit()
            except Exception:  # noqa: BLE001 - one schedule must not kill the run
                self.env.cr.rollback()
                # still push next_run so a broken schedule doesn't hot-loop
                sched._bump_next()
                self.env.cr.commit()
