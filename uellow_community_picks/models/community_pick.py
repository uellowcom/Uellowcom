# -*- coding: utf-8 -*-
"""نموذج «اختيار المجتمع»: ترشيحات الزوّار للمنتجات.

كل سجل = ترشيح واحد من زائر لمنتج واحد، باسمه الأول. يظهر المنتج فورًا في
بلوك «اختيار المجتمع» مرتّبًا حسب عدد الترشيحات (اختيار المالك: ظهور فوري
بلا مراجعة أدمن، مع حدٍّ بسيط لمنع التكرار/العبث من نفس الجهاز).
"""
import hashlib
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# الحدّ الأقصى للترشيحات من نفس الجهاز خلال ساعة (حماية بسيطة من العبث)
_HOURLY_CAP = 25
# الطول الأقصى لاسم المُرشِّح
_NAME_MAX = 24


class CommunityPick(models.Model):
    _name = 'uellow.community.pick'
    _description = 'Community Product Pick'
    _order = 'id desc'
    _rec_name = 'nominator_name'

    product_tmpl_id = fields.Many2one(
        'product.template', string='المنتج', required=True,
        ondelete='cascade', index=True)
    nominator_name = fields.Char(string='اسم المُرشِّح', required=True)
    website_id = fields.Many2one('website', string='الموقع', index=True)
    # بصمة الجهاز (تجزئة IP+المتصفح) — لمنع التكرار دون تخزين IP صريح
    visitor_key = fields.Char(string='بصمة الزائر', index=True)
    partner_id = fields.Many2one('res.partner', string='العميل (إن سجّل دخول)')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        # ترشيح واحد لكل (جهاز، منتج) — يمنع تكرار نفس الزائر لنفس المنتج
        ('uniq_visitor_product',
         'unique(product_tmpl_id, visitor_key)',
         'لقد رشّحت هذا المنتج من قبل.'),
    ]

    # ─────────────────────────────────────────────────────────────────
    # أدوات مساعدة
    # ─────────────────────────────────────────────────────────────────
    @api.model
    def _visitor_key_from_request(self, request):
        """بصمة مموّهة للزائر من عنوان IP + وكيل المتصفح."""
        try:
            ip = request.httprequest.remote_addr or ''
            ua = request.httprequest.user_agent.string if \
                request.httprequest.user_agent else ''
        except Exception:
            ip, ua = '', ''
        raw = ('%s|%s' % (ip, ua)).encode('utf-8', 'ignore')
        return hashlib.sha256(raw).hexdigest()[:32]

    @api.model
    def _clean_name(self, name):
        """تنظيف اسم المُرشِّح: إزالة الفراغات الزائدة والرموز الغريبة."""
        name = (name or '').strip()
        # نسمح بالحروف العربية/اللاتينية والأرقام والمسافة فقط
        name = re.sub(r'[^\w؀-ۿ \.\-]', '', name, flags=re.UNICODE)
        name = re.sub(r'\s+', ' ', name).strip()
        return name[:_NAME_MAX]

    @api.model
    def nominate(self, product_id, name, website_id=None,
                 visitor_key=None, partner_id=None):
        """تسجيل ترشيح جديد. يعيد dict فيه عدد الترشيحات الحالي للمنتج.

        يرفع UserError برسالة عربية واضحة عند الفشل (منتج غير صالح/اسم ناقص/
        تكرار/تجاوز الحدّ) ليعرضها الزر للمستخدم.
        """
        name = self._clean_name(name)
        if not name or len(name) < 2:
            raise UserError('يرجى كتابة اسمك (حرفان على الأقل).')
        try:
            product_id = int(product_id)
        except Exception:
            raise UserError('منتج غير صالح.')
        Tmpl = self.env['product.template'].sudo().browse(product_id)
        if not Tmpl.exists() or not Tmpl.is_published or not Tmpl.active:
            raise UserError('هذا المنتج غير متاح للترشيح.')

        if not visitor_key:
            raise UserError('تعذّر التحقّق من الجهاز.')

        Sudo = self.sudo()
        # حدّ بسيط لمنع الإغراق: عدد ترشيحات هذا الجهاز خلال آخر ساعة
        last_hour = fields.Datetime.subtract(fields.Datetime.now(), hours=1)
        recent = Sudo.search_count([
            ('visitor_key', '=', visitor_key),
            ('create_date', '>=', last_hour)])
        if recent >= _HOURLY_CAP:
            raise UserError('لقد أضفت ترشيحات كثيرة، حاول لاحقًا.')

        # منع التكرار لنفس المنتج من نفس الجهاز
        dup = Sudo.search_count([
            ('visitor_key', '=', visitor_key),
            ('product_tmpl_id', '=', product_id)])
        if dup:
            raise UserError('لقد رشّحت هذا المنتج من قبل. شكرًا لك!')

        try:
            Sudo.create({
                'product_tmpl_id': product_id,
                'nominator_name': name,
                'website_id': website_id or False,
                'visitor_key': visitor_key,
                'partner_id': partner_id or False,
            })
        except ValidationError:
            raise UserError('لقد رشّحت هذا المنتج من قبل. شكرًا لك!')

        count = Sudo.search_count([
            ('product_tmpl_id', '=', product_id), ('active', '=', True)])
        return {'ok': True, 'count': count, 'name': name}

    @api.model
    def has_nominated(self, product_id, visitor_key):
        """هل رشّح هذا الجهاز المنتجَ من قبل؟ (لإخفاء/تعطيل الزر)."""
        if not visitor_key or not product_id:
            return False
        return bool(self.sudo().search_count([
            ('visitor_key', '=', visitor_key),
            ('product_tmpl_id', '=', int(product_id))]))

    @api.model
    def _top_picks(self, limit=10, website_ids=None):
        """أعلى المنتجات ترشيحًا: يعيد قائمة dicts [{product_id, count,
        latest_name}] مرتّبة تنازليًا. تُستخدم من مُحلِّل البلوك.
        """
        limit = max(1, min(int(limit or 10), 30))
        where = "active = true"
        params = []
        if website_ids:
            where += " AND (website_id IN %s OR website_id IS NULL)"
            params.append(tuple(website_ids))
        self.env.cr.execute("""
            SELECT product_tmpl_id,
                   COUNT(*) AS n,
                   (ARRAY_AGG(nominator_name ORDER BY id DESC))[1] AS latest
              FROM uellow_community_pick
             WHERE %s
          GROUP BY product_tmpl_id
          ORDER BY n DESC, MAX(id) DESC
             LIMIT %%s
        """ % where, params + [limit])
        rows = self.env.cr.dictfetchall()
        return [{'product_id': r['product_tmpl_id'],
                 'count': int(r['n'] or 0),
                 'latest_name': r['latest'] or ''} for r in rows]
