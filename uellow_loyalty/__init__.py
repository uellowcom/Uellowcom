from . import models
from . import controllers


def post_init_hook(env):
    IrCron = env['ir.cron']
    IrModel = env['ir.model']
    model_rec = IrModel.search([('model', '=', 'uellow.loyalty.account')], limit=1)
    if model_rec and not IrCron.search([('name', '=', 'Uellow Loyalty: Expire Points')], limit=1):
        IrCron.create({
            'name': 'Uellow Loyalty: Expire Points',
            'model_id': model_rec.id,
            'state': 'code',
            'code': 'model.cron_expire_points()',
            'interval_number': 1,
            'interval_type': 'days',
            'active': True,
        })
