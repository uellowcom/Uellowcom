# -*- coding: utf-8 -*-
"""
Beena Coach — self-improvement loop (Phase 1).
==============================================
Beena audits her OWN conversations on a schedule (hourly in the intensive
first week), scores each one, extracts concrete findings (what went wrong,
why, suggested fix), dedupes them by fingerprint, flags lost sales with an
estimated value, and emails the admin IMMEDIATELY on high/critical issues.

The loop: Beena discovers → admin approves → the fix is applied (prompt
"learned lessons" can be applied with one click; code fixes go to the
developer). No automatic code changes ever touch production.
"""
import hashlib
import json
import logging

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'

AUDITOR_PROMPT = """You are Beena Coach — a strict QA auditor for "Beena", the AI shopping
assistant of uellow.com (Kuwait marketplace, Arabic-first customers).
You will receive ONE chat transcript. Audit Beena's performance ONLY (not the customer).

Evaluate: intent understanding, correct tool usage (orders/loyalty/sizes/try-on/cart/
location), hallucination (inventing orders/products/info), context loss (re-greeting,
forgetting what was discussed), formatting quality, speed/efficiency, and whether a
LIKELY SALE WAS LOST (customer showed buying intent then abandoned).

Return STRICT JSON only — no prose, no markdown fences:
{"score": <0-100 overall quality>,
 "lost_sale": <true|false>,
 "lost_value_kd": <estimated KD value of the lost sale, 0 if none>,
 "findings": [
   {"category": "prompt|trigger|bug|data|context|hallucination|ux|other",
    "severity": "low|medium|high|critical",
    "title": "<short specific title, English>",
    "description": "<what exactly went wrong, quote the relevant turn>",
    "suggestion": "<concrete actionable fix — a prompt instruction, a trigger keyword, a code area, or a data fix>"}
 ]}
Rules: empty findings list if the conversation was handled well. Be specific, not generic.
A finding must be actionable. score reflects the customer's experience."""


class BeenaConversationCoachExt(models.Model):
    _inherit = 'beena.conversation'

    coach_analyzed = fields.Boolean(default=False, index=True)
    coach_score = fields.Integer(string='Coach Score', default=0)


