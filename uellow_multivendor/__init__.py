from . import models
from . import wizard
from . import controllers


def post_init_hook(env):
    """Create default commission plans after install."""
    Plan = env['uellow.commission.plan']
    if not Plan.search([('code', '=', 'BASIC')]):
        Plan.create([
            {'name': 'Basic Plan', 'code': 'BASIC',
             'monthly_fee': 5.0, 'commission_rate': 10.0,
             'currency_id': env.ref('base.KWD').id},
            {'name': 'Professional Plan', 'code': 'PRO',
             'monthly_fee': 15.0, 'commission_rate': 8.0,
             'currency_id': env.ref('base.KWD').id},
            {'name': 'Premium Plan', 'code': 'PREMIUM',
             'monthly_fee': 35.0, 'commission_rate': 6.0,
             'currency_id': env.ref('base.KWD').id},
        ])
