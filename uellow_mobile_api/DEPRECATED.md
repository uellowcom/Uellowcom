# DEPRECATED — `uellow_mobile_api`

⚠️ **This module is deprecated** as of 2026-05-30.

All endpoints under `/api/v1/...` have been **superseded by v2** in the
`uellow_mobile_manager` module (`/api/mobile/v2/...`).

## Why deprecated

- Pre-dates the unified app-manager backend
- No bilingual response support
- No proper token auth (used `ir.config_parameter` rows as token store)
- Splits "app data" between two modules — content editors couldn't
  manage everything from one place
- Doesn't share the cart/auth/loyalty model with the v2 stack

## Migration map

| Old (`/api/v1`)                  | New (`/api/mobile/v2`)                       |
|----------------------------------|----------------------------------------------|
| `/api/v1/products`               | `/api/mobile/v2/products`                    |
| `/api/v1/products/<id>`          | `/api/mobile/v2/products/<id>`               |
| `/api/v1/products/<id>/variants` | `/api/mobile/v2/products/<id>/variants`      |
| `/api/v1/categories`             | `/api/mobile/v2/categories` (+ `/tree`)      |
| `/api/v1/cart`                   | `/api/mobile/v2/cart` (+ `/add /update /remove /clear /apply-coupon`) |
| `/api/v1/cart/add`               | `/api/mobile/v2/cart/add`                    |
| `/api/v1/cart/remove`            | `/api/mobile/v2/cart/remove`                 |
| `/api/v1/orders`                 | `/api/mobile/v2/orders`                      |
| `/api/v1/orders/<id>`            | `/api/mobile/v2/orders/<id>`                 |
| `/api/v1/orders/create`          | `/api/mobile/v2/orders/checkout/confirm`     |
| `/api/v1/profile`                | `/api/mobile/v2/auth/me` (+ `/profile/update`) |
| `/api/v1/ai/chat`                | `/api/mobile/v2/beena/chat`                  |
| `/api/v1/loyalty`                | `/api/mobile/v2/loyalty`                     |
| `/api/v1/search`                 | `/api/mobile/v2/search`                      |
| `/api/v1/home`                   | `/api/mobile/v2/home`                        |
| `/api/v1/notifications/register` | `/api/mobile/v2/notifications/register-device` |

## What changes for callers

| Concern        | v1                            | v2                                  |
|----------------|-------------------------------|-------------------------------------|
| Auth header    | `X-Mobile-Token: <uid-token>` | `Authorization: Bearer <token>`     |
| Token storage  | `ir.config_parameter`         | `mobile.session` (sha256-hashed)    |
| Response shape | varies per endpoint           | uniform `{success,data,meta,error}` |
| Localization   | English only                  | every text returns `{en,ar}`        |
| Guest cart     | not supported                 | `X-Cart-Token` auto-managed         |

## Sunset plan

- **Phase 1** (now): every legacy response gets a `Deprecation: true`
  header and a `Sunset` header pointing at the removal date.
- **Phase 2** (2026-08-01): legacy endpoints start returning
  `426 Upgrade Required` to anonymous clients lacking a recent
  `X-App-Version` header.
- **Phase 3** (2026-10-01): module uninstalled and removed from the
  addons path.

Until Phase 2, no behaviour changes — old clients keep working.
