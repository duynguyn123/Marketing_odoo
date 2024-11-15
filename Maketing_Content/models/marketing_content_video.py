from odoo import models, fields, api
import base64
import io
import requests
import json

class MarketingContentVideo(models.Model):
    _name = 'marketing.content.video'
    _description = 'Marketing Content Video'

    name = fields.Char(string='Video Name', required=True)
    content_id = fields.Many2one('marketing.content', string='Marketing Content', required=True, ondelete='cascade')
    video_filename = fields.Char(string='Filename')
    video = fields.Binary(string='Video File', attachment=True)
    video_url = fields.Char(string='Video URL', readonly=True)

    @api.model
    def create(self, vals):
        if not vals.get('video_filename') and vals.get('name'):
            vals['video_filename'] = f"{vals['name']}.mp4"
        record = super(MarketingContentVideo, self).create(vals)
        if vals.get('video'):
            record.upload_video_to_gdrive()
        return record

    def upload_video_to_gdrive(self):
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        SERVICE_ACCOUNT_FILE = 'D:\Company\VsCode\Phase2\odoo-config\addons\maketing_content\ggdiriveforadd-283fcb48f431.json'

        # Load credentials from the service account file
        with open(SERVICE_ACCOUNT_FILE) as f:
            credentials = json.load(f)

        # Get access token
        auth_url = 'https://oauth2.googleapis.com/token'
        auth_data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': self._create_jwt(credentials)
        }
        auth_response = requests.post(auth_url, data=auth_data)
        auth_response_data = auth_response.json()
        access_token = auth_response_data['access_token']

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        for record in self:
            if record.video:
                video_data = base64.b64decode(record.video)
                video_io = io.BytesIO(video_data)

                # Upload video
                metadata = {
                    'name': record.video_filename,
                    'mimeType': 'video/mp4'
                }
                files = {
                    'data': ('metadata', io.BytesIO(json.dumps(metadata).encode('utf-8')), 'application/json'),
                    'file': ('video.mp4', video_io, 'video/mp4')
                }
                response = requests.post(
                    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
                    headers=headers,
                    files=files
                )
                response_data = response.json()

                # Thay đổi quyền truy cập của file thành công khai
                permission = {
                    'type': 'anyone',
                    'role': 'reader',
                }
                requests.post(
                    f'https://www.googleapis.com/drive/v3/files/{response_data["id"]}/permissions',
                    headers=headers,
                    json=permission
                )

                record.video_url = f"https://drive.google.com/file/d/{response_data['id']}/view"

    def _create_jwt(self, credentials):
        import jwt
        import time

        now = int(time.time())
        payload = {
            'iss': credentials['client_email'],
            'sub': credentials['client_email'],
            'aud': 'https://oauth2.googleapis.com/token',
            'iat': now,
            'exp': now + 3600,
            'scope': 'https://www.googleapis.com/auth/drive.file'
        }
        additional_headers = {
            'kid': credentials['private_key_id']
        }
        signed_jwt = jwt.encode(payload, credentials['private_key'], headers=additional_headers, algorithm='RS256')
        return signed_jwt