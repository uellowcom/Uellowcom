from . import models
from . import wizard
from . import controllers

# NOTE: crons are defined in data/cron_data.xml. The previous post_init_hook
# created the same two crons, producing duplicates on upgrade. Removed.
