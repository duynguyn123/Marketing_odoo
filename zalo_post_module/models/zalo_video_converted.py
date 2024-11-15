import base64
import json
import logging
import requests
from odoo import models, fields,_ , api # type: ignore
import logging
_logger = logging.getLogger(__name__)

class ZaloVideoConvert(models.Model):  
    _name = 'zalo.videoconvert'
    _description = 'Zalo Video Convert'



    zalo_post = fields.Many2one('zalo.post')
    # post_id = fields.Char(related='zalo_post.id', string='Zalo post ID')
    videoToken = fields.Char(related='zalo_post.videoToken', string='Video Token')
    
