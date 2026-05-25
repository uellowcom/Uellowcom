from . import models

def post_init_hook(env):
    IrCron = env['ir.cron']
    IrModel = env['ir.model']
    model_rec = IrModel.search([('model','=','uellow.seo.product')], limit=1)
    if model_rec and not IrCron.search([('name','=','Uellow: SEO Auto-generate')], limit=1):
        IrCron.create({'name':'Uellow: SEO Auto-generate','model_id':model_rec.id,
            'state':'code','code':'model.cron_generate_seo()',
            'interval_number':1,'interval_type':'days','active':True})
