from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class CustomRemindTime(models.Model):
    _name = 'custom.remind.time'
    _description = 'Custom Remind Time'

    REMIND_OPTIONS = [
        ('stop', 'Stop'),
        ('custom', 'Custom Time'),
    ]

    name = fields.Selection(REMIND_OPTIONS, string='Remind Time', required=True, default='custom')
    days = fields.Integer(string='Days', default=0)
    hours = fields.Integer(string='Hours', default=0)
    minutes = fields.Integer(string='Minutes', default=0)
    display_name = fields.Char(string='Value', compute='_compute_display_name', store=True)

    @api.constrains('days', 'hours', 'minutes')
    def _check_time_values(self):
        for record in self:
            if record.days < 0 or record.hours < 0 or record.minutes < 0:
                raise ValidationError("Time values must be non-negative.")
            if record.name == 'custom' and (record.days == 0 and record.hours == 0 and record.minutes == 0):
                raise ValidationError("At least one time value must be greater than zero when not set to stop.")

    @api.depends('days', 'hours', 'minutes', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.name == 'stop':
                record.display_name = 'Stop'
            else:
                time_parts = []
                if record.days > 0:
                    time_parts.append(f"{record.days} day{'s' if record.days > 1 else ''}")
                if record.hours > 0:
                    time_parts.append(f"{record.hours} hour{'s' if record.hours > 1 else ''}")
                if record.minutes > 0:
                    time_parts.append(f"{record.minutes} minute{'s' if record.minutes > 1 else ''}")
                
                record.display_name = ', '.join(time_parts) if time_parts else '0 minutes'

    def get_total_minutes(self):
        if self.name == 'stop':
            return 0  # Trả về 0 nếu là trạng thái stop
        return self.days * 24 * 60 + self.hours * 60 + self.minutes
    @api.depends('days')
    def _compute_show_days(self):
        for record in self:
            record.show_days = record.days > 0

    @api.depends('hours')
    def _compute_show_hours(self):
        for record in self:
            record.show_hours = record.hours > 0

    @api.depends('minutes')
    def _compute_show_minutes(self):
        for record in self:
            record.show_minutes = record.minutes > 0