"""HTTP endpoints for Smart Connector.

Auth & access:
  - All endpoints are restricted to the Smart Connector manager group so an
    arbitrary internal user (e.g. a portal-only or sales rep) cannot mutate
    import jobs they don't own.
  - Mutations check `check_access_rights` before doing anything.
"""
import logging

from odoo import http, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

# XML id of the manager group, defined in security/security.xml.
_MANAGER_GROUP = 'uellow_smart_connector.group_sc_manager'


def _ensure_manager():
    """Raise AccessError unless the current user is a Smart Connector manager."""
    user = request.env.user
    if not user.has_group(_MANAGER_GROUP):
        raise AccessError(_('غير مصرّح. تحتاج صلاحية "مدير Smart Connector".'))


class SmartConnectorController(http.Controller):

    @http.route('/smart-connector/job/status/<int:job_id>',
                type='json', auth='user', methods=['POST'])
    def job_status(self, job_id):
        """Return current job state and stats — used by frontend polling."""
        _ensure_manager()
        job = request.env['uellow.import.job'].browse(job_id)
        if not job.exists():
            return {'error': 'Job not found'}
        # Reading triggers Odoo's ACL/record-rule chain naturally.
        job.check_access_rights('read')
        job.check_access_rule('read')
        return {
            'state':          job.state,
            'total_lines':    job.total_lines,
            'new_count':      job.new_count,
            'update_count':   job.update_count,
            'warning_count':  job.warning_count,
            'approved_count': job.approved_count,
            'error_message':  job.error_message or '',
        }

    @http.route('/smart-connector/line/approve',
                type='json', auth='user', methods=['POST'])
    def approve_line(self, line_id):
        _ensure_manager()
        try:
            line = request.env['uellow.import.job.line'].browse(int(line_id))
        except (TypeError, ValueError):
            return {'error': 'Invalid line_id'}
        if not line.exists():
            return {'error': 'Line not found'}
        line.check_access_rights('write')
        line.check_access_rule('write')
        line.action_approve()
        return {'ok': True}

    @http.route('/smart-connector/line/reject',
                type='json', auth='user', methods=['POST'])
    def reject_line(self, line_id, reason='other', note=''):
        _ensure_manager()
        try:
            line = request.env['uellow.import.job.line'].browse(int(line_id))
        except (TypeError, ValueError):
            return {'error': 'Invalid line_id'}
        if not line.exists():
            return {'error': 'Line not found'}
        line.check_access_rights('write')
        line.check_access_rule('write')
        # Write reason BEFORE action_reject so its constraint passes.
        line.write({'reject_reason': reason, 'reject_note': note or ''})
        try:
            line.action_reject()
        except UserError as ue:
            return {'error': ue.args[0]}
        return {'ok': True}

    @http.route('/smart-connector/settings/test-ai',
                type='json', auth='user', methods=['POST'])
    def test_ai_connection(self):
        """Validate the Anthropic API key WITHOUT spending tokens.

        Previously this called `messages.create` which billed ~$0.003 per
        click and tied up a worker for 1-2s. We now call `models.list()`
        which is free and returns instantly.
        """
        _ensure_manager()
        settings = request.env['uellow.connector.settings'].get_settings()
        api_key = (settings.get('anthropic_api_key') or '').strip()
        if not api_key:
            return {'ok': False, 'message': _('لم يتم ضبط مفتاح API')}
        # Cheap format sanity check before paying for any HTTP.
        if not api_key.startswith('sk-ant-') or len(api_key) < 50:
            return {'ok': False, 'message': _('شكل المفتاح يبدو غير صحيح')}
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=8)
            # Free, fast endpoint — returns immediately if the key is valid.
            client.models.list()
            return {'ok': True, 'message': _('الاتصال يعمل')}
        except ImportError:
            return {'ok': False, 'message': _('مكتبة anthropic غير مثبّتة')}
        except Exception as e:
            return {'ok': False, 'message': str(e)[:200]}
