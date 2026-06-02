"""Drop obsolete SQL constraints replaced by the variant-aware uniqueness.

v1.1.0 had:
  uniq_product_size       UNIQUE(product_id, size_label)
  uniq_product_attr_value UNIQUE(product_id, attribute_value_id)

v1.2.0 replaces them with a single 3-column constraint that allows variant
overrides on the same (product, attribute_value) pair.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    for cname in ('product_size_chart_uniq_product_size',
                  'product_size_chart_uniq_product_attr_value'):
        cr.execute(
            "ALTER TABLE product_size_chart DROP CONSTRAINT IF EXISTS %s"
            % cname
        )
        _logger.info('dropped old constraint: %s', cname)
