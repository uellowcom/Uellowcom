import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SmartConnectorController(http.Controller):

    @http.route('/smart-connector/job/status/<int:job_id>',
                type='json', auth='user', methods=['POST'])
    def job_status(self, job_id):
        """Return current job state and stats — used by frontend polling."""
        job = request.env['uellow.import.job'].browse(job_id)
        if not job.exists():
            return {'error': 'Job not found'}
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
        line = request.env['uellow.import.job.line'].browse(int(line_id))
        if line.exists():
            line.action_approve()
            return {'ok': True}
        return {'error': 'Line not found'}

    @http.route('/smart-connector/line/reject',
                type='json', auth='user', methods=['POST'])
    def reject_line(self, line_id, reason='other', note=''):
        line = request.env['uellow.import.job.line'].browse(int(line_id))
        if line.exists():
            line.action_reject()
            line.reject_reason = reason
            line.reject_note = note
            return {'ok': True}
        return {'error': 'Line not found'}

    @http.route('/smart-connector/settings/test-ai',
                type='json', auth='user', methods=['POST'])
    def test_ai_connection(self):
        """Test Anthropic API key connectivity."""
        settings = request.env['uellow.connector.settings'].get_settings()
        api_key = settings.get('anthropic_api_key', '')
        if not api_key:
            return {'ok': False, 'message': 'لم يتم ضبط مفتاح API'}
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model='claude-sonnet-4-20250514',
                max_tokens=10,
                messages=[{'role': 'user', 'content': 'ping'}],
            )
            return {'ok': True, 'message': 'الاتصال يعمل'}
        except Exception as e:
            return {'ok': False, 'message': str(e)}
