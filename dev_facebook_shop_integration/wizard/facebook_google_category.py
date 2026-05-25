# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

import logging
import mimetypes
import requests
import csv
from io import StringIO

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FacebookGoogleCategory(models.TransientModel):
    _name = "facebook.google.category"
    _description = "Facebook / Google Category Importer"
    _rec_name = "platform"

    url = fields.Char(
        string="URL",
        required=True,
        help="Plain‑text taxonomy in *.txt format",
    )
    platform = fields.Selection(
        [('google', 'Google'), ('facebook', 'Facebook')],
        string="Platform",
        required=True,
    )
    rewrite_if_exists = fields.Boolean(
        string="Rewrite Names",
        help="Overwrite existing category names if they are already present.",
    )

    @api.onchange("platform")
    def _onchange_platform_set_url(self):
        self.url = (
            "https://www.google.com/basepages/producttype/taxonomy-with-ids.en-US.txt"
            if self.platform == "google"
            else "https://www.facebook.com/products/categories/en_US.txt"
            if self.platform == "facebook"
            else ""
        )

    def _download_txt(self, url, timeout=30):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise UserError(_("Error opening URL: %s") % err)
        return resp.text

    def action_update(self):
        self.ensure_one()

        # 1) Validate mime type
        mimetype, encoding = mimetypes.guess_type(self.url)
        if mimetype != "text/plain":
            raise UserError(_("Only plain‑text (*.txt) files are allowed."))

        # 2) Download file
        content = self._download_txt(self.url)

        if self.platform == "google":
            return self._import_google_categories(content)
        elif self.platform == "facebook":
            return self._import_facebook_categories(content)
        else:
            raise UserError(_("Unknown platform selected."))

    def _import_google_categories(self, content):
        Category = self.env["custom.google.category"]
        index = 1

        for line in content.splitlines():
            if not line or line.startswith("#"):
                continue

            try:
                code, category = line.split(" - ", 1)
            except ValueError:
                _logger.warning("Skipping malformed taxonomy row: %s", line)
                continue

            hierarchy = category.split(" > ")
            vals = {
                "name": hierarchy[-1],
                "code": code,
                "sequence": index,
            }

            if len(hierarchy) > 1:
                parent = Category.search([("name", "=", hierarchy[-2])], limit=1)
                vals["parent_id"] = parent.id if parent else False

            existing = Category.search([("code", "=", code)], limit=1)
            if existing:
                if self.rewrite_if_exists:
                    existing.write(vals)
            else:
                Category.create(vals)

            index += 1

        return {
            "name": _("Google Categories"),
            "type": "ir.actions.act_window",
            "res_model": "custom.google.category",
            "view_mode": "list,form",
            "target": "current",
        }

    def _import_facebook_categories(self, content):
        Category = self.env["custom.facebook.category"]

        # Parse CSV from text
        reader = csv.reader(StringIO(content))
        header_skipped = False
        for row in reader:
            if not header_skipped:
                header_skipped = True
                continue
            if not row or len(row) < 2:
                continue

            code, name = row[0], row[1]
            vals = {
                "code": code,
                "name": name,
            }

            existing = Category.search([("code", "=", code)], limit=1)
            if existing:
                if self.rewrite_if_exists:
                    existing.write(vals)
            else:
                Category.create(vals)

        return {
            "name": _("Facebook Categories"),
            "type": "ir.actions.act_window",
            "res_model": "custom.facebook.category",
            "view_mode": "list,form",
            "target": "current",
        }
