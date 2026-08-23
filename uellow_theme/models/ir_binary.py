# -*- coding: utf-8 -*-
from odoo import models

# Product & category media are PUBLIC content. Marking their Stream public flips
# Cache-Control from `private` to `public`, so Cloudflare (and any shared/edge
# cache) can store them globally. The image URLs already carry a `?unique=<hash>`
# token, so caching is immutable/1-year with correct cache-busting on change.
_UC_PUBLIC_IMAGE_MODELS = frozenset({
    'product.template', 'product.product', 'product.public.category',
    'product.image', 'product.style', 'res.company', 'website',
})


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        stream = super()._record_to_stream(record, field_name)
        try:
            if (record._name in _UC_PUBLIC_IMAGE_MODELS
                    and (field_name or '').startswith('image')):
                stream.public = True
        except Exception:
            # never break image serving
            pass
        return stream
