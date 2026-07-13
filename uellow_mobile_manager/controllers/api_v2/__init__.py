# -*- coding: utf-8 -*-
"""
Uellow Mobile API v2 — clean, versioned, app-only endpoints.

Design principles:
  1. Self-contained: every endpoint reads from data models only,
     never from website templates/views. Editing /shop or website
     hero sliders never breaks the app.
  2. Bilingual by default: every user-facing string returns
     {"en": ..., "ar": ...}. Flutter picks the active locale.
  3. Token auth: bearer tokens issued by /auth/login, stored as
     sha256 in `mobile.session`. Plaintext token never leaves the
     login response.
  4. Same envelope on every response (success/data/meta or
     success/error/code) so the Flutter side has ONE error path.
  5. Backed by the `uellow_mobile_manager` admin module — content
     editors manage sliders / banners / sections / popups there
     and they appear in the app instantly.

Endpoint groups in this package:
  auth           Login / register / OTP / social / logout / me
  profile        Update profile, change password, delete account
  home           Sliders, category icons, feature banners, sections, popups
  products       List / detail / variants / reviews / related / sections
  categories     Tree + per-category products
  cart           Get / add / update / remove / coupons
  orders         List / detail / checkout summary / confirm
  addresses      CRUD on res.partner child addresses
  wishlist       Add / remove / list (auth)
  search         Full-text + popular queries
  reviews        Create / list mine
  loyalty        Points, tier, redeem rate (read from loyalty.card)
  wallet        Balance + transactions
  notifications  List + mark-read + register device token
  beena          Chat passthrough to /ai/chat
  settings      App config + version check + languages + countries + states
"""
from . import _common
from . import auth
from . import profile
from . import home
from . import products
from . import categories
from . import cart
from . import orders
from . import addresses
from . import wishlist
from . import search
from . import reviews
from . import loyalty
from . import beena
from . import notifications
from . import settings
from . import geo
from . import flash_sale
from . import vendors
from . import shipping
from . import account
from . import img
from . import openapi
from . import coupons
from . import fit
from . import helpdesk
from . import mockup
from . import push
from . import videos
from . import well_known
from . import ads
from . import reviewers
from . import promotions
from . import category_slides
from . import announcements
from . import shop_config
from . import admin_app
from . import tracking
from . import newcustomer
from . import bundles
from . import warranty
