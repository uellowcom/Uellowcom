# -*- coding: utf-8 -*-
"""مسارات «اختيار المجتمع»:

- الويب: زر الترشيح في صفحة المنتج (أي زائر) → POST /uellow/community/nominate
- التطبيق: نفس الترشيح + جلب أعلى المرشَّحين عبر /api/mobile/v2/community/*
"""
import json
import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _visitor_key():
    """بصمة الجهاز الحالية من الطلب."""
    return request.env['uellow.community.pick'].sudo() \
        ._visitor_key_from_request(request)


def _cur_website_id():
    try:
        return request.website.id if request.website else None
    except Exception:
        return None


def _cur_partner_id():
    try:
        pid = request.env.user.partner_id.id
        # لا نربط ترشيحات الزائر العام (public user) بشريك
        if request.env.user._is_public():
            return None
        return pid
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════
# مسارات الويب (صفحة المنتج في المتصفح)
# ══════════════════════════════════════════════════════════════════════
class CommunityPicksWeb(http.Controller):

    @http.route('/uellow/community/nominate', type='http', auth='public',
                methods=['POST'], csrf=False, website=True)
    def web_nominate(self, **kw):
        """يستقبل {product_id, name} ويعيد JSON {ok, count} أو {error}."""
        Pick = request.env['uellow.community.pick'].sudo()
        try:
            res = Pick.nominate(
                product_id=kw.get('product_id'),
                name=kw.get('name'),
                website_id=_cur_website_id(),
                visitor_key=_visitor_key(),
                partner_id=_cur_partner_id(),
            )
            payload = {'ok': True, 'count': res['count'], 'name': res['name']}
        except UserError as e:
            payload = {'ok': False, 'error': e.args and e.args[0] or 'تعذّر الترشيح.'}
        except Exception:
            _logger.exception('community web nominate failed')
            payload = {'ok': False, 'error': 'حدث خطأ، حاول لاحقًا.'}
        return request.make_response(
            json.dumps(payload),
            headers=[('Content-Type', 'application/json; charset=utf-8')])

    @http.route('/uellow/community/state', type='http', auth='public',
                methods=['GET'], csrf=False, website=True)
    def web_state(self, product_id=None, **kw):
        """هل رشّح هذا الجهاز المنتجَ من قبل؟ (لتعطيل الزر)."""
        Pick = request.env['uellow.community.pick'].sudo()
        done = Pick.has_nominated(product_id, _visitor_key())
        return request.make_response(
            json.dumps({'nominated': bool(done)}),
            headers=[('Content-Type', 'application/json; charset=utf-8')])


