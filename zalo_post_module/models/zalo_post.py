import base64
import logging
import requests
from odoo.http import request # type: ignore
from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError, ValidationError # type: ignore
import logging
from datetime import datetime
_logger = logging.getLogger(__name__)

class ZaloPost(models.Model):
    _name = 'zalo.post'
    _description = 'Zalo Post'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Testing inherit

    #Model zalo.app
    zalo_account = fields.Many2one(related='zalo_app_id.zalo_account_id', string = "Zalo Account")
    access_token = fields.Char(related='zalo_app_id.access_token', string='Access Token')
    name = fields.Text(related='content_id.content', string='Title')


    schedule_date = fields.Datetime(string="Scheduled Date", help="Choose the date and time to schedule the post.")
    is_post_to_zalo = fields.Boolean("Post now", default=False)
    cover_url = fields.Char(string='Cover URL',compute="_depend_cover_url")
    is_posted = fields.Boolean(string="Is Post")
    no_video = fields.Boolean('No Video', default=False)
    post_message_respond = fields.Char('Message Respond')
    post_status = fields.Char(string='Post Status')

    #Video 
    video_message_respond = fields.Char('Video Message Respond')
    video_file = fields.Binary('Video File', required=False)  
    video_name = fields.Char('File Name',default="New")
    videoToken = fields.Char('Video Token', default="None")
    video_id = fields.Char('Video ID')
    status = fields.Char('Status')
    video_type = fields.Selection([('cover_only', 'For cover'),
                                ('content_only', 'For content'),
                                ('cover_and_content', 'For cover and content')], string='This video for')


    #Model marketing.content
    image_ids = fields.One2many(related='content_id.image_ids')

    # Kết nối các models lại với nhau
    content_id = fields.Many2one('marketing.content'  , string='Marketing Content')
    zalo_app_id = fields.Many2one('zalo.app', string = "Zalo App")
    account_id = fields.Many2one('zalo.account')

    #Lấy hình ảnh đầu tiên của content
    @api.depends("image_ids")
    def _depend_cover_url(self):
        for record in self:
            if record.image_ids:  # Kiểm tra xem danh sách không rỗng
                if record.image_ids[0].id:  # Kiểm tra ID đã được xác định
                    # Lấy URL server hiện tại
                    base_url = request.httprequest.host_url
                    # Tạo cover_url với URL tự động
                    record.cover_url = f"{base_url}web/image?model=marketing.content.image&id={record.image_ids[0].id}&field=image"
                else:
                    record.cover_url = ""  # Rỗng nếu ID không hợp lệ

    #inherit hàm tạo
    def create(self, vals):
        now = datetime.now()
        record = super(ZaloPost, self).create(vals)

        # Nếu có video thì setup cho video đó
        if not record.no_video and not self.env["zalo.video"].search([("zalo_post", "=", record.id)]):
            self.env["zalo.video"].create({
                "zalo_post": record.id,
                  "schedule": now
                  })
            record.prepare_video_upload()
            record.verify_video_upload()
            
            # Tạo record cho các video đang được convert
            if not self.env["zalo.videoconvert"].search([("zalo_post", "=", record.id)]):
                self.env["zalo.videoconvert"].create({
                    "zalo_post": record.id,
                    "videoToken": record.videoToken
                    })

        # Đặt status cho post
        record.post_status = "Ready" if record.no_video else "Waiting"

        # Nếu dùng post now
        if record.is_post_to_zalo and not record.is_posted:
            try:
                record.write({'schedule_date': now})

                # Tạo record trong zalo schedule
                if not self.env["zalo.schedule"].search([("zalo_post", "=", record.id)]):
                    self.env["zalo.schedule"].create({
                        "zalo_post": record.id
                        })

                response = record.action_post_feed()

                # Xóa record sau khi thành công
                schedule_record = self.env["zalo.schedule"].search([
                    ("zalo_post", "=", record.id),
                    ("post_status", "=", "Ready")])
                
                if schedule_record:
                    schedule_record.unlink()

            except Exception as e:
                _logger.error(f"Error posting to Zalo: {e}")

        return record

    #inherit hàm chỉnh sửa
    def write(self, vals):
        now = datetime.now()
        for record in self:
            
            #Set schedule cho bài post nếu vẫn chưa có
            if vals.get('is_post_to_zalo') and not record.is_posted and not record.schedule_date:
                try:
                    vals['schedule_date'] = now

                    # Tạo schedule record của post nếu chưa có
                    if not self.env["zalo.schedule"].search([("zalo_post", "=", record.id)]):
                        self.env["zalo.schedule"].create({
                            "zalo_post": record.id
                            })

                    response = record.action_post_feed()

                    #Xóa schedule record nếu đã upload thành công
                    schedule_record = self.env["zalo.schedule"].search([("zalo_post", "=", record.id)])
                    if schedule_record:
                        schedule_record.unlink()

                except Exception as e:
                    _logger.error(f"Error posting to Zalo: {e}")
        return super(ZaloPost, self).write(vals)


    @api.model
    def post_feed(self):
        
        try:
            # URL for the API endpoint
            url = "https://openapi.zalo.me/v2.0/article/create"
            _logger.info(f"access_token - {self.zalo_app_id.access_token}")
            
            # Headers including the access token
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "access_token": self.zalo_app_id.access_token
            }

            # Prepare the body based on the user's selection of content type
            body_content = [
                {
                    "type": "text",
                    "content": self.content_id.content
                },
                {
                    "type": "image",
                    "url": self.cover_url
                }]
            

            # Based Payload containing app_id, app_secret, message, and link
            payload = {
                "app_id": self.zalo_app_id.app_id,
                "app_secret": self.zalo_app_id.app_secret,
                "type": "normal",
                "title": self.content_id.content,
                "author": "News",
                "cover": {
                    "cover_type": "photo",
                    "photo_url": self.cover_url,
                    "status": "show"
                },
                "description": self.content_id.content,
                "body": body_content,
                "status": "show",
                "comment": "show"
            }

            #Nếu người dùng chọn video cho cover
            if self.video_type == 'cover_only':
                payload = {
                    "app_id": self.zalo_app_id.app_id,
                    "app_secret": self.zalo_app_id.app_secret,
                    "type": "normal",
                    "title": self.content_id.content,
                    "author": "News",
                    "cover": {
                        "cover_type": "video",
                        "cover_view": "horizontal",
                        "video_id": self.video_id,
                        "status": "show"
                    },
                    "description": self.content_id.content,
                    "body": body_content,
                    "status": "show",
                    "comment": "show"
                }

            #Nếu người dùng chọn video cho content
            elif self.video_type == 'content_only':
                body_content = [
                {
                    "type": "video",
                    "video_id": self.video_id,
                },
                {
                    "type": "text",
                    "content": self.content_id.content
                },
                {
                    "type": "image",
                    "url": self.cover_url
                }]

            #Nếu người dùng chọn video cho cả 2
            elif self.video_type == 'cover_and_content':
                body_content = [
                {
                    "type": "video",
                    "video_id": self.video_id,
                },
                {
                    "type": "text",
                    "content": self.content_id.content
                },
                {
                    "type": "image",
                    "url": self.cover_url
                }]

                payload = {
                    "app_id": self.zalo_app_id.app_id,
                    "app_secret": self.zalo_app_id.app_secret,
                    "type": "normal",
                    "title": self.content_id.content,
                    "author": "News",
                    "cover": {
                        "cover_type": "video",
                        "cover_view": "horizontal",
                        "video_id": self.video_id,
                        "status": "show"
                    },
                    "description": self.content_id.content,
                    "body": body_content,
                    "status": "show",
                    "comment": "show"
                }

            # Send POST request with headers and JSON payload
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            if 'message' in response_data:
                self.post_message_respond = response_data['message']
                _logger.info(self.post_message_respond)
            
            # Check if the request was successful
            if response.status_code == 200 and response_data.get('error') == 0:
                self.is_posted = True
                return response.json()  # Return the JSON response
            else:
                
                #Trường hợp lỗi
                response.raise_for_status()  # Raise an exception for any errors
                self.post_status = "Error"
                
                raise UserError(_(f"Failed to post: {response_data.get('message', 'Unknown error')}"))

        except Exception as e:
            _logger.error(f"Error posting to Zalo: {e}")
                
    def action_post_feed(self):
        response_feed = self.post_feed()
        if 'message' in response_feed:
            self.post_message_respond = response_feed['message']
            _logger.info(self.post_message_respond)

        if response_feed.get('error') != 0:
            self.post_status = 'Error'
            raise UserError(f"Đăng bài không thành công! Lỗi: {self.post_message_respond}")
        else:

            self.post_status = 'Success'
            self.is_posted = True  # Đánh dấu đã đăng thành công

        return response_feed

    
    @api.model
    def schedule_post_feed(self):

        # Fetch records where the scheduled date has passed and the post has not been made
        now = datetime.now()
        records = self.env["zalo.schedule"].search([
            ('schedule_date', '<=', now),
            ('post_status', '=', 'Ready')
        ])
        
        for record in records:
            zalo_post = record.zalo_post
            try:
                zalo_post.action_post_feed()  # Call the post feed action
                zalo_post.is_posted = True  # Mark as posted
                _logger.info(f"Successfully posted feed for record {zalo_post.id}")
                
                # Delete the schedule record after successful posting
                record.unlink()
                _logger.info(f"Deleted schedule record {record.id}")

            except Exception as e:

                # Log the error and raise a popup to notify the user
                _logger.error(f"Failed to post feed for record {zalo_post.id}: {e}")
                raise UserError(_(f"Failed to post feed for record {zalo_post.id}: {e}"))
    

    def prepare_video_upload(self):
        # URL của API
        url = 'https://openapi.zalo.me/v2.0/article/upload_video/preparevideo'
        # Thực hiện POST request
        file = base64.b64decode(self.video_file)
        response = requests.post(
            url,
            headers={
                'access_token': self.access_token,
            },
            files={
                'file': (self.video_name,file, 'video/mp4')
            }
        )
        _logger.info( f"zalo app access = {self.access_token}")
        response_data = response.json()

        # Kiểm tra kết quả trả về
        if response.status_code == 200 and response_data.get('error') == 0:
            
            #Lấy ra message respond
            self.video_message_respond = response_data.get('message')

            # Nếu thành công thì lấy ra video token
            if 'data' in response_data and 'token' in response_data['data']:
                self.videoToken = response_data['data']['token']
        else:
            #Thất bại thì hiển thị lỗi và status của post là error
            self.status = "Error"
            self.video_message_respond = response_data.get('message')
            _logger.info('Error:', response.status_code, response.text)
    

    def verify_video_upload(self):
         
        _logger.info(f"Verifying video upload for record {self.id}, access_token: {self.access_token}")


        if not self.access_token or not isinstance(self.access_token, str):
            raise UserError("Access token is missing or invalid. Please ensure it is set correctly.")

        url = "https://openapi.zalo.me/v2.0/article/upload_video/verify"
        
        # Prepare the payload
        headers = {
            'access_token': self.access_token,
            'token': self.videoToken
        }
        
        # Make the GET request
        try:
            response = requests.get(url, headers=headers)
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(f"An error occurred while making the request: {e}")

        # Check for success
        if response.status_code == 200 and response_data.get('error') == 0:
            # If successful, retrieve status and video_id
            self.video_id = response_data['data']['video_id']
            self.status = "Being converted"
            _logger.info('Video is being converted')
        else:
            # Handle failure
            return {
                'error': response.status_code,
                'message': response.text
            }

        return response_data



    def action_verify_video(self):
        
        verify = self.verify_video_upload()

        #Lấy ra thông tin message
        if 'message' in verify:
            self.video_message_respond = verify['message']
            _logger.info(self.video_message_respond)

        #Nếu thành công thì lấy ra video_id và status
        if verify['error'] == 0:
            self.video_id = verify['data']['video_id']
            videoStatus = verify['data']['status']

            #Nếu là 3 thì video đang upload chưa xong
            if videoStatus == 3:
                self.status = "Being converted"
                _logger.info('Video is being converted')
                
            #Nếu là 1 thì upload thành công, đổi status thành ready
            elif videoStatus == 1:
                self.status = "Ready"
                self.post_status = "Ready"
                _logger.info('Video is ready')
        
        # Trường hợp nếu không thành công
        else:

            self.video_message_respond = verify['message']
            self.status = "Error"
            raise UserError(f"Lỗi: {self.video_message_respond}")
            
        return verify
    


    def schedule_video(self):
        records = self.env["zalo.videoconvert"].search([])
        for record in records:
            zalo_post = record.zalo_post
            
            # Check if the zalo_post is valid
            if not zalo_post:
                _logger.error(f"Record {record.id} in zalo.videoconvert does not have a valid related zalo_post.")
                continue  # Skip this record
            
            try:
                # Check if the access_token is valid
                if not zalo_post.access_token or not isinstance(zalo_post.access_token, str):
                    _logger.error(f"Record {zalo_post.id} has an invalid or missing access_token")
                    continue  # Skip this record
                
                _logger.info(f"Starting video verification for record {zalo_post.id} with access_token: {zalo_post.access_token}")


                zalo_post.action_verify_video()
                
                # Optionally remove the processed record
                if record.status == "Ready":
                    record.unlink()
            except Exception as e:
                _logger.error(f"Failed for record {zalo_post.id}: {str(e)}")


