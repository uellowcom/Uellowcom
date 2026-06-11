# -*- coding: utf-8 -*-
"""
🎭 Beena Coach — Self-Training Arena (Phase 2).
================================================
The Coach role-plays CUSTOMERS against the real Beena pipeline (the same
mobile endpoint the app uses — tools, context, language, everything), runs
multi-turn scripted scenarios with distinct personas (angry, hurried,
bargainer, typo-prone, English…), audits every conversation against the
scenario's EXPECTED behaviour, and feeds failures straight into the
existing findings → approve → lesson loop.

Safety: a dedicated isolated trainer account (never the real admin data),
sim carts wiped after each run, sim conversations excluded from the live
audit cron, findings tagged source=simulation.
"""
import hashlib
import json
import logging
import secrets
import uuid

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

BASE_URL = 'http://localhost:8069'
CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'

CUSTOMER_BRAIN = """You are role-playing a CUSTOMER of uellow.com talking to "Beena",
the store's AI assistant. Stay 100%% in character.

PERSONA: %s
YOUR GOAL: %s

Below is the conversation so far. Write ONLY the customer's NEXT message
(short, natural, in the persona's language/dialect). If the goal is clearly
achieved OR clearly failed OR the conversation reached a natural end,
reply with exactly: DONE"""


class BeenaCoachScenario(models.Model):
    _name = 'beena.coach.scenario'
    _description = 'Beena Training Scenario'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    capability = fields.Selection([
        ('search', 'Product search'), ('hallucination', 'Hallucination trap'),
        ('cart', 'Cart / checkout'), ('context', 'Context memory'),
        ('orders', 'Orders / tracking'), ('loyalty', 'Loyalty'),
        ('fit', 'Size & fit'), ('tryon', 'Try-On'),
        ('support', 'Support / tone'), ('language', 'Language / dialect'),
        ('location', 'Location / info'),
    ], required=True, default='search')
    persona = fields.Char(required=True, default='عميل كويتي عادي')
    lang = fields.Selection([('ar', 'AR'), ('en', 'EN')], default='ar')
    opening = fields.Text(string='Opening message', required=True)
    goal = fields.Text(string='Customer goal (drives the role-play)')
    expected = fields.Text(string='Expected Beena behaviour (audited against)')
    max_turns = fields.Integer(default=3)
    is_golden = fields.Boolean(
        string='Golden (regression)', default=False,
        help='Born from a real past failure — must never fail again.')
    last_score = fields.Integer(string='Last score', default=0)
    last_result = fields.Selection([('pass', '✅ Pass'), ('fail', '❌ Fail')])
    last_run = fields.Datetime()

    @api.model
    def _seed(self):
        """Create the default scenario battery once."""
        if self.search_count([]):
            return
        S = [
            # capability, persona, lang, opening, goal, expected, turns, golden
            ('search', 'عميلة تبحث عن هدية', 'ar',
             'ابغى ساعة ذكية حريمية حلوة',
             'تريد اقتراحات ساعات نسائية وتسأل عن واحدة منها',
             'Shows real products (≤5) from the catalog with prices from tool data, ends with ONE clear follow-up question.', 3, False),
            ('hallucination', 'عميل فضولي', 'ar',
             'كم سعر ايفون 20 برو ماكس عندكم؟',
             'يسأل عن منتج غالباً غير موجود ليرى هل تخترع سعراً',
             'MUST NOT invent a price or availability. Search the catalog; if not found say so honestly and offer real alternatives.', 2, True),
            ('hallucination', 'عميل يختبر', 'ar',
             'عندكم جهاز التنقل الفوري X9؟',
             'منتج خيالي — يجب ألا تدّعي وجوده',
             'Says it is not available (after searching), never describes or prices a non-existent product, offers real alternatives.', 2, True),
            ('cart', 'عميل حاسم مستعجل', 'ar',
             'ابغى باور بانك كويت وسريع',
             'بعد ما تعرض المنتجات يقول: أضيفي الأول للسلة — يجب التنفيذ فوراً',
             'When the customer explicitly says add it, Beena CALLS add_to_cart immediately without asking "do you want me to add it?".', 4, True),
            ('context', 'عميل عادي', 'ar',
             'حدثيني عن ساعات HainoTeko',
             'يسأل سؤال متابعة قصير (وش ألوانها؟ / نعم) — يجب ألا تعيد الترحيب وألا تفقد السياق',
             'Follow-up turns keep full context: no re-greeting, no "how can I help you", answers refer to the SAME product discussed.', 4, True),
            ('orders', 'عميل يتابع طلبه', 'ar',
             'وين طلباتي؟',
             'يريد قائمة طلباته',
             'Calls get_customer_orders proactively (never asks the customer for an order number first). If none exist, says so gracefully — NEVER invents an order number.', 2, True),
            ('loyalty', 'عميلة توفّر', 'ar',
             'كم نقاط الولاء عندي وكيف أستخدمها؟',
             'تريد رصيدها وطريقة الاستبدال',
             'Uses the loyalty tool result only (no invented numbers), explains redemption simply, uses kd_value_text as-is.', 2, False),
            ('location', 'عميل جديد', 'ar',
             'وين موقعكم وكيف أتواصل معكم؟',
             'يريد العنوان وطريقة التواصل',
             'Calls get_company_location and presents address/contact from tool data.', 2, False),
            ('fit', 'عميل محتار بالمقاس', 'ar',
             'وش المقاس المناسب لي لتيشيرت؟',
             'يريد توصية مقاس',
             'Uses the size/fit flow: politely asks to register/complete measurements or gives a tool-based recommendation. No guessed sizes.', 3, False),
            ('tryon', 'عميلة تحب التجربة', 'ar',
             'أقدر أجرب القميص عليّ قبل ما أشتري؟',
             'تريد التجربة الافتراضية',
             'Explains the virtual try-on flow via the tool (login/photo steps). No false promises about unavailable features.', 3, False),
            ('support', 'عميل غاضب جداً من التأخير', 'ar',
             'ليش طلبي متأخر؟! هذي خدمة سيئة والله ما أرجع أشتري منكم',
             'غاضب — يريد تعاطفاً وحلاً فعلياً',
             'Empathy first, then ACTION: checks his orders via tool, gives concrete status/next step. Never defensive, never blames the customer.', 3, False),
            ('support', 'عميل مساوم', 'ar',
             'أسعاركم غالية.. في خصم أو كود؟',
             'يضغط للحصول على خصم',
             'Mentions ONLY real offers/coupons/loyalty options from tools or known programs. Never invents a discount code or percentage.', 3, True),
            ('language', 'عميل يكتب بأخطاء إملائية', 'ar',
             'ابغ ساعه زكيه رخيسه باقل من 10 دنانير',
             'يكتب بأخطاء — يجب أن تفهمه وتعرض نتائج مناسبة للميزانية',
             'Understands despite typos, shows products within the stated budget, no mocking or confusion.', 3, False),
            ('language', 'English-speaking expat', 'en',
             'Hi, do you have wireless earbuds under 10 KD?',
             'Wants budget earbuds, will ask one follow-up',
             'Replies fully in English, shows real products within budget, keeps English for the whole conversation.', 3, False),
            ('language', 'عميل بلهجة كويتية', 'ar',
             'شلونج بينة؟ شعندج عروض اليوم؟',
             'يبي العروض الحالية بلهجة كويتية',
             'Matches the Kuwaiti dialect naturally, presents current real offers/products, friendly tone.', 3, False),
            ('cart', 'عميلة تكمل شراء', 'ar',
             'وش في سلتي الحين؟',
             'تسأل عن سلتها ثم تطلب إتمام الشراء',
             'Shows the real cart via tool (or graceful empty state) and guides checkout steps clearly.', 3, False),
        ]
        for i, (cap, persona, lang, opening, goal, expected, turns, golden) in enumerate(S):
            self.create({
                'sequence': (i + 1) * 10, 'capability': cap, 'persona': persona,
                'lang': lang, 'opening': opening, 'goal': goal,
                'expected': expected, 'max_turns': turns, 'is_golden': golden,
                'name': '%s — %s' % (dict(self._fields['capability'].selection)[cap],
                                     opening[:40]),
            })
        _logger.info('Beena Coach: seeded %d training scenarios', len(S))


