import base64
import json
import logging
from urllib.parse import urlencode
import requests
from odoo import models, fields,_ , api # type: ignore
import logging
_logger = logging.getLogger(__name__)

class ZaloVideo(models.Model):  
    _name = 'zalo.video'
    _description = 'Zalo Video'

    zalo_post = fields.Many2one('zalo.post')
    schedule = fields.Datetime(related = 'zalo_post.schedule_date')
    videoToken = fields.Char(related='zalo_post.videoToken')
    status = fields.Char(related='zalo_post.status')
    video_id = fields.Char(related='zalo_post.video_id')
    video_name = fields.Char(related='zalo_post.video_name')

