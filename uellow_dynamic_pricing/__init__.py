from . import models

def post_init_hook(env):
    IrCron = env['ir.cron']
    IrModel = env['ir.model']
    model_rec = IrModel.search([('model','=','uellow.dynamic.pricing.rule')], limit=1)
    if model_rec and not IrCron.search([('name','=','Uellow: Dynamic Pricing Update')], limit=1):
        IrCron.create({'name':'Uellow: Dynamic Pricing Update','model_id':model_rec.id,
            'state':'code','code':'model.cron_apply_pricing()',
            'interval_number':30,'interval_type':'minutes','active':True})
