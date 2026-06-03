import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

_logger = logging.getLogger(__name__)

# Bunny Stream management API host (separate from the CDN pull-zone host).
_BUNNY_API = 'https://video.bunnycdn.com'


class ProductVideo(models.Model):
    """Add Bunny Stream (or any S3/CDN-style external host) as a video
    backend so admins can keep large MP4s OFF the Odoo server.

    Admin workflow:
      1. Upload to Bunny Stream via Bunny dashboard.
      2. Copy the video GUID (e.g. 1a2b3c4d-...-...).
      3. Set `video_type = bunny_stream`, paste the GUID in
         `bunny_video_id`. Optionally tick `bunny_thumb_auto` to use
         the auto-generated thumbnail.
      4. Save — `bunny_playback_url` and `bunny_thumb_url` compute
         automatically from system parameters."""
    _inherit = 'product.video'

    video_type = fields.Selection(
        selection_add=[('bunny_stream', 'Bunny Stream (external CDN)')],
        ondelete={'bunny_stream': 'set default'},
    )

    bunny_video_id = fields.Char(
        string='Bunny video GUID',
        help='The video GUID from the Bunny Stream dashboard.',
    )
    bunny_playback_url = fields.Char(
        string='Bunny playback URL (HLS)',
        compute='_compute_bunny_urls', store=False,
    )
    bunny_thumb_url = fields.Char(
        string='Bunny thumbnail URL',
        compute='_compute_bunny_urls', store=False,
    )
    bunny_thumb_auto = fields.Boolean(
        string='Use Bunny auto thumbnail',
        default=True,
        help='If on, the Bunny CDN auto-generates a thumbnail and the '
             'mobile app + website use it. If off, the thumbnail field '
             'on this record is used instead.',
    )

    @api.depends('video_type', 'bunny_video_id')
    def _compute_bunny_urls(self):
        ICP = self.env['ir.config_parameter'].sudo()
        pull = (ICP.get_param('uellow_cdn_video.bunny_pull_zone') or '').strip()
        lib  = (ICP.get_param('uellow_cdn_video.bunny_library_id') or '').strip()
        for rec in self:
            if rec.video_type != 'bunny_stream' or not rec.bunny_video_id or not pull:
                rec.bunny_playback_url = ''
                rec.bunny_thumb_url = ''
                continue
            gid = rec.bunny_video_id.strip()
            rec.bunny_playback_url = f'https://{pull}/{gid}/playlist.m3u8'
            rec.bunny_thumb_url = f'https://{pull}/{gid}/thumbnail.jpg'

    def _bunny_config(self):
        """Return (api_key, library_id) or raise if Bunny isn't set up."""
        if requests is None:
            raise UserError(_('The Python "requests" library is missing on the server.'))
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = (ICP.get_param('uellow_cdn_video.bunny_api_key') or '').strip()
        lib = (ICP.get_param('uellow_cdn_video.bunny_library_id') or '').strip()
        if not api_key or not lib:
            raise UserError(_(
                'Bunny Stream is not configured. Open Settings → 🐰 Bunny '
                'Stream and fill the Library ID and API key first.'))
        return api_key, lib

    def _bunny_upload_one(self, api_key, lib):
        """Upload this single record's `video_file` to Bunny: create the video
        object, PUT the bytes, store the GUID, switch to the bunny_stream
        backend and free the local copy. Returns the GUID. Raises on failure
        (caller decides whether to abort or keep going)."""
        self.ensure_one()
        if not self.video_file:
            raise UserError(_('No video file attached.'))
        try:
            payload = base64.b64decode(self.video_file)
        except Exception:
            raise UserError(_('The attached video file could not be read.'))
        title = (self.name
                 or (self.product_tmpl_id.name if self.product_tmpl_id else '')
                 or 'Product video')
        headers = {'AccessKey': api_key, 'accept': 'application/json'}
        # 1) Create the video object → get its GUID.
        try:
            cr = requests.post(
                '%s/library/%s/videos' % (_BUNNY_API, lib),
                headers=dict(headers, **{'content-type': 'application/json'}),
                json={'title': title[:200]},
                timeout=30,
            )
            cr.raise_for_status()
            guid = (cr.json() or {}).get('guid')
        except Exception as e:
            _logger.exception('Bunny: create video failed')
            raise UserError(_('Could not create the video on Bunny Stream: %s') % e)
        if not guid:
            raise UserError(_('Bunny Stream did not return a video GUID.'))
        # 2) Upload the bytes to that GUID.
        try:
            ur = requests.put(
                '%s/library/%s/videos/%s' % (_BUNNY_API, lib, guid),
                headers=dict(headers, **{'content-type': 'application/octet-stream'}),
                data=payload,
                timeout=900,
            )
            ur.raise_for_status()
        except Exception as e:
            _logger.exception('Bunny: file upload failed')
            raise UserError(_(
                'The video object was created (GUID %s) but uploading the file '
                'failed: %s') % (guid, e))
        # 3) Switch to the Bunny backend and free the local copy. Safe: the PUT
        #    succeeded, so the bytes are already on Bunny.
        self.write({
            'video_type': 'bunny_stream',
            'bunny_video_id': guid,
            'video_file': False,
            'video_filename': False,
        })
        return guid

    def action_upload_to_bunny(self):
        """Single-record upload (the button on the product video form)."""
        self.ensure_one()
        api_key, lib = self._bunny_config()
        guid = self._bunny_upload_one(api_key, lib)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Uploaded to Bunny Stream'),
                'message': _(
                    'Video sent to Bunny (GUID %s) and the local copy was '
                    'removed to save server space. It becomes playable once '
                    'Bunny finishes processing — usually a minute or two.') % guid,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_upload_to_bunny_bulk(self):
        """Bulk upload — runs over the selected records (list Action menu).
        Skips records with no local file or already on Bunny. Each success is
        committed immediately so a later failure (or a timeout on a big file)
        never loses already-uploaded videos. Returns a summary notification."""
        api_key, lib = self._bunny_config()
        todo = self.filtered(
            lambda v: v.video_file and not (
                v.video_type == 'bunny_stream' and v.bunny_video_id))
        skipped = len(self) - len(todo)
        done = 0
        failures = []
        for rec in todo:
            try:
                rec._bunny_upload_one(api_key, lib)
                done += 1
                # Persist each success on its own so the batch is resumable
                # and partial progress survives a later error / timeout.
                self.env.cr.commit()
            except Exception as e:
                _logger.exception('Bunny bulk: %s failed', rec.display_name)
                failures.append('%s: %s' % (rec.display_name, e))
        parts = [_('%s uploaded') % done]
        if skipped:
            parts.append(_('%s skipped (no file / already on Bunny)') % skipped)
        if failures:
            parts.append(_('%s failed') % len(failures))
        msg = ' · '.join(parts)
        if failures:
            msg += '\n' + '\n'.join(failures[:5])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bunny bulk upload'),
                'message': msg,
                'type': 'warning' if failures else 'success',
                'sticky': bool(failures),
            },
        }
