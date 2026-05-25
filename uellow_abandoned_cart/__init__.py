from . import models


def post_init_hook(env):
    IrCron = env['ir.cron']
    IrModel = env['ir.model']
    for model_name, method, name, interval_number, interval_type in [
        ('uellow.abandoned.cart', 'cron_detect_abandoned',
         'Uellow: Detect Abandoned Carts', 1, 'hours'),
        ('uellow.abandoned.cart', 'cron_send_recovery',
         'Uellow: Send Cart Recovery Messages', 1, 'hours'),
    ]:
        model_rec = IrModel.search([('model', '=', model_name)], limit=1)
        if not model_rec:
            continue
        if not IrCron.search([('name', '=', name)], limit=1):
            IrCron.create({
                'name': name,
                'model_id': model_rec.id,
                'state': 'code',
                'code': f'model.{method}()',
                'interval_number': interval_number,
                'interval_type': interval_type,
                'active': True,
            })
