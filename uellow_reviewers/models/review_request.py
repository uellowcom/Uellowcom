from odoo import models, fields, api
from odoo.exceptions import UserError
import uuid
import datetime


class ReviewRequest(models.Model):
    _name        = 'review.request'
    _description = 'Review Request Session'
    _rec_name    = 'token'
    _order       = 'create_date desc'

    token        = fields.Char(default=lambda self: str(uuid.uuid4())[:12], index=True)
    reviewer_id  = fields.Many2one('reviewer.profile', string='الريفيور', required=True, ondelete='cascade')
    customer_id  = fields.Many2one('res.partner', string='العميل')
    product_id   = fields.Many2one('product.template', string='المنتج')

    session_type = fields.Selection([
        ('written', 'رأي مكتوب'),
        ('chat',    'شات مباشر'),
        ('photo',   'صورة + رأي'),
        ('video',   'مكالمة فيديو'),
    ], string='نوع الجلسة', required=True, default='written')

    state = fields.Selection([
        ('pending',   'بانتظار القبول'),
        ('accepted',  'مقبول'),
        ('active',    'جلسة نشطة'),
        ('completed', 'مكتمل'),
        ('expired',   'منتهي الصلاحية'),
        ('cancelled', 'ملغي'),
    ], default='pending', string='الحالة', index=True)

    # ── Chat messages ─────────────────────────────────────────────────────────
    messages_json   = fields.Text(default='[]')
    reviewer_verdict = fields.Selection([
        ('recommend',    'أنصح بالشراء'),
        ('not_recommend','لا أنصح'),
        ('neutral',      'محايد'),
    ], string='رأي الريفيور')
    reviewer_notes  = fields.Text(string='ملاحظات الريفيور')

    # ── Ratings ───────────────────────────────────────────────────────────────
    quality_rating  = fields.Integer(string='جودة المنتج', default=0)
    value_rating    = fields.Integer(string='القيمة مقابل السعر', default=0)
    comfort_rating  = fields.Integer(string='الراحة', default=0)

    # ── Timing ────────────────────────────────────────────────────────────────
    accepted_at     = fields.Datetime(string='وقت القبول')
    completed_at    = fields.Datetime(string='وقت الإكمال')
    expires_at      = fields.Datetime(string='ينتهي في')

    # ── Commission ────────────────────────────────────────────────────────────
    fee             = fields.Float(string='رسوم الجلسة (KD)')
    commission_pct  = fields.Float(string='نسبة العمولة %')
    commission_amt  = fields.Float(string='مبلغ العمولة (KD)')
    order_id        = fields.Many2one('sale.order', string='الطلب المرتبط')
    commission_paid = fields.Boolean(default=False)

    # ── Customer rating of reviewer ───────────────────────────────────────────
    customer_rating = fields.Integer(string='تقييم العميل للريفيور', default=0)
    customer_review = fields.Text(string='تعليق العميل')

    # ── Try-On image sharing ──────────────────────────────────────────────────
    tryon_image     = fields.Binary(string='صورة Try-On')
    tryon_shared    = fields.Boolean(default=False)

    # Group voting: multiple review.request records sharing the same
    # batch_token form one vote pool over the same try-on image.
    batch_token     = fields.Char(string='Group vote token', index=True,
        help='Identifies a multi-reviewer vote on a single try-on image.')
    tryon_image_id  = fields.Many2one('customer.tryon.image', string='Try-On image record',
        index=True, ondelete='set null',
        help='Link to the try-on image record (lets the reviewer dashboard '
             'show the same generated photo without re-uploading).')
    kind            = fields.Selection([
        ('product_review', 'Product review'),
        ('tryon_opinion',  'Try-on opinion'),
    ], default='product_review', string='Kind')

    def get_messages(self):
        import json
        try:
            return json.loads(self.messages_json or '[]')
        except Exception:
            return []

    def add_message(self, sender, text, msg_type='text'):
        import json
        msgs = self.get_messages()
        msgs.append({
            'sender':    sender,  # 'customer' or 'reviewer'
            'text':      text,
            'type':      msg_type,
            'timestamp': fields.Datetime.now().isoformat(),
        })
        self.messages_json = json.dumps(msgs, ensure_ascii=False)

    def action_accept(self):
        now = fields.Datetime.now()
        # Set expiry based on session type
        ttl = {'written': 30, 'chat': 60, 'photo': 45, 'video': 90}
        minutes = ttl.get(self.session_type, 30)
        self.write({
            'state':       'accepted',
            'accepted_at': now,
            'expires_at':  now + datetime.timedelta(minutes=minutes),
        })
        # Increment reviewer review count
        self.reviewer_id.review_count += 1

    def action_complete(self, verdict=None, notes=None):
        vals = {'state': 'completed', 'completed_at': fields.Datetime.now()}
        if verdict: vals['reviewer_verdict'] = verdict
        if notes:   vals['reviewer_notes']   = notes
        self.write(vals)
        self._calculate_commission()

    def action_expire(self):
        self.write({'state': 'expired'})

    def _calculate_commission(self):
        """Calculate commission if linked order was placed."""
        if not self.order_id:
            return
        env  = self.env
        pct  = float(env['ir.config_parameter'].sudo().get_param(
            f'uellow_reviewers.commission_{self.session_type}', '5'
        ))
        order_amount = self.order_id.amount_total
        commission   = round(order_amount * pct / 100, 3)
        self.write({
            'commission_pct': pct,
            'commission_amt': commission,
        })
        # Add to reviewer wallet
        self.reviewer_id.wallet_balance += commission
        self.reviewer_id.total_earned   += commission
        self.reviewer_id.purchase_count += 1

    def to_dict(self):
        import json
        tryon_url = ''
        # Preferred: binary image attached to the customer.tryon.image record.
        if self.tryon_image_id and self.tryon_image_id.image:
            tryon_url = '/web/image/customer.tryon.image/%d/image' % self.tryon_image_id.id
        # Fallback: provider URL (Replicate / FASHN CDN) — used when we only
        # have the remote URL, not a stored binary.
        elif self.tryon_image_id and getattr(self.tryon_image_id, 'image_url', ''):
            tryon_url = self.tryon_image_id.image_url
        elif self.tryon_image:
            # Legacy binary on the request itself
            tryon_url = '/web/image/review.request/%d/tryon_image' % self.id
        # Final fallback: ir.attachment we created when posting the request
        if not tryon_url:
            att = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'review.request'),
                ('res_id',    '=', self.id),
                ('mimetype', 'like', 'image/%'),
            ], limit=1, order='id desc')
            if att:
                tryon_url = '/web/image/ir.attachment/%d/datas' % att.id
        return {
            'id':           self.id,
            'token':        self.token,
            'session_type': self.session_type,
            'kind':         getattr(self, 'kind', '') or 'product_review',
            'batch_token':  self.batch_token or '',
            'state':        self.state,
            'reviewer':     self.reviewer_id.to_dict() if self.reviewer_id else {},
            'product':      {
                'id':        self.product_id.id,
                'name':      self.product_id.name,
                'image_url': '/web/image/product.template/%d/image_256' % self.product_id.id,
            } if self.product_id else {},
            'tryon_image_url': tryon_url,
            'messages':     self.get_messages(),
            'verdict':      self.reviewer_verdict,
            'notes':        self.reviewer_notes or '',
            'ratings': {
                'quality':  self.quality_rating,
                'value':    self.value_rating,
                'comfort':  self.comfort_rating,
            },
            'expires_at':   self.expires_at.isoformat() if self.expires_at else '',
            'create_date':  self.create_date.isoformat() if self.create_date else '',
        }
