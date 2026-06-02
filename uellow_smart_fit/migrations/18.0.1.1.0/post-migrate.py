"""Auto-link existing product.size.chart rows to product.attribute.value.

When the new attribute_value_id column was introduced, all existing rows have it
NULL. This script tries to auto-link each row whose size_label exactly matches
an attribute value already present on its product.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT id, product_id, size_label
        FROM product_size_chart
        WHERE attribute_value_id IS NULL
    """)
    rows = cr.fetchall()
    if not rows:
        return

    linked = 0
    for chart_id, product_id, size_label in rows:
        if not size_label:
            continue
        # Find any attribute_value linked to this product whose name matches
        # pav.name is jsonb {lang: value}. Match against any translation.
        cr.execute("""
            SELECT pav.id
              FROM product_attribute_value pav
              JOIN product_template_attribute_line ptal
                ON ptal.attribute_id = pav.attribute_id
              JOIN product_attribute_value_product_template_attribute_line_rel rel
                ON rel.product_attribute_value_id = pav.id
               AND rel.product_template_attribute_line_id = ptal.id
             WHERE ptal.product_tmpl_id = %s
               AND EXISTS (
                   SELECT 1 FROM jsonb_each_text(pav.name) AS kv
                    WHERE lower(trim(kv.value)) = lower(trim(%s))
               )
             LIMIT 1
        """, (product_id, size_label))
        match = cr.fetchone()
        if match:
            cr.execute(
                "UPDATE product_size_chart SET attribute_value_id = %s WHERE id = %s",
                (match[0], chart_id),
            )
            linked += 1

    _logger.info(
        "Smart-fit migration 18.0.1.1.0: auto-linked %d/%d chart rows to attribute values.",
        linked, len(rows),
    )
