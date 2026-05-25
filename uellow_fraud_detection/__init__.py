from . import models


def post_init_hook(env):
    IrCron = env['ir.cron']
    IrModel = env['ir.model']
    IrSeq = env['ir.sequence']

    # Create sequence
    if not IrSeq.search([('code', '=', 'uellow.fraud.case')], limit=1):
        IrSeq.create({
            'name': 'Fraud Case',
            'code': 'uellow.fraud.case',
            'prefix': 'FRD/%(year)s/',
            'padding': 4,
        })

    # Create cron
    model_rec = IrModel.search([('model', '=', 'uellow.fraud.case')], limit=1)
    if model_rec and not IrCron.search([('name', '=', 'Uellow: Fraud Detection Scan')], limit=1):
        IrCron.create({
            'name': 'Uellow: Fraud Detection Scan',
            'model_id': model_rec.id,
            'state': 'code',
            'code': 'model.cron_scan_orders()',
            'interval_number': 1,
            'interval_type': 'days',
            'active': True,
        })