class BeenaCoachFinding(models.Model):
    _name = 'beena.coach.finding'
    _description = 'Beena Coach Finding'
    _order = 'severity_rank desc, occurrences desc, id desc'

    run_id = fields.Many2one('beena.coach.run', string='Run', ondelete='set null')
    conversation_id = fields.Many2one('beena.conversation', string='Conversation',
                                      ondelete='set null')
    fingerprint = fields.Char(index=True)
    occurrences = fields.Integer(default=1)
    last_seen = fields.Datetime(default=fields.Datetime.now)
    category = fields.Selection([
        ('prompt', 'Prompt gap'), ('trigger', 'Tool trigger gap'),
        ('bug', 'Code bug'), ('data', 'Data gap'), ('context', 'Context loss'),
        ('hallucination', 'Hallucination'), ('ux', 'UX'), ('other', 'Other'),
    ], required=True, default='other')
    severity = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'),
        ('high', 'High'), ('critical', 'Critical'),
    ], required=True, default='medium')
    severity_rank = fields.Integer(compute='_compute_rank', store=True)
    title = fields.Char(required=True)
    description = fields.Text()
    suggestion = fields.Text(string='Suggested Fix')
    lost_sale = fields.Boolean(string='Lost Sale?')
    lost_value_kd = fields.Float(string='Lost Value (KD)', digits=(10, 3))
    state = fields.Selection([
        ('new', 'New'), ('approved', 'Approved'),
        ('applied', 'Applied'), ('dismissed', 'Dismissed'),
    ], default='new', index=True)
    # v2.1.92 — ONE button. The coach assesses the right action itself;
    # the admin just confirms. lesson = injected into Beena's prompt now;
    # code = queued for the developer.
    recommended_action = fields.Selection([
        ('lesson', '🟢 Lesson — apply to Beena instantly'),
        ('code', '🔧 Code/Data — queue for developer'),
    ], compute='_compute_recommended', store=True, string='Recommended Action')
    recommendation_note = fields.Char(compute='_compute_recommended',
                                      store=True, string='Why')

    @api.depends('severity')
    def _compute_rank(self):
        ranks = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        for r in self:
            r.severity_rank = ranks.get(r.severity, 0)

    @api.depends('category', 'suggestion')
    def _compute_recommended(self):
        # behaviour-class findings are fixable by teaching Beena directly;
        # everything else needs the developer.
        lesson_cats = {'prompt', 'trigger', 'context', 'hallucination', 'ux'}
        notes = {
            'prompt': 'Wording/behaviour gap — a prompt lesson fixes it, no code.',
            'trigger': 'Tool-trigger gap — teachable via lesson, no code.',
            'context': 'Context handling — teachable via lesson, no code.',
            'hallucination': 'Hallucination guard — a lesson stops it, no code.',
            'ux': 'Conversational UX — teachable via lesson, no code.',
            'bug': 'Code bug — needs the developer.',
            'data': 'Missing/incorrect data — needs the developer.',
            'other': 'Unclassified — routed to the developer to be safe.',
        }
        for r in self:
            if r.category in lesson_cats and (r.suggestion or '').strip():
                r.recommended_action = 'lesson'
            else:
                r.recommended_action = 'code'
            r.recommendation_note = notes.get(r.category or 'other',
                                              notes['other'])

    def action_confirm(self):
        """v2.1.92 — the single Approve/Confirm button: executes whatever
        the coach recommended. Lessons go live on Beena immediately;
        code/data findings are marked approved for the developer batch."""
        lessons = self.filtered(lambda r: r.recommended_action == 'lesson')
        if lessons:
            lessons.action_apply_lesson()
        (self - lessons).write({'state': 'approved'})

    def action_confirm_selected(self):
        """v2.2.46 — list-header batch button: Approve every SELECTED row in
        one click (only the ones still 'new'; others are silently skipped).
        In Odoo list views a header object-button receives the ticked records
        as `self`."""
        targets = self.filtered(lambda r: r.state == 'new')
        if targets:
            targets.action_confirm()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Coach',
                'message': '%d finding(s) approved.' % len(targets),
                'type': 'success', 'sticky': False,
            },
        }

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_dismiss(self):
        self.write({'state': 'dismissed'})

    def action_apply_lesson(self):
        """One-click learning: append the approved suggestion to the
        'learned lessons' block injected into Beena's system prompt.
        Only prompt/trigger/context-class findings make sense here."""
        ICP = self.env['ir.config_parameter'].sudo()
        lessons = ICP.get_param('uellow_ai.learned_lessons', '') or ''
        for r in self:
            if not r.suggestion:
                continue
            line = '- %s' % r.suggestion.strip().replace('\n', ' ')[:300]
            if line not in lessons:
                lessons = (lessons + '\n' + line).strip()
            r.state = 'applied'
        ICP.set_param('uellow_ai.learned_lessons', lessons)
        # v2.2.05 — self-maintaining: past 12KB the lessons are distilled
        # back to ≤40 crisp rules via Claude (they once silently grew to
        # 44KB; only the first 8KB reaches Beena's prompt).
        if len(lessons) > 12000:
            try:
                self._distill_lessons()
            except Exception:
                pass

    def _distill_lessons(self):
        import requests as _rq
        ICP = self.env['ir.config_parameter'].sudo()
        lessons = ICP.get_param('uellow_ai.learned_lessons', '') or ''
        api_key = ICP.get_param('uellow_ai.claude_api_key', '')
        if not api_key or len(lessons) < 4000:
            return
        prompt = ("Below are accumulated behavioural lessons for Beena, an "
                  "Arabic/English e-commerce shopping assistant. Distill "
                  "them into AT MOST 40 crisp, non-overlapping imperative "
                  "rules (one line each, <=160 chars, start each with '- '). "
                  "Merge duplicates, drop anything about test/simulated "
                  "data. Output ONLY the rules.\n\n" + lessons[:60000])
        r = _rq.post('https://api.anthropic.com/v1/messages', headers={
            'x-api-key': api_key, 'anthropic-version': '2023-06-01',
            'content-type': 'application/json'}, json={
            'model': 'claude-sonnet-4-6', 'max_tokens': 2500,
            'messages': [{'role': 'user', 'content': prompt}]}, timeout=120)
        out = (r.json().get('content') or [{}])[0].get('text', '').strip()
        if out.startswith('-') and len(out) > 500:
            ICP.set_param('uellow_ai.learned_lessons', out)


