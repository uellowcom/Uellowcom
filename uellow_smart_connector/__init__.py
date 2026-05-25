from . import models
from . import wizard
from . import controllers


def post_init_hook(env):
    """Create scheduled actions after module models are registered."""
    IrCron = env['ir.cron']
    IrModel = env['ir.model']

    for model_name, method, name, interval_number, interval_type in [
        ('uellow.price.intelligence', 'cron_check_prices',
         'Smart Connector: فحص أسعار المنافسين', 1, 'days'),
        ('uellow.dead.stock', 'cron_scan_dead_stock',
         'Smart Connector: فحص المخزون الراكد', 7, 'days'),
    ]:
        model_rec = IrModel.search([('model', '=', model_name)], limit=1)
        if not model_rec:
            continue
        existing = IrCron.search([('name', '=', name)], limit=1)
        if not existing:
            IrCron.create({
                'name': name,
                'model_id': model_rec.id,
                'state': 'code',
                'code': f'model.{method}()',
                'interval_number': interval_number,
                'interval_type': interval_type,
                'active': True,
            })
