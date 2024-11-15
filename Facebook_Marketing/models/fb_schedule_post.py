from odoo import models, fields, api
from datetime import datetime, timedelta
class ScheduledPost(models.Model):
    _name = 'scheduled.post'
    _description = 'Scheduled Post'

    post_id = fields.Many2one('marketing.post', string='ID Post', required=True, ondelete='cascade')
    schedule_post = fields.Datetime(string='Scheduled Time', required=True)
