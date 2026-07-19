# DEPRECATED — `mobile_api`

⚠️ **This module is deprecated** as of 2026-05-30.

The FastAPI-based mobile API was an earlier experiment. It has been
superseded by the cleaner, integrated v2 API in `uellow_mobile_manager`
(`/api/mobile/v2/...`).

## Why deprecated

- Splits the app's data/control between TWO Odoo modules
  (this one + `uellow_mobile_manager` for slider/banners/popups
  editing). Content editors had no single place to manage everything.
- FastAPI router stack adds a separate dependency tree (`fastapi`,
  `pydantic`, `endpoint_route_handler`) that's heavier than needed
  for what is essentially CRUD over Odoo ORM.
- Custom JWT implementation conflicts with the simpler bearer-token
  + `mobile.session` pattern used by v2.
- Schemas duplicate Odoo's existing models — schema drift bugs
  appeared whenever a field was added on the website side.

## Migration

All endpoints have equivalents in v2 under `/api/mobile/v2/...`.
See `uellow_mobile_api/DEPRECATED.md` for the full endpoint map (the
two old modules cover overlapping surface).

## Sunset plan

- **Phase 1** (now): module remains installable but marked deprecated.
- **Phase 2** (2026-08-01): module flagged for removal in next release.
- **Phase 3** (2026-10-01): module uninstalled.

To prevent accidental rebuild against this module, the `__manifest__.py`
has been updated to mark it `deprecated: True` and `auto_install: False`.
