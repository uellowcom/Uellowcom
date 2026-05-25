from . import models

def post_init_hook(env):
    IrCron = env['ir.cron']
    IrModel = env['ir.model']
    model_rec = IrModel.search([('model','=','uellow.demand.forecast')], limit=1)
    if model_rec and not IrCron.search([('name','=','Uellow: Demand Forecasting')], limit=1):
        IrCron.create({'name':'Uellow: Demand Forecasting','model_id':model_rec.id,
            'state':'code','code':'model.cron_run_forecast()',
            'interval_number':7,'interval_type':'days','active':True})
