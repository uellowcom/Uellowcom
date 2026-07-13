# -*- coding: utf-8 -*-
"""Provider-agnostic dropshipping adapter interface + registry.

Every dropshipping provider (AliExpress, CJ, Spocket, ...) is implemented as a
subclass of :class:`DropshipAdapter`. The core never imports a concrete
provider directly; it resolves one through :func:`get_adapter` using the
``code`` stored on a ``dropship.provider`` record. This keeps the module
provider-agnostic: adding a provider = adding one adapter file + registering it.

A concrete adapter converts each provider's raw JSON into the UNIFIED schema
documented in :meth:`DropshipAdapter.normalize` so the rest of the module never
sees provider-specific shapes.
"""
import logging

_logger = logging.getLogger(__name__)

# code -> adapter class
_REGISTRY = {}


def register(code):
    """Class decorator: register an adapter under a provider ``code``."""
    def _wrap(cls):
        _REGISTRY[code] = cls
        return cls
    return _wrap


def get_adapter(provider):
    """Return an adapter INSTANCE bound to a ``dropship.provider`` record.

    :param provider: a ``dropship.provider`` recordset (single record).
    :raises KeyError: if no adapter is registered for ``provider.code``.
    """
    cls = _REGISTRY.get(provider.code)
    if cls is None:
        raise KeyError("No dropship adapter registered for code %r" % provider.code)
    return cls(provider)


def registered_codes():
    return sorted(_REGISTRY.keys())


class DropshipAdapter(object):
    """Standard interface every provider adapter must implement.

    The unified schema returned by :meth:`normalize` / :meth:`get_product`:

        {
            'source_id':   str,        # provider's product id (unique per provider)
            'title_en':    str,
            'title_ar':    str | None,
            'description_html': str | None,
            'price':       float,      # base cost in provider currency
            'currency':    str,        # ISO code, e.g. 'USD'
            'image_url':   str | None, # main image
            'image_urls':  [str],      # gallery
            'category':    str | None,
            'variants':    [ {'sku': str, 'attrs': {..}, 'price': float, 'stock': int} ],
            'shipping_days': (int, int) | None,   # (min, max)
            'raw':         dict,       # untouched provider payload (for audit)
        }
    """

    #: provider code this adapter serves (set by @register too)
    code = None

    def __init__(self, provider):
        # provider is a dropship.provider record; use it for credentials + env
        self.provider = provider
        self.env = provider.env

    # -- 1. auth ---------------------------------------------------------
    def authenticate(self):
        """Ensure a valid access token (refresh if expired). Return True/raise."""
        raise NotImplementedError

    # -- 2. discovery / feed --------------------------------------------
    def search_feed(self, query=None, category=None, page=1, page_size=20):
        """Return a list of unified product dicts for the storefront listing."""
        raise NotImplementedError

    # -- 3. single product ----------------------------------------------
    def get_product(self, source_id):
        """Return one unified product dict (full detail)."""
        raise NotImplementedError

    # -- 4. shipping / landed cost --------------------------------------
    def get_freight(self, source_id, country_code, quantity=1):
        """Return [{'service': str, 'cost': float, 'currency': str,
                     'days_min': int, 'days_max': int}]."""
        raise NotImplementedError

    # -- 5. order --------------------------------------------------------
    def place_order(self, order_payload):
        """Place a dropship order. Return {'provider_order_id': str, 'status': str}."""
        raise NotImplementedError

    # -- 6. tracking -----------------------------------------------------
    def get_tracking(self, provider_order_id):
        """Return {'carrier': str, 'tracking_no': str, 'status': str,
                    'events': [{'time': str, 'desc': str}]}."""
        raise NotImplementedError

    # -- normalizer (override per provider) -----------------------------
    def normalize(self, raw):
        """Convert one raw provider product payload to the unified schema.

        Default is a pass-through skeleton; concrete adapters override this.
        """
        return {
            'source_id': str(raw.get('id') or raw.get('product_id') or ''),
            'title_en': raw.get('title') or raw.get('subject') or '',
            'title_ar': None,
            'description_html': raw.get('description'),
            'price': float(raw.get('price') or 0.0),
            'currency': raw.get('currency') or 'USD',
            'original_price': float(raw.get('original_price') or 0.0),
            'image_url': raw.get('image'),
            'image_urls': raw.get('images') or [],
            'video_url': raw.get('video') or raw.get('video_url'),
            'category': raw.get('category'),
            'variants': raw.get('variants') or [],
            'shipping_days': None,
            'raw': raw,
        }