# ══════════════════════════════════════════════════════════════════════
# مسارات التطبيق (api_v2) — بنفس مظروف الاستجابة القياسي
# ══════════════════════════════════════════════════════════════════════
try:
    from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import (
        safe_endpoint, get_payload, ok, fail, current_partner,
    )

    class CommunityPicksApp(http.Controller):

        @http.route('/api/mobile/v2/community/nominate', type='http',
                    auth='public', methods=['POST', 'OPTIONS'], csrf=False)
        @safe_endpoint
        def app_nominate(self, **kw):
            p = get_payload()
            Pick = request.env['uellow.community.pick'].sudo()
            try:
                partner = current_partner()
                res = Pick.nominate(
                    product_id=p.get('product_id'),
                    name=p.get('name'),
                    website_id=_cur_website_id(),
                    visitor_key=_visitor_key(),
                    partner_id=partner.id if partner else None,
                )
                return ok({'count': res['count'], 'name': res['name']})
            except UserError as e:
                return fail('NOMINATE_FAILED',
                            e.args and e.args[0] or 'تعذّر الترشيح.', 400)

        @http.route('/api/mobile/v2/community/state', type='http',
                    auth='public', methods=['GET', 'OPTIONS'], csrf=False)
        @safe_endpoint
        def app_state(self, product_id=None, **kw):
            Pick = request.env['uellow.community.pick'].sudo()
            return ok({'nominated':
                       bool(Pick.has_nominated(product_id, _visitor_key()))})

    # ══════════════════════════════════════════════════════════════════
    # جهّز باقتك (Build Kit) — إضافة المنتجات المختارة للسلة + خصم باقة
    # حقيقي محمي بالهامش (يعيد استخدام بنية الكوبونات المثبتة في scratch).
    # ══════════════════════════════════════════════════════════════════
    class BuildKitApp(http.Controller):

        @http.route('/api/mobile/v2/kit/add', type='http', auth='public',
                    methods=['POST', 'OPTIONS'], csrf=False)
        @safe_endpoint
        def kit_add(self, **kw):
            p = get_payload()
            ids = []
            for x in (p.get('product_ids') or []):
                try:
                    ids.append(int(x))
                except Exception:
                    pass
            if not ids:
                return fail('BAD_INPUT', 'product_ids required', 400)
            try:
                disc = float(p.get('bundle_discount') or 0)
            except Exception:
                disc = 0.0
            disc = max(0.0, min(disc, 90.0))

            from odoo.addons.uellow_mobile_manager.controllers.api_v2.cart \
                import _get_or_create_order, serialize_cart, _consolidate_lines
            from odoo.addons.uellow_mobile_manager.controllers.api_v2.loyalty \
                import _gen_code

            Tmpl = request.env['product.template'].sudo()
            tmpls = Tmpl.browse(ids).exists().filtered(
                lambda t: t.is_published and t.active and t.product_variant_ids)
            if not tmpls:
                return fail('NOT_FOUND', 'No valid products', 404)

            order = _get_or_create_order(create=True)
            variant_ids = []
            for t in tmpls:
                prod = t.product_variant_ids[0]
                variant_ids.append(prod.id)
                exists = order.order_line.filtered(
                    lambda l: l.product_id == prod and not l.is_reward_line)
                if not exists:
                    request.env['sale.order.line'].sudo().create({
                        'order_id': order.id, 'product_id': prod.id,
                        'product_uom_qty': 1})

            code = None
            applied = False
            applied_pct = 0
            if disc >= 1:
                # حماية الهامش: لا نخصم تحت التكلفة لأي منتج في الباقة
                safe = int(disc)
                for t in tmpls:
                    cost = float(t.standard_price or 0)
                    price = float(t.list_price or 0)
                    if cost > 0 and price > 0:
                        ms = max(0, min(90, int((1.0 - cost / price) * 100)))
                        safe = min(safe, ms)
                if safe >= 1:
                    applied_pct = safe
                    Program = request.env['loyalty.program'].sudo()
                    Reward = request.env['loyalty.reward'].sudo()
                    Card = request.env['loyalty.card'].sudo()
                    company = request.env.company
                    import hashlib as _hl
                    key = _hl.md5((','.join(map(str, sorted(variant_ids)))
                                   + '|' + str(safe)).encode()).hexdigest()[:10]
                    pname = 'KIT-%s-%d' % (key, safe)
                    prog = Program.search(
                        [('name', '=', pname),
                         ('program_type', '=', 'promo_code')], limit=1)
                    if not prog:
                        prog = Program.create({
                            'name': pname, 'program_type': 'promo_code',
                            'applies_on': 'current', 'active': True,
                            'company_id': company.id,
                            'currency_id': company.currency_id.id})
                        Reward.create({
                            'program_id': prog.id, 'reward_type': 'discount',
                            'discount': safe, 'discount_mode': 'percent',
                            'discount_applicability': 'specific',
                            'discount_product_ids': [(6, 0, variant_ids)],
                            'required_points': 1})
                    from datetime import date as _d, timedelta as _td
                    partner = current_partner()
                    code = _gen_code('KIT', 6)
                    cvals = {'program_id': prog.id, 'code': code, 'points': 1,
                             'expiration_date': _d.today() + _td(days=3)}
                    if partner:
                        cvals['partner_id'] = partner.id
                    Card.create(cvals)
                    try:
                        if order and order.state in ('draft', 'sent') \
                                and hasattr(order, '_try_apply_code'):
                            order._try_apply_code(code)
                            applied = True
                    except Exception:
                        applied = False

            try:
                _consolidate_lines(order)
            except Exception:
                pass
            order = request.env['sale.order'].sudo().browse(order.id)
            return ok({'cart': serialize_cart(order), 'code': code,
                       'pct': applied_pct, 'applied': applied,
                       'added': len(variant_ids)})

except Exception:  # pragma: no cover
    # إن لم تتوفّر أدوات api_v2 لأي سبب، نكتفي بمسارات الويب فقط
    _logger.warning('community: api_v2 helpers unavailable; app routes off')
