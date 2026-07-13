# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Backfill preparation_state on already-confirmed orders so the
    Order Preparation queue is populated on install.

    Uses raw SQL (not ORM write) to avoid triggering the many sale.order
    write hooks (notifications / SLA / live-activity) across the whole
    historical order base on a production DB.
    """
    # Confirmed orders not yet handed to delivery -> queue for preparation.
    env.cr.execute("""
        UPDATE sale_order
           SET preparation_state = 'to_prepare'
         WHERE state = 'sale'
           AND (delivery_status = 'pending' OR delivery_status IS NULL)
           AND preparation_state IS NULL
    """)
    # Confirmed orders already in the delivery pipeline -> past preparation.
    env.cr.execute("""
        UPDATE sale_order
           SET preparation_state = 'picked_up'
         WHERE state = 'sale'
           AND delivery_status IS NOT NULL
           AND delivery_status != 'pending'
           AND preparation_state IS NULL
    """)
