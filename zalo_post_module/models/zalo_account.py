import requests
from odoo import models, fields, _, api # type: ignore
import logging
_logger = logging.getLogger(__name__)
from datetime import timedelta


class ZaloAccount(models.Model):
    _name = 'zalo.account'
    _description = 'Zalo Offical Account'

    is_favorite = fields.Boolean(string="Favorite", default=False, tracking=True)
    name = fields.Char('Tên tài khoản')
    account_id = fields.Char('App ID')
    description = fields.Char('Description')
    cate_name = fields.Char('Danh mục')
    num_follower = fields.Char('Follower')
    avatar_url = fields.Char('Account Image')
    package_name = fields.Char('Package Name')


    zalo_app = fields.Many2one('zalo.app')
    access_token = fields.Char(related='zalo_app.access_token', string = 'Access Token')



    def take_image_account_url(self):
        url = "https://openapi.zalo.me/v2.0/oa/getoa"
        
        # Prepare the payload
        headers = {
            'access_token':self.access_token,
        }
        
        # Make the POST request
        response = requests.get(url, headers=headers)
        print(response)
        
        # Check for success
        if response.status_code == 200:
            return response.json()  # Return the JSON response
        else:
            return {
                'error': response.status_code,
                'message': response.text
            }
        
    def action_take_url_image(self):
        info = self.take_image_account_url()
        self.account_id = info['data']['oa_id']
        self.name = info['data']['name']
        self.description = info['data']['description']
        self.cate_name = info['data']['cate_name']
        self.avatar_url = info['data']['avatar']
        self.num_follower = info['data']['num_follower']
        self.package_name = info['data']['package_name']
        if self.zalo_app:
            zalo_app = self.env["zalo.app"].write({
                "name": self.name,
            })
        return info
    
















