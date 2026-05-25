from . import models

def post_init_hook(env):
    IrCron = env['ir.cron']
    IrModel = env['ir.model']
    model_rec = IrModel.search([('model','=','uellow.kpi.snapshot')], limit=1)
    if model_rec and not IrCron.search([('name','=','Uellow: KPI Snapshot')], limit=1):
        IrCron.create({'name':'Uellow: KPI Snapshot','model_id':model_rec.id,
            'state':'code','code':'model.cron_take_snapshot()',
            'interval_number':1,'interval_type':'hours','active':True})
