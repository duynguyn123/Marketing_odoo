import logging
from odoo import models, fields, api # type: ignore
import logging
_logger = logging.getLogger(__name__)

class ZaloSchedule(models.Model):
    _name = 'zalo.schedule'
    _description = 'Zalo Post Schedule'

    zalo_post = fields.Many2one('zalo.post')
    schedule_date = fields.Datetime(related = 'zalo_post.schedule_date')
    post_status = fields.Char(related='zalo_post.post_status')