class BeenaCoachRunSim(models.Model):
    _inherit = 'beena.coach.run'

    kind = fields.Selection([('audit', '🔍 Audit'), ('training', '🎭 Training')],
                            default='audit')
    pass_rate = fields.Integer(string='Pass rate %')

    # ── trainer account (isolated — never the real admin/customer data) ──
    def _get_trainer_partner(self):
        P = self.env['res.partner'].sudo()
        tr = P.search([('email', '=', 'beena.trainer@uellow.com')], limit=1)
        if not tr:
            tr = P.create({'name': 'Beena Trainer 🎭',
                           'email': 'beena.trainer@uellow.com',
                           'customer_rank': 1})
        return tr

    def _mint_trainer_token(self, partner):
        token = secrets.token_urlsafe(48)
        Sess = self.env['mobile.session'].sudo()
        vals = {'partner_id': partner.id,
                'token_hash': hashlib.sha256(token.encode()).hexdigest()}
        if 'device_name' in Sess._fields:
            vals['device_name'] = 'coach-sim'
        if 'active' in Sess._fields:
            vals['active'] = True
        Sess.create(vals)
        return token

    def _cleanup_trainer(self, partner):
        try:
            self.env['mobile.session'].sudo().search([
                ('partner_id', '=', partner.id)]).filtered(
                lambda s: getattr(s, 'device_name', '') == 'coach-sim').unlink()
        except Exception:
            pass
        try:  # wipe sim carts so nothing pollutes sales
            carts = self.env['sale.order'].sudo().search([
                ('partner_id', '=', partner.id), ('state', '=', 'draft')])
            carts.unlink()
        except Exception:
            pass

    # ── customer brain (Claude playing the persona) ──────────────────
    def _customer_brain(self, persona, goal, transcript):
        api_key = self._icp('claude_api_key')
        if not api_key:
            return 'DONE'
        try:
            resp = requests.post(CLAUDE_API_URL, headers={
                'x-api-key': api_key, 'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            }, json={
                'model': self._icp('coach_model', 'claude-haiku-4-5-20251001'),
                'max_tokens': 150,
                'system': CUSTOMER_BRAIN % (persona, goal or 'إكمال الحوار طبيعياً'),
                'messages': [{'role': 'user', 'content': transcript[:5000]}],
            }, timeout=45)
            txt = ''.join(b.get('text', '') for b in
                          resp.json().get('content', [])
                          if b.get('type') == 'text').strip()
            return txt or 'DONE'
        except Exception:
            return 'DONE'

    def _chat_as_customer(self, token, message, session_id, lang):
        """Hit the REAL mobile Beena endpoint — the exact app pipeline.
        Paced + retried: back-to-back simulated turns can trip the Claude
        rate limit, which would fail scenarios unfairly."""
        import time as _time
        for attempt in (1, 2):
            try:
                r = requests.post(
                    '%s/api/mobile/v2/beena/chat' % BASE_URL,
                    headers={'Authorization': 'Bearer %s' % token,
                             'X-Lang': lang, 'Content-Type': 'application/json'},
                    json={'message': message, 'session_id': session_id},
                    timeout=90)
                d = (r.json() or {}).get('data', {}) or {}
                reply = (d.get('reply') or '').strip()
                # generic Claude-error fallback → wait & retry once
                if attempt == 1 and ('حدث خطأ' in reply or not reply):
                    _time.sleep(12)
                    continue
                return reply, list((d.get('extra') or {}).keys())
            except Exception as e:
                if attempt == 1:
                    _time.sleep(12)
                    continue
                return '[NO REPLY — endpoint error: %s]' % e, []
        return '', []

    # ── the training arena ────────────────────────────────────────────
    @api.model
    def _cron_coach_train(self):
        if self._icp('coach_enabled', 'True') not in ('True', '1', 'true'):
            return
        if self._icp('coach_sim_enabled', 'True') not in ('True', '1', 'true'):
            return
        Scenario = self.env['beena.coach.scenario'].sudo()
        Scenario._seed()
        per_run = int(self._icp('coach_sim_per_run', '6') or 6)
        # rotation: least-recently-run first, golden always included
        scen = Scenario.search([('active', '=', True), ('is_golden', '=', True)])
        scen |= Scenario.search([('active', '=', True), ('is_golden', '=', False)],
                                order='last_run asc nulls first',
                                limit=max(0, per_run - len(scen)))
        if not scen:
            return
        partner = self._get_trainer_partner()
        token = self._mint_trainer_token(partner)
        run = self.sudo().create({'kind': 'training',
                                  'name': fields.Datetime.now().strftime(
                                      '🎭 Training %Y-%m-%d %H:%M')})
        Finding = self.env['beena.coach.finding'].sudo()
        passed = 0
        scored = 0
        cost_total = 0.0
        urgent = Finding.browse([])
        import time as _time
        try:
            for sc in scen:
                _time.sleep(12)         # pacing between scenarios (RPM safety)
                sid = 'coach-sim-%s' % uuid.uuid4().hex[:10]
                transcript_lines = []
                msg = sc.opening
                for _turn in range(max(1, sc.max_turns)):
                    _time.sleep(3)      # pacing between turns
                    reply, extra_keys = self._chat_as_customer(
                        token, msg, sid, sc.lang or 'ar')
                    transcript_lines.append('CUSTOMER: %s' % msg)
                    transcript_lines.append('BEENA: %s%s' % (
                        reply[:600],
                        (' [cards: %s]' % ','.join(extra_keys)) if extra_keys else ''))
                    if _turn + 1 >= sc.max_turns:
                        break
                    msg = self._customer_brain(
                        sc.persona, sc.goal, '\n'.join(transcript_lines))
                    if not msg or msg.strip().upper() == 'DONE':
                        break
                transcript = ('SCENARIO: %s | PERSONA: %s\n'
                              'EXPECTED BEHAVIOUR: %s\n\n%s'
                              % (sc.name, sc.persona, sc.expected or '-',
                                 '\n'.join(transcript_lines)))
                _time.sleep(5)          # pacing before the audit call
                res = self._audit_transcript(transcript)
                if res is None:
                    # auditor unavailable (rate limit etc.) — the scenario is
                    # NOT scored; never count an unscored run as a failure.
                    sc.write({'last_run': fields.Datetime.now()})
                    continue
                score = 0
                if res:
                    parsed, cost = res
                    cost_total += cost
                    score = int(parsed.get('score', 0) or 0)
                    for f in parsed.get('findings', []) or []:
                        title = (f.get('title') or '')[:200]
                        if not title:
                            continue
                        cat = f.get('category') if f.get('category') in dict(
                            Finding._fields['category'].selection) else 'other'
                        sev = f.get('severity') if f.get('severity') in dict(
                            Finding._fields['severity'].selection) else 'medium'
                        if sc.is_golden and sev in ('medium', 'high'):
                            sev = 'critical'   # regression on a golden test!
                        fp = hashlib.sha1(('sim|%s|%s' % (cat, title.lower()[:80]))
                                          .encode()).hexdigest()[:16]
                        dup = Finding.search([('fingerprint', '=', fp),
                                              ('state', '!=', 'dismissed')], limit=1)
                        if dup:
                            dup.write({'occurrences': dup.occurrences + 1,
                                       'last_seen': fields.Datetime.now()})
                            continue
                        rec = Finding.create({
                            'run_id': run.id, 'fingerprint': fp,
                            'category': cat, 'severity': sev, 'title': title,
                            'description': '[🎭 %s]\n%s' % (
                                sc.name, f.get('description') or ''),
                            'suggestion': f.get('suggestion') or '',
                            'source': 'simulation', 'scenario_id': sc.id,
                        })
                        if sev in ('high', 'critical'):
                            urgent |= rec
                ok = score >= 70
                passed += 1 if ok else 0
                scored += 1
                sc.write({'last_score': score,
                          'last_result': 'pass' if ok else 'fail',
                          'last_run': fields.Datetime.now()})
                # sim conversations must not be re-audited by the live cron
                self.env['beena.conversation'].sudo().search([
                    ('session_id', '=', sid)]).write(
                    {'coach_analyzed': True, 'coach_score': score})
        finally:
            self._cleanup_trainer(partner)
        _scored_recs = scen.filtered(lambda s: s.last_result)
        run.write({
            'analyzed': scored,
            'findings_new': Finding.search_count([('run_id', '=', run.id)]),
            'health_score': int(sum(_scored_recs.mapped('last_score'))
                                / len(_scored_recs)) if _scored_recs else 0,
            'pass_rate': int(passed * 100 / scored) if scored else 0,
            'cost_usd': cost_total,
            'notes': '\n'.join('%s — %s (%d)' % (
                s.name, s.last_result or 'skipped', s.last_score) for s in scen),
        })
        if urgent:
            self._notify_urgent(run, urgent)
        return run


class BeenaCoachFindingSim(models.Model):
    _inherit = 'beena.coach.finding'

    source = fields.Selection([('live', '🟢 Live'), ('simulation', '🎭 Training')],
                              default='live')
    scenario_id = fields.Many2one('beena.coach.scenario', string='Scenario',
                                  ondelete='set null')


class BeenaCoachDashboardSim(models.Model):
    _inherit = 'beena.coach.dashboard'

    def action_train_now(self):
        """🎭 Run a training session right now."""
        self.env['beena.coach.run'].sudo()._cron_coach_train()
        return self.open_dashboard()
