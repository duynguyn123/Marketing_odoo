from odoo import models, fields, api
from datetime import timedelta
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)
class AutoCommentSchedule(models.Model):
    _name = 'auto.comment.schedule'
    _description = 'Auto Comment Schedule'

    post_id = fields.Many2one('marketing.post', string='Post ID', required=True, ondelete='cascade')
    end_time = fields.Datetime(string='End Time', required=True)
    remind_time_id = fields.Many2one('custom.remind.time', string='Remind Time')
    reminder_next_time = fields.Datetime(string='Next Reminder Time')
    def action_stop_auto_comment(self):
        self.ensure_one()
        stop_remind_time = self.env['custom.remind.time'].search([('name', '=', 'stop')], limit=1)
        if not stop_remind_time:
            raise ValidationError("Không tìm thấy tùy chọn 'stop' trong custom.remind.time")

        # Cập nhật bảng phụ (auto.comment.schedule)
        self.write({
            'remind_time_id': stop_remind_time.id,
            'reminder_next_time': False
        })

        # Cập nhật bảng chính (marketing.post)
        self.post_id.write({
            'remind_time_id': stop_remind_time.id,
            # 'start_auto_comment': False,
            # 'end_auto_comment': False
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }