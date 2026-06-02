from . import models
from . import wizard
from . import controllers

# NOTE: post_init_hook was removed. Cron is now defined in
# data/ir_cron_data.xml which is the standard Odoo way.
