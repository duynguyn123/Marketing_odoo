from urllib.parse import urlencode
import requests
from odoo import models, fields, _ # type: ignore
import logging
_logger = logging.getLogger(__name__)
from datetime import timedelta


class ZaloAccount(models.Model):
    _name = 'zalo.app'
    _description = 'Zalo App'
    
    is_favorite = fields.Boolean(string="Favorite", default=False, tracking=True)
    name = fields.Char('Tên tài khoản', required=True)
    app_id = fields.Char('App ID', required=True)
    app_secret = fields.Char('App Secret', required=True)
    access_token = fields.Char('Access Token')
    refresh_token = fields.Char('Refresh Token')
    token_expiration = fields.Datetime('Token Expiration')
    image_app = fields.Binary('Image App')


    zalo_account_id = fields.Many2one('zalo.account')


    # Gọi api lấy token mới
    def get_new_access_token(self):
        url = 'https://oauth.zaloapp.com/v4/oa/access_token'
        session = requests.Session()
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'secret_key': self.app_secret,
        }
        payload = {
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token',
            'app_id': self.app_id,
        }
        urlencoded_data = urlencode(payload)
        _logger.info(f"{urlencoded_data} ")
        response = session.post(url, headers=headers, data=urlencoded_data)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.status_code, "message": response.text}

    # Gán các giá trị mới vào fields
    def action_token_new(self):
        now = fields.Datetime.now()
        response_token = self.get_new_access_token()

        # Update refresh_token
        if 'refresh_token' in response_token:
            self.refresh_token = response_token.get('refresh_token', self.refresh_token)
            self.token_expiration = now
            _logger.info(self.refresh_token)

        # Update access_token
        if 'access_token' in response_token:
            self.access_token = response_token.get('access_token', self.access_token)
            _logger.info(self.access_token)

        return response_token

    def check_token_expiration(self):
        # Kiểm tra nếu token hết hạn
        now = fields.Datetime.now()
        expiration_duration = timedelta(seconds=9000)  # 9000 seconds = 2h30p
        for record in self.search([('token_expiration', '!=', False)]):
            if now - record.token_expiration >= expiration_duration:
                # Log cho biết token hết hạn
                _logger.warning(f"Token for account {record.name} has expired.")
                # Optionally, call action_token_new() to refresh the token automatically
                record.action_token_new()

    
        