class BeenaCoachRun(models.Model):
    _name = 'beena.coach.run'
    _description = 'Beena Coach Analysis Run'
    _order = 'id desc'

    name = fields.Char(default=lambda s: fields.Datetime.now().strftime(
        'Coach run %Y-%m-%d %H:%M'))
    analyzed = fields.Integer(string='Conversations Analyzed')
    findings_new = fields.Integer(string='New Findings')
    findings_dup = fields.Integer(string='Repeated Findings')
    health_score = fields.Integer(string='Health Score (avg)')
    lost_value_kd = fields.Float(string='Lost Sales (KD)', digits=(10, 3))
    cost_usd = fields.Float(digits=(12, 6))
    notes = fields.Text()
    finding_ids = fields.One2many('beena.coach.finding', 'run_id')

    # ── Claude (model-level, cron-safe — no request needed) ────────────
    def _icp(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param(
            'uellow_ai.%s' % key, default)

    def _audit_transcript(self, transcript):
        api_key = self._icp('claude_api_key')
        if not api_key:
            return None
        model = self._icp('coach_model', 'claude-haiku-4-5-20251001')
        import time as _time
        for attempt in (1, 2, 3):
            try:
                resp = requests.post(CLAUDE_API_URL, headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                }, json={
                    'model': model,
                    'max_tokens': 1200,
                    'system': AUDITOR_PROMPT,
                    'messages': [{'role': 'user', 'content': transcript[:6000]}],
                }, timeout=60)
                if resp.status_code == 429 or resp.status_code >= 500:
                    raise Exception('HTTP %s' % resp.status_code)
                data = resp.json()
                txt = ''.join(b.get('text', '') for b in data.get('content', [])
                              if b.get('type') == 'text').strip()
                # tolerate accidental code fences
                if txt.startswith('```'):
                    txt = txt.strip('`').lstrip('json').strip()
                usage = data.get('usage', {}) or {}
                cost = (usage.get('input_tokens', 0) * 1e-6
                        + usage.get('output_tokens', 0) * 5e-6)
                return json.loads(txt), cost
            except Exception as e:
                _logger.warning('Beena Coach audit attempt %d failed: %s',
                                attempt, e)
                if attempt < 3:
                    _time.sleep(15 * attempt)   # back off on rate limits
        return None

    @api.model
    def _cron_coach_analyze(self):
        if self._icp('coach_enabled', 'True') not in ('True', '1', 'true'):
            return
        batch = int(self._icp('coach_batch', '25') or 25)
        Conv = self.env['beena.conversation'].sudo()
        convs = Conv.search([
            ('coach_analyzed', '=', False),
            ('message_count', '>=', 2),
            ('write_date', '<=', fields.Datetime.subtract(
                fields.Datetime.now(), minutes=10)),
        ], order='write_date desc', limit=batch)
        if not convs:
            return
        Finding = self.env['beena.coach.finding'].sudo()
        run = self.sudo().create({})
        new_cnt = dup_cnt = 0
        scores = []
        lost_total = 0.0
        cost_total = 0.0
        urgent = Finding.browse([])
        for conv in convs:
            lines = []
            for m in conv.message_ids.sorted('id')[:40]:
                who = 'CUSTOMER' if m.role == 'user' else 'BEENA'
                lines.append('%s: %s' % (who, (m.body or '')[:400]))
            res = self._audit_transcript('\n'.join(lines))
            conv.write({'coach_analyzed': True})
            if not res:
                continue
            parsed, cost = res
            cost_total += cost
            score = int(parsed.get('score', 0) or 0)
            conv.write({'coach_score': score})
            scores.append(score)
            if parsed.get('lost_sale'):
                lost_total += float(parsed.get('lost_value_kd', 0) or 0)
            for f in parsed.get('findings', []) or []:
                title = (f.get('title') or '')[:200]
                if not title:
                    continue
                cat = f.get('category') if f.get('category') in dict(
                    Finding._fields['category'].selection) else 'other'
                sev = f.get('severity') if f.get('severity') in dict(
                    Finding._fields['severity'].selection) else 'medium'
                fp = hashlib.sha1(('%s|%s' % (cat, title.lower()[:80]))
                                  .encode()).hexdigest()[:16]
                dup = Finding.search([('fingerprint', '=', fp),
                                      ('state', '!=', 'dismissed')], limit=1)
                if dup:
                    dup.write({'occurrences': dup.occurrences + 1,
                               'last_seen': fields.Datetime.now()})
                    dup_cnt += 1
                    continue
                rec = Finding.create({
                    'run_id': run.id, 'conversation_id': conv.id,
                    'fingerprint': fp, 'category': cat, 'severity': sev,
                    'title': title,
                    'description': f.get('description') or '',
                    'suggestion': f.get('suggestion') or '',
                    'lost_sale': bool(parsed.get('lost_sale')),
                    'lost_value_kd': float(parsed.get('lost_value_kd', 0) or 0),
                })
                new_cnt += 1
                if sev in ('high', 'critical'):
                    urgent |= rec
        run.write({
            'analyzed': len(convs), 'findings_new': new_cnt,
            'findings_dup': dup_cnt,
            'health_score': int(sum(scores) / len(scores)) if scores else 0,
            'lost_value_kd': lost_total, 'cost_usd': cost_total,
        })
        if urgent:
            self._notify_urgent(run, urgent)
        return run

    def _notify_urgent(self, run, findings):
        """First-week intensive mode: IMMEDIATE email on high/critical."""
        if self._icp('coach_urgent_email', 'True') not in ('True', '1', 'true'):
            return
        to = self._icp('coach_email', 'ali@uellow.com')
        try:
            rows = ''.join(
                '<li><b>[%s]</b> %s<br/><i>%s</i><br/>💡 %s</li>'
                % (f.severity.upper(), f.title,
                   (f.description or '')[:300], (f.suggestion or '')[:300])
                for f in findings)
            self.env['mail.mail'].sudo().create({
                'subject': '🐝🚨 Beena Coach: %d urgent finding(s) — health %d/100'
                           % (len(findings), run.health_score),
                'email_to': to,
                'body_html': '<p>Beena Coach detected urgent issues:</p>'
                             '<ul>%s</ul><p>Review them in Odoo → Beena → '
                             'Coach Findings.</p>' % rows,
            }).send()
        except Exception as e:
            _logger.warning('coach urgent mail failed: %s', e)


