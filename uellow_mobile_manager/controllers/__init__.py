# -*- coding: utf-8 -*-
from . import mobile_api  # legacy v1 (kept for backward compat, will be removed once Flutter migrates)
# NOTE (payment fix): `main` was a STALE DUPLICATE of uellow_checkout's website
# checkout controller. Because uellow_mobile_manager DEPENDS ON uellow_checkout,
# its controller loaded LAST and silently OVERRODE every /shop/* and
# /uellow/checkout/* route — so all the maintained fixes in uellow_checkout
# (gateway redirect, payment-method scoping, ship-guard, no auto-confirm on
# failure) never took effect, and online payments fell into this copy's
# auto-confirm-and-redirect-to-success fallback (customer never reached the
# gateway). Disabled so uellow_checkout (the canonical, fixed module) owns the
# storefront checkout. The app uses the api_v2 endpoints, not these routes.
# from . import main       # checkout / cart / states / payment overrides
from . import api_v2       # new clean v2 API
from . import app_preview  # interactive mockup at /uellow-app-preview/
from . import api_v2_preview_screens  # screen renderers used by app_preview
from . import app_download  # APK download at /download/uellow-app
from . import cart_share_public  # /cart/share/<token> share-cart landing
from . import vendor_promotions
from . import website_selective_checkout  # /shop/cart/checkout-selected (selective checkout)
from . import website_tracking  # /website/track — website visitor journey
