from . import models

def post_init_hook(env):
    IrCron = env['ir.cron']
    IrModel = env['ir.model']
    model_rec = IrModel.search([('model','=','uellow.customer.ltv')], limit=1)
    if model_rec and not IrCron.search([('name','=','Uellow: Compute LTV')], limit=1):
        IrCron.create({'name':'Uellow: Compute LTV','model_id':model_rec.id,
            'state':'code','code':'model.cron_compute_all()',
            'interval_number':1,'interval_type':'days','active':True})