class AiConfigCoachExt(models.TransientModel):
    """🎓 Beena Coach controls inside the main Beena settings panel —
    one panel controls everything (schedule, on/off, model, email…)."""
    _inherit = 'ai.config.settings'

    coach_enabled = fields.Boolean(string='تفعيل المدرّب', default=True)
    coach_interval_number = fields.Integer(string='كل', default=1)
    coach_interval_type = fields.Selection([
        ('hours', 'ساعة/ساعات'), ('days', 'يوم/أيام'),
    ], string='الوحدة', default='hours')
    coach_run_hour = fields.Integer(
        string='ساعة التشغيل (بتوقيت الكويت)', default=8,
        help='يُستخدم في الوضع اليومي: يحدد متى يعمل التقرير (0-23).')
    coach_batch = fields.Integer(string='محادثات لكل دفعة', default=25)
    coach_model = fields.Selection([
        ('claude-haiku-4-5-20251001', 'Haiku 4.5 (أرخص — موصى به)'),
        ('claude-sonnet-4-6',         'Sonnet 4.6 (أدق)'),
    ], string='موديل التدقيق', default='claude-haiku-4-5-20251001')
    coach_email = fields.Char(string='إيميل التقارير', default='ali@uellow.com')
    coach_urgent_email = fields.Boolean(
        string='إيميل فوري للحرج', default=True,
        help='إرسال إيميل فوراً عند اكتشاف مشكلة high/critical.')
    coach_lessons = fields.Text(
        string='الدروس المتعلَّمة',
        help='تُحقن في برومبت بينا. كل سطر درس. تُضاف تلقائياً من زر '
             '«Apply as lesson» ويمكن تحريرها هنا.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        p = self._get_param
        vals = {
            'coach_enabled':      p('coach_enabled', 'True') in ('True', '1', 'true'),
            'coach_batch':        int(p('coach_batch', '25') or 25),
            'coach_model':        p('coach_model', 'claude-haiku-4-5-20251001'),
            'coach_email':        p('coach_email', 'ali@uellow.com'),
            'coach_urgent_email': p('coach_urgent_email', 'True') in ('True', '1', 'true'),
            'coach_run_hour':     int(p('coach_run_hour', '8') or 8),
            'coach_lessons':      p('learned_lessons', ''),
        }
        try:
            cron = self.env.ref('uellow_ai_engine.cron_beena_coach')
            vals['coach_interval_number'] = cron.interval_number
            vals['coach_interval_type'] = cron.interval_type \
                if cron.interval_type in ('hours', 'days') else 'hours'
        except Exception:
            pass
        # only return what the caller asked for (web client contract)
        res.update({k: v for k, v in vals.items()
                    if not fields_list or k in fields_list})
        return res

    def execute(self):
        res = super().execute()
        self._set_param('coach_enabled',      str(self.coach_enabled))
        self._set_param('coach_batch',        str(self.coach_batch or 25))
        self._set_param('coach_model',        self.coach_model or 'claude-haiku-4-5-20251001')
        self._set_param('coach_email',        self.coach_email or 'ali@uellow.com')
        self._set_param('coach_urgent_email', str(self.coach_urgent_email))
        self._set_param('coach_run_hour',     str(self.coach_run_hour or 8))
        self._set_param('learned_lessons',    self.coach_lessons or '')
        try:
            cron = self.env.ref('uellow_ai_engine.cron_beena_coach').sudo()
            vals = {
                'active': bool(self.coach_enabled),
                'interval_number': max(1, self.coach_interval_number or 1),
                'interval_type': self.coach_interval_type or 'hours',
            }
            if (self.coach_interval_type or 'hours') == 'days':
                # schedule next run at the chosen Kuwait hour (UTC+3)
                from datetime import timedelta
                utc_h = (int(self.coach_run_hour or 8) - 3) % 24
                now = fields.Datetime.now()
                nxt = now.replace(hour=utc_h, minute=0, second=0, microsecond=0)
                if nxt <= now:
                    nxt += timedelta(days=1)
                vals['nextcall'] = nxt
            cron.write(vals)
        except Exception as e:
            _logger.warning('coach cron update failed: %s', e)
        return res


class BeenaCoachDashboard(models.Model):
    """🎓 Coach KPI dashboard — one record, one colourful HTML board."""
    _name = 'beena.coach.dashboard'
    _description = 'Beena Coach Dashboard'

    name = fields.Char(default='Beena Coach', readonly=True)
    kpi_html = fields.Html(compute='_compute_kpis', sanitize=False)
    coach_on = fields.Boolean(compute='_compute_kpis')

    @api.model
    def open_dashboard(self):
        rec = self.search([], limit=1) or self.create({})
        return {'type': 'ir.actions.act_window', 'name': '🎓 Coach Dashboard',
                'res_model': self._name, 'res_id': rec.id,
                'view_mode': 'form', 'target': 'current'}

    # ── Instant header controls (no Save needed) ─────────────────────
    def _set_coach_active(self, on):
        self.env['ir.config_parameter'].sudo().set_param(
            'uellow_ai.coach_enabled', str(bool(on)))
        try:
            self.env.ref('uellow_ai_engine.cron_beena_coach').sudo().write(
                {'active': bool(on)})
        except Exception as e:
            _logger.warning('coach cron toggle failed: %s', e)
        return self.open_dashboard()

    def action_enable(self):
        return self._set_coach_active(True)

    def action_disable(self):
        return self._set_coach_active(False)

    def action_run_now(self):
        """⚡ Analyze the pending conversations right now."""
        self.env['beena.coach.run'].sudo()._cron_coach_analyze()
        return self.open_dashboard()

    @staticmethod
    def _card(title, value, sub, bg, fg='#fff'):
        return ('<div style="flex:1;min-width:150px;background:%s;color:%s;'
                'border-radius:14px;padding:16px 18px;box-shadow:0 3px 10px '
                'rgba(0,0,0,.08)"><div style="font-size:12px;opacity:.85">%s'
                '</div><div style="font-size:26px;font-weight:900;margin:2px 0">'
                '%s</div><div style="font-size:11px;opacity:.8">%s</div></div>'
                % (bg, fg, title, value, sub))

    def _compute_kpis(self):
        F = self.env['beena.coach.finding'].sudo()
        R = self.env['beena.coach.run'].sudo()
        ICP = self.env['ir.config_parameter'].sudo()
        runs = R.search([], order='id desc', limit=12)
        last = runs[:1]
        prev = runs[1:2]
        health = last.health_score if last else 0
        trend = ''
        if last and prev:
            d = last.health_score - prev.health_score
            trend = ('▲ +%d' % d) if d > 0 else (('▼ %d' % d) if d < 0 else '＝')
        hcolor = ('linear-gradient(135deg,#2E9E6B,#1F7A50)' if health >= 75
                  else 'linear-gradient(135deg,#E6A817,#C98A00)' if health >= 50
                  else 'linear-gradient(135deg,#D2604E,#A93B2A)')
        sev = {s: F.search_count([('severity', '=', s),
                                  ('state', 'in', ('new', 'approved'))])
               for s in ('critical', 'high', 'medium', 'low')}
        open_cnt = sum(sev.values())
        applied = F.search_count([('state', '=', 'applied')])
        total_f = F.search_count([])
        fix_rate = int(applied * 100 / total_f) if total_f else 0
        lost = sum(F.search([]).mapped('lost_value_kd'))
        cost = sum(R.search([]).mapped('cost_usd'))
        analyzed = sum(R.search([]).mapped('analyzed'))
        enabled = ICP.get_param('uellow_ai.coach_enabled', 'True') in ('True', '1', 'true')
        try:
            cron = self.env.ref('uellow_ai_engine.cron_beena_coach')
            sched = 'كل %d %s' % (cron.interval_number,
                                  'ساعة' if cron.interval_type == 'hours' else 'يوم')
            nxt = fields.Datetime.to_string(cron.nextcall)[:16] if cron.nextcall else '—'
        except Exception:
            sched, nxt = '—', '—'
        # mini bar chart of last runs (oldest → newest)
        bars = ''
        for r in reversed(list(runs)):
            h = max(6, int(r.health_score * 0.6))
            c = '#2E9E6B' if r.health_score >= 75 else '#E6A817' \
                if r.health_score >= 50 else '#D2604E'
            bars += ('<div title="%s — %d/100" style="width:18px;height:%dpx;'
                     'background:%s;border-radius:4px 4px 0 0"></div>'
                     % (r.name, r.health_score, h, c))
        sevrow = ''.join(
            '<span style="background:%s;color:#fff;border-radius:999px;'
            'padding:4px 12px;font-weight:800;font-size:12px;margin-inline-end:6px">'
            '%s %d</span>' % (c, l, sev[k])
            for k, l, c in (('critical', '🔴 حرج', '#A93B2A'),
                            ('high', '🟠 عالي', '#D2604E'),
                            ('medium', '🟡 متوسط', '#E6A817'),
                            ('low', '⚪ منخفض', '#9AA5A1')))
        for rec in self:
            rec.coach_on = enabled
            rec.kpi_html = (
                '<div style="direction:rtl;font-family:inherit">'
                '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px">'
                + self._card('💚 درجة الصحة', '%d/100 <span style="font-size:13px">%s</span>'
                             % (health, trend), 'آخر دفعة تحليل', hcolor)
                + self._card('🗂 اكتشافات مفتوحة', str(open_cnt),
                             'بانتظار المعالجة', 'linear-gradient(135deg,#2F6E62,#1E4B42)')
                + self._card('✅ نسبة الإصلاح', '%d%%' % fix_rate,
                             '%d من %d معالَجة' % (applied, total_f),
                             'linear-gradient(135deg,#7A4FE0,#5634AC)')
                + self._card('💰 مبيعات ضائعة', '%.2f KD' % lost,
                             'فرص مكتشفة للاسترداد', 'linear-gradient(135deg,#C99000,#9A6E00)')
                + self._card('🧪 محادثات مدققة', str(analyzed),
                             'بتكلفة $%.3f' % cost, 'linear-gradient(135deg,#3D6B9E,#27496D)')
                + '</div>'
                '<div style="display:flex;gap:12px;flex-wrap:wrap">'
                '<div style="flex:2;min-width:260px;background:#fff;border:1px solid #E8E8E8;'
                'border-radius:14px;padding:14px 16px">'
                '<div style="font-weight:900;margin-bottom:8px">📈 اتجاه الصحة (آخر الدفعات)</div>'
                '<div style="display:flex;align-items:flex-end;gap:5px;height:70px">'
                + (bars or '<span style="color:#999">لا بيانات بعد</span>') + '</div></div>'
                '<div style="flex:2;min-width:260px;background:#fff;border:1px solid #E8E8E8;'
                'border-radius:14px;padding:14px 16px">'
                '<div style="font-weight:900;margin-bottom:10px">🚦 المفتوحة حسب الخطورة</div>'
                + sevrow +
                '<div style="margin-top:14px;font-size:12px;color:#555">'
                '⚙️ الحالة: <b style="color:%s">%s</b> · الجدولة: <b>%s</b> · '
                'التشغيل القادم (UTC): <b>%s</b></div></div>'
                '</div></div>'
                % ('#2E9E6B' if enabled else '#A93B2A',
                   'شغّال' if enabled else 'متوقف', sched, nxt))
