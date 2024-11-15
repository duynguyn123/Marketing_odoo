
import json
import logging
from odoo import models, fields, api
import requests
import base64
from datetime import datetime, timedelta
import time

_logger = logging.getLogger(__name__)

class ManagerAccount(models.Model):
    _name = 'manager.account'
    _description = 'Load account facebook information'

    ################THUỘC TÍNH######################
    is_favorite = fields.Boolean(string="Favorite", default=False, tracking=True)
    account_name = fields.Char('User Name', readonly=True)
    account_id = fields.Char(string='Account ID' )
    access_token = fields.Text('Access Token')
    account_avatar = fields.Binary('Avatar')
    page_ids = fields.One2many('facebook.page', 'account_id', string="Pages")
    display_name = fields.Char(compute='_compute_display_name')
    cliend_id = fields.Char('Client ID', required=True)
    id_secret = fields.Char('Client Secret', required=True)
    last_token_refresh = fields.Datetime('Last Token Refresh')
    auth_status = fields.Selection([
        ('not_authenticated', 'Not Authenticated'),
        ('authenticated', 'Authenticated')
    ], string='Authentication Status', default='not_authenticated', readonly=True)
   #####################PHƯƠNG THỨC################################
    @api.depends('account_name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.account_name
    #Load dữ liệu        
    # def load_data(self):
    #     for record in self:
    #         record.load_account_info()
    #         record.load_account_ava()
    #         record.load_pages()
    #     return True
    # Tự động Refesh token
    def _cron_refresh_tokens(self):
        # Tìm kiếm tài khoản
        accounts = self.search([])
        for account in accounts:
            # Lặp vòng lặp kiểm tra gọi hàm update và load data
            if account.update_access_token():
                account.load_data()
    def update_access_token(self, max_retries=3, retry_delay=5):
     now = fields.Datetime.now()
     if not self.last_token_refresh or (now - self.last_token_refresh) > timedelta(minutes=1):
        url = "https://graph.facebook.com/v20.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.cliend_id,
            "client_secret": self.id_secret,
            "fb_exchange_token": self.access_token
        }
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                if 'access_token' in data:
                    self.access_token = data['access_token']
                    self.last_token_refresh = now
                    _logger.info(f"Token truy cập đã được cập nhật cho tài khoản {self.account_name}")
                    return True
                else:
                    _logger.warning(f"Phản hồi không mong đợi cho tài khoản {self.account_name}: {data}")
            except requests.exceptions.RequestException as e:
                error_message = str(e)
                if response.status_code == 400:
                    error_details = response.json().get('error', {})
                    error_message = f"Lỗi {error_details.get('code')}: {error_details.get('message')}"
                
                _logger.error(f"Lỗi cập nhật token truy cập cho tài khoản {self.account_name}: {error_message}")
                
                if attempt < max_retries - 1:
                    _logger.info(f"Thử lại sau {retry_delay} giây...")
                    time.sleep(retry_delay)
                else:
                    _logger.error(f"Không thể cập nhật token sau {max_retries} lần thử")
                    # Thông báo cho admin hoặc người dùng về lỗi liên tục
                    self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'title': 'Lỗi Làm Mới Token',
                        'message': f"Không thể làm mới token cho {self.account_name}. Vui lòng kiểm tra thông tin đăng nhập và quyền của ứng dụng.",
                        'type': 'danger',
                    })
                    return False
     return True
    #Load thông tin account
    def load_account_info(self):
        url_info_request = f'https://graph.facebook.com/v20.0/{self.account_id}?access_token={self.access_token}'  
        try:
            # Lấy dữ liệu callback trả về
            info_response = requests.get(url_info_request)
            # Chuyển đổi sang json
            info_data = info_response.json()
            # Gán tên tài khoản bằng tên trả về từ API
            self.account_name = info_data['name']
        # In ra lỗi nếu gọi API không thành công
        except requests.exceptions.RequestException as e:
            print(f"Đã xảy ra lỗi khi gọi API Get account info: {e}")
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'title': 'Lỗi',
                'message': f"Đã xảy ra lỗi khi gọi API: {e}",
                'type': 'danger',
            })
        return None
    #Load avatar
    def load_account_ava(self):
        url_avatar_request = f'https://graph.facebook.com/v20.0/{self.account_id}/picture?type=large&access_token={self.access_token}'
        try:
            avatar_response = requests.get(url_avatar_request)

            #set fields
            self.account_avatar = base64.b64encode(avatar_response.content).decode('utf-8')

        except requests.exceptions.RequestException as e:
            print(f"Đã xảy ra lỗi khi gọi API Get Avatar: {e}")
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'title': 'Lỗi',
                'message': f"Đã xảy ra lỗi khi gọi API: {e}",
                'type': 'danger',
            })
        return None
    #Load pages
    def load_pages(self):
        url_pages_request = f'https://graph.facebook.com/v20.0/{self.account_id}/accounts?access_token={self.access_token}'
        try:
            pages_response = requests.get(url_pages_request)
            # Lấy dữ liệu trả về và chuyển đổi sang json
            page_data = pages_response.json()

            if page_data and 'data' in page_data:
                for page in page_data['data']:
                    # Tạo hoặc cập nhật Facebook Page
                    facebook_page = self.env['facebook.page'].search([('page_id', '=', page['id'])], limit=1)
                    if not facebook_page:
                         # Nếu không tìm thấy, tạo mới Facebook Page
                        facebook_page = self.env['facebook.page'].create({
                            'account_id': self.id,
                            'page_name': page['name'],
                            'page_id': page['id'],
                            'page_avatar': self.get_pages_ava(page['id']),
                            'access_token': page['access_token'],
                            'category': page['category']
                        })
                    else:
                        # Nếu tìm thấy, cập nhật thông tin Facebook Page
                        facebook_page.write({
                            'page_name': page['name'],
                            'page_avatar': self.get_pages_ava(page['id']),
                            'access_token': page['access_token'],
                            'category': page['category']
                        })

                    # Xử lý các category
                    category_ids = []
                    if 'category_list' in page:
                        for category in page['category_list']:
                            fb_category = self.env['facebook.category'].search([('fb_category_id', '=', category['id'])], limit=1)
                            if fb_category:
                                category_ids.append(fb_category.id)
                            else:
                                # Nếu category không tồn tại, bạn có thể quyết định tạo mới hoặc bỏ qua
                                new_category = self.env['facebook.category'].create({
                                    'fb_category_name': category['name'],
                                    'fb_category_id': category['id'],
                                })
                                category_ids.append(new_category.id)
                        
                    # Cập nhật các category cho Facebook Page
                    facebook_page.write({
                        'category_ids': [(6, 0, category_ids)]
                    })

        except requests.exceptions.RequestException as e:
             # Bắt ngoại lệ nếu có lỗi xảy ra trong quá trình gửi yêu cầu
            print(f"Đã xảy ra lỗi khi gọi API Get Page: {e}")
             # Gửi thông báo lỗi đến người dùn
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'title': 'Lỗi',
                'message': f"Đã xảy ra lỗi khi gọi API: {e}",
                'type': 'danger',
            })
        return None
    #Load avatar page
    def get_pages_ava(self, page_id):
        url_page_ava_request = f'https://graph.facebook.com/v20.0/{page_id}/picture?type=large&access_token={self.access_token}'
        try:
            avatar_page_response = requests.get(url_page_ava_request)
            return base64.b64encode(avatar_page_response.content)
            # logging.info(base64.b64encode(avatar_page_response.content))
            # return base64.b64encode(avatar_page_response.content)

        except requests.exceptions.RequestException as e:
            print(f"Đã xảy ra lỗi khi gọi API Get Avatar Page: {e}")
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'title': 'Lỗi',
                'message': f"Đã xảy ra lỗi khi gọi API: {e}",
                'type': 'danger',
            })
            return None   
    #Thêm vào yêu thích
    def toggle_favorite(self):
        for record in self:
            record.is_favorite = not record.is_favorite
    def authenticate_facebook(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        callback_url = f"{base_url}/facebook_auth_callback"
        
        auth_url = f"https://www.facebook.com/v20.0/dialog/oauth?client_id={self.cliend_id}&redirect_uri={callback_url}&scope=pages_show_list,pages_read_engagement,pages_manage_posts"
        
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'new',
        }

    def facebook_auth_callback(self, code):
        self.ensure_one()
        _logger.info("Processing Facebook auth callback")
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        callback_url = f"{base_url}/facebook_auth_callback"
        
        token_url = "https://graph.facebook.com/v20.0/oauth/access_token"
        params = {
            "client_id": self.cliend_id,
            "client_secret": self.id_secret,
            "redirect_uri": callback_url,
            "code": code
        }
        
        try:
            response = requests.get(token_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'access_token' in data:
                self.write({
                    'access_token': data['access_token'],
                    'auth_status': 'authenticated'
                })
                self._fetch_account_info()
                self.with_context(force_reload=True).load_data()
                self.env.cr.commit()
                _logger.info("Facebook authentication successful and data loaded")
                
                # 
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'refresh_facebook_data', {
                    'message': 'Facebook data updated',
                    'account_id': self.id
                })
            else:
                _logger.error("No access token in Facebook response: %s", data)
                raise ValueError("No access token received from Facebook")
        except requests.exceptions.RequestException as e:
            _logger.error("Error during Facebook token exchange: %s", str(e))
            raise ValueError("Error communicating with Facebook")
        except json.JSONDecodeError as e:
            _logger.error("Error decoding Facebook response: %s", str(e))
            raise ValueError("Invalid response from Facebook")
        except Exception as e:
            _logger.error("Unexpected error during Facebook authentication: %s", str(e))
            raise

    def load_data(self):
        self.ensure_one()
        _logger.info("Starting to load data for account: %s", self.account_name)
        
        try:
            self.load_account_info()
            self.load_account_ava()
            self.load_pages()
            
            self.env.cr.commit() 
            _logger.info("Data loaded successfully for account: %s", self.account_name)
            return True
        except Exception as e:
            _logger.error("Error loading data for account %s: %s", self.account_name, str(e))
            self.env.cr.rollback()  
            return False

    @api.model
    def refresh_data(self, ids):
        records = self.browse(ids)
        for record in records:
            record.with_context(force_reload=True).load_data()
        return True

    def _fetch_account_info(self):
        _logger.info("Fetching Facebook account info")
        url = f"https://graph.facebook.com/v20.0/me?fields=id,name&access_token={self.access_token}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            self.write({
                'account_id': data.get('id'),
                'account_name': data.get('name')
            })
            _logger.info("Account info fetched successfully. Data: %s", data)
            _logger.info("Account info fetched successfully. Account ID: %s", self.account_id)
            _logger.info("Account info fetched successfully. Account Name: %s", self.account_name)
        except Exception as e:
            _logger.error("Error fetching account info: %s", str(e))
            raise ValueError("Could not fetch account information from Facebook")
