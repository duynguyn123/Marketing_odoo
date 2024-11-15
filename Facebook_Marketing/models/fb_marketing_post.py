import requests
import json
from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import base64
import logging
import random
import traceback
from odoo.addons.http_routing.models.ir_http import slug
from odoo.http import request

_logger = logging.getLogger(__name__)

class FacebookPost(models.Model):
    _name = 'marketing.post'
    _description = 'Facebook Post'

    # Định nghĩa các trường (fields) cho model
    content_id = fields.Many2one('marketing.content', string='Content', default=lambda self: self._get_latest_content())  
    # Liên kết đến 'marketing.content', mặc định là nội dung mới nhất

    account_id = fields.Many2one('manager.account', string='Account', required=True)  
    # Liên kết đến 'manager.account', là trường bắt buộc

    page_id = fields.Many2one('facebook.page', string='Page', domain="[('account_id', '=', account_id)]")  
    # Liên kết đến 'facebook.page', chỉ hiện trang thuộc tài khoản đã chọn

    post_now = fields.Boolean(string='Post Now')  # Tùy chọn đăng ngay lập tức
    schedule_post = fields.Datetime(string='Đặt lịch post bài')  # Thời gian lên lịch đăng bài
    comment = fields.Text(string='Comment')  # Nội dung bình luận cho bài viết
    comment_suggestion_id = fields.Many2many('marketing.comment', string='Comment Suggestion')  
    comment_suggestions_text = fields.Text(compute='_compute_comment_suggestions', string='Comment Suggestions')
    last_auto_comment_time = fields.Datetime('Last Auto Comment Time')  # Thời gian bình luận tự động cuối cùng
    start_auto_comment = fields.Datetime(string='Start Auto Comment')  # Thời gian bắt đầu tự động bình luận
    end_auto_comment = fields.Datetime(string='End Auto Comment')  # Thời gian kết thúc tự động bình luận
    last_comment_index = fields.Integer('Chỉ số comment cuối cùng', default=-1)  # Chỉ số bình luận cuối cùng được chọn
    post_id = fields.Char('Post ID')  # ID bài viết trên Facebook
    post_url = fields.Char('Post URL')  # URL của bài viết trên Facebook
    state = fields.Selection([('draft', 'Draft'), ('scheduled', 'Scheduled'), 
                              ('posted', 'Posted'), ('failed', 'Failed')], 
                             string='Status', default='draft')  
    # Trạng thái của bài đăng (draft, scheduled, posted, failed)
     
    auto_reply_enabled = fields.Boolean(string='Enable Auto Reply', default=False)  
    # Tùy chọn để kích hoạt tính năng tự động trả lời bình luận

    auto_reply_message = fields.Text(string='Auto Reply Message', default='Thank you for your comment!')  
    # Nội dung trả lời tự động

    last_comment_id = fields.Char(string='Last Processed Comment ID')  # ID của bình luận cuối cùng đã được xử lý
    # Thời gian đăng bài 
    remind_time_id = fields.Many2one('custom.remind.time', string='Remind Time')
    
    def action_show_full_columns(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Marketing Posts',
            'res_model': 'marketing.post',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.ids)],
            'context': {'show_full_columns': True},  # Chuyển context khi nhấn nút
        }
    # Thay đổi hiển thị lấy hết nội dung của comment_suggestion
    @api.depends('comment_suggestion_id')
    def _compute_comment_suggestions(self):
        for record in self:
            record.comment_suggestions_text = ', '.join(record.comment_suggestion_id.mapped('name')[:2])  # Lấy 2 bình luận
    # Lịch post comment
    def _post_scheduled(self):
        current_time = fields.Datetime.now()
        _logger.info(f"Kiểm tra các bài viết đã được lên lịch vào lúc {current_time}")
        # Tất cả bài viết được lưu trong bản ghi phụ
        all_scheduled_posts = self.env['scheduled.post'].search([])
        _logger.info(f"Tất cả các bài viết đã được lên lịch: {all_scheduled_posts}")
        # Tìm kiếm bản ghi được lên lịch từ SchedulePost
        scheduled_posts = self.env['scheduled.post'].search([('schedule_post', '<=', current_time)])
        _logger.info(f"Danh sách bài viết được lên lịch để xử lý: {scheduled_posts}")
        _logger.info(f"Tìm thấy {len(scheduled_posts)} bài viết đã được lên lịch để xử lý")
        # Lập điều kiện kiểm tra bài post nếu không có trong bảng
        if not scheduled_posts:
            _logger.warning("Không tìm thấy bài viết nào được lên lịch. Kiểm tra lại điều kiện tìm kiếm.")
            all_scheduled = self.env['scheduled.post'].search([])
            _logger.info(f"Tổng số bài viết trong bảng scheduled.post: {len(all_scheduled)}")
            if all_scheduled:
                _logger.info(f"Bài viết gần nhất: ID={all_scheduled[0].id}, Thời gian={all_scheduled[0].schedule_post}")
        # Lấy thông tin chi tiết bài viết từ bảng chính
        post_ids = [sp.post_id.id for sp in scheduled_posts]
        posts = self.browse(post_ids)
        # Lập tìm bài post và đăng
        for post in posts:
            _logger.info(f"Đang cố gắng đăng bài viết với ID {post.id}")
            post.post_to_facebook()
            # Nếu state đã được cập nhật thành posted thì log đăng thành công
            if post.state == 'posted':
                _logger.info(f"Đăng bài viết thành công với ID {post.id}")
                 # Xóa bản ghi khỏi cơ sở dữ liệu khi đăng thành công
                scheduled_posts.unlink()
            else:
                _logger.error(f"Đăng bài viết thất bại với ID {post.id}")
       
    @api.model
    def _get_latest_content(self):
        """ Lấy nội dung mới nhất đã được tạo trong hệ thống """
        return self.env['marketing.content'].search([], order='create_date desc', limit=1).id

    @api.onchange('content_id')
    def _onchange_content_id(self):
        """ Cập nhật bình luận khi nội dung được thay đổi """
        if self.content_id:
            self.comment = self.content_id.content  # Cập nhật nội dung bình luận bằng nội dung bài viết đã chọn

    @api.model
    def create(self, vals):
        """ Ghi đè phương thức tạo để tự động chọn nội dung mới nhất nếu không được cung cấp """
        if 'content_id' not in vals:
            vals['content_id'] = self._get_latest_content()  # Lấy nội dung mới nhất nếu không có giá trị content_id
        return super(MarketingPost, self).create(vals)  # Gọi phương thức tạo từ class cha để hoàn tất
    # Hàm thay đổi _update_auto_comment_schedule
    @api.onchange('remind_time_id')
    def _onchange_remind_time(self):
        for record in self:
            if record.remind_time_id.name == 'stop':
                # Xóa bản ghi nếu remind_time là 'stop'
                schedules = self.env['auto.comment.schedule'].search([('post_id', '=', record.id)])
                if schedules:
                    schedules.unlink()
                    _logger.info(f"Đã xóa bản ghi lịch tự động bình luận cho bài đăng có ID {record.id}")
                else:
                    _logger.info(f"Không tìm thấy bản ghi nào để xóa trong auto.comment.schedule cho bài đăng có ID {record.id}")
    @api.model
    def run_auto_comment_cron(self):
        """ Chạy cron job tự động bình luận """
        _logger.info("Chạy cron job auto-comment")
        self._auto_comment()  # Gọi hàm tự động bình luận
    # Hàm thay đổi trạng thái post now
    @api.onchange('post_now')
    def _onchange_post_now(self):
        """ Nếu tùy chọn 'post_now' được chọn, bỏ qua lịch đăng """
        if self.post_now:
            self.schedule_post = False  # Nếu đăng ngay lập tức, bỏ lịch
        else:
            self.schedule_post = fields.Datetime.now()  # Nếu không, lên lịch đăng bài ngay lúc này
    # Hàm thay đổi account_id
    @api.onchange('account_id')
    def _onchange_account_id(self):
        """ Cập nhật danh sách các trang thuộc tài khoản đã chọn """
        self.page_id = False  # Xóa trang đã chọn trước đó
        return {'domain': {'page_id': [('account_id', '=', self.account_id.id)]}}  # Chỉ hiện trang thuộc tài khoản đã chọn
    # Hàm thay đổi comment gợi ý
    @api.onchange('comment_suggestion_id')
    def _onchange_comment_suggestion_id(self):
        """ Cập nhật bình luận dựa trên các gợi ý bình luận đã chọn """
        if self.comment_suggestion_id:
            self.comment = '\n'.join(comment.name for comment in self.comment_suggestion_id)  # Gộp các gợi ý bình luận thành một chuỗi
        else:
            self.comment = ''  # Nếu không chọn gợi ý nào, để trống bình luận
    # Hàm thay đổi thời gian post
    @api.onchange('schedule_post')
    def _onchange_schedule_post(self):
        """ Cập nhật thời gian và trạng thái khi đặt lịch đăng bài """
        for record in self:
            if record.schedule_post:
                record.state = 'scheduled'  # Đặt trạng thái thành 'scheduled'
                record.start_auto_comment = record.schedule_post  # Thiết lập thời gian bắt đầu tự động bình luận
                record.end_auto_comment = record.start_auto_comment + timedelta(weeks=1)  # Tự động bình luận trong 1 tuần
                _logger.info(f"Đặt lịch post bài với ID {record.id} vào lúc {record.schedule_post}")
    # Hàm post comment tiếp theo trong danh sách người dùng chọn commnent
    def post_next_comment_to_facebook(self):
        """ Đăng bình luận tiếp theo dựa trên các gợi ý bình luận """
        if not self.comment_suggestion_id:
            _logger.warning(f"Không tìm thấy gợi ý bình luận cho bài đăng có ID {self.id}")
            return  # Nếu không có gợi ý, dừng lại

        comment_suggestions = self.comment_suggestion_id.mapped('name')  # Lấy danh sách các gợi ý bình luận
        if not comment_suggestions:
            _logger.warning(f"Danh sách gợi ý bình luận trống cho bài đăng có ID {self.id}")
            return  # Nếu không có gợi ý hợp lệ, dừng lại

        # Tăng chỉ số bình luận và quay vòng lại nếu đã hết
        self.last_comment_index = (self.last_comment_index + 1) % len(comment_suggestions)
        comment_content = comment_suggestions[self.last_comment_index]  # Lấy bình luận tiếp theo

        if not comment_content or comment_content.lower() == 'false':
            _logger.warning(f"Bình luận không hợp lệ cho bài đăng có ID {self.id}: {comment_content}")
            return  # Nếu bình luận không hợp lệ, dừng lại

        self.post_comment_to_facebook(comment_content)  # Gửi bình luận lên Facebook
        _logger.info(f"Đã đăng bình luận tiếp theo cho bài đăng có ID {self.id}: {comment_content}")
    # Chọn content mới nhất được lưu
    @api.model
    def _get_latest_content(self):
        return self.env['marketing.content'].search([], order='create_date desc', limit=1)
    #Post facebook
    def post_to_facebook(self):
        content = self.content_id.content or "Không lấy được content"
        logging.info("-----------------------------------------------------------------")
        logging.info("%s \n\n\n\n", self.content_id)
        #Lấy hình ảnh từ MarketingContent
        images = self.content_id.image_ids
        
        try:
            # Tạo biến lưu access_token và page_id
            access_token = self.page_id.access_token
            page_id = self.page_id.page_id

            # Tải lên từng ảnh riêng lẻ
            media_ids = []
            # Lập qua từng ảnh trong danh sách images
            for idx, attachment in enumerate(images):
                _logger.info(f"Available fields for attachment: {attachment._fields.keys()}")
                _logger.info(f"Attachment data: {attachment.read()}")
                
                image_data = attachment.image or attachment.datas
                # Kiểm tra ảnh có dữ liệu hay không
                if not image_data:
                    _logger.warning(f"Ảnh {idx} không có dữ liệu, bỏ qua.")
                    continue
                # Chuyển hình ảnh thành base64 để xử lí
                image_data = base64.b64decode(image_data)
                files = {f'file{idx}': (f'image{idx}.jpg', image_data, 'image/jpeg')}
                photo_data = {
                    'access_token': access_token,
                    'published': False  # Không đăng ảnh ngay lập tức
                }
                # Tạo request đăng ảnh lên page
                photo_response = requests.post(
                    f'https://graph.facebook.com/{page_id}/photos',
                    data=photo_data,
                    files=files
                )
                # Gửi request để tải ảnh lên Facebook và lưu lại ID của ảnh.
                photo_response.raise_for_status()
                # Danh sách các ảnh đã tải lên
                media_ids.append({'media_fbid': photo_response.json()['id']})
            # Kiểm tra và thêm URL vào nội dung nếu include_link được bật
            if self.content_id.include_link and self.content_id.url:
             content += f"\n\n{self.content_id.url}"   
            # Tạo bài đăng với tất cả ảnh đã tải lên
            data = {
                'message': content,
                'access_token': access_token,
                'attached_media': json.dumps(media_ids),
            }
            #Log kiểm tra quá trình đăng ảnh
            _logger.info(f"Đăng bài với pageID {page_id}")
            _logger.info(f"Dữ liệu trước khi gửi {data}")
            _logger.info(f"Tổng số ảnh đã đăng: {len(media_ids)}")
            # Gửi request đăng bài lên facebook
            response = requests.post(
                f'https://graph.facebook.com/{page_id}/feed',
                data=data
            )

            _logger.info(f"Status Code: {response.status_code}")
            _logger.info(f"Nội dung trả về: {response.content}")

            response.raise_for_status()
            post_data = response.json()
            # Lưu ID bài viết vừa đăng
            self.post_id = post_data.get('id')
            # Tạo URL của bài đăng
            self.post_url = f"https://www.facebook.com/{self.post_id.replace('_', '/posts/')}"
            # Kiểm tra nếu có gắn link vào bình luận
            if not self.content_id.include_link and self.content_id.url:
                try:
                    # Gửi yêu cầu post 
                    comment_response = requests.post(
                        f'https://graph.facebook.com/{self.post_id}/comments',
                        data={
                            'message': self.content_id.url,
                            'access_token': access_token
                        }
                    )
                    # Gửi request để thêm bình luận với URL sản phẩm vào bài đăng.
                    comment_response.raise_for_status()
                    _logger.info(f"Thêm bình luận thành công với URL sản phẩm vào bài viết")
                except requests.exceptions.RequestException as e:
                    _logger.error(f"Thêm bình luận URL thất bại : {e}")
                    _logger.error(f"Comment response content: {e.response.content if e.response else 'No response content'}")
            # self.state: Cập nhật trạng thái bài đăng thành 'posted'.
            # self.start_auto_comment: Lưu thời gian bắt đầu tự động bình luận.
            # self.end_auto_comment: Lưu thời gian kết thúc tự động bình luận (sau 1 tuần).
            self.state = 'posted'
            # self.start_auto_comment = datetime.now()
            # self.end_auto_comment = self.start_auto_comment + timedelta(weeks=1)
            # Kiểm tra nếu không có remind_time_id và comment_suggestion
            if not self.remind_time_id or not self.comment_suggestion_id:
             _logger.warning(f"Bài đăng có ID {self.id} không có remind_time_id hoặc comment_suggestion.")
             return
            self._update_auto_comment_schedule()
        # Xử lí ngoại lệ
        except requests.exceptions.RequestException as e:
            # Nếu state= false
            self.state = 'failed'
            _logger.error(f"Đăng lên trang '{page_id}' thất bại: {e}")
            _logger.error(f"Response content: {e.response.content if e.response else 'No response content'}")
            _logger.debug(f"Nội dung phản hồi: {e.response.content if e.response else 'Không có nội dung phản hồi'}")
        except Exception as e:
         self.state = 'failed'
         error_message = f"Lỗi không xác định khi đăng bài: {e}"
         _logger.error(error_message)
         _logger.error(f"Traceback: {traceback.format_exc()}")
         raise UserError(error_message)
        _logger.info("Kết thúc quá trình đăng bài lên Facebook")
        # Thành công trả về true
        return True
    #Post comment
    def post_comment_to_facebook(self, comment_content=None):
     # Kiểm tra điều kiệu comment
     if comment_content is None:
        comment_content = self.comment or "Bình luận mặc định"
    # Nếu không có comment hợp lệ in ra log thông báo lỗi
     if not comment_content or comment_content.lower() == 'false':
        _logger.warning(f"Nội dung bình luận không hợp lệ cho bài đăng có ID {self.post_id}: {comment_content}")
        return
     # API post comment lên bài viết
     page_url = f'https://graph.facebook.com/{self.post_id}/comments'
     try:
        response = requests.post(
            page_url,
            data={
                'message': comment_content,
                'access_token': self.page_id.access_token
            }
        )
        # Gửi yêu cầu request lên bài viết
        response.raise_for_status()
        _logger.info(f"Đã đăng bình luận thành công cho bài viết '{self.post_id}' trên trang '{self.page_id.page_id}': {comment_content}")
     # Xử lí exception
     except requests.exceptions.RequestException as e:
        _logger.error(f"Không thể đăng bình luận cho bài viết '{self.post_id}' trên trang '{self.page_id.page_id}': {e}")
        _logger.error(f"Nội dung phản hồi: {e.response.content if e.response else 'Không có nội dung phản hồi'}")
    # Xóa bản ghi
    def _remove_auto_comment_schedule(self, schedule):
        _logger.info(f"Xóa lịch tự động bình luận cho bài đăng có ID {schedule.post_id.id}")
        schedule.unlink()
    # Lịch tự động comment
    def _auto_comment(self):
           current_time = fields.Datetime.now()
           _logger.info(f"Đang chạy kiểm tra tự động bình luận lúc {current_time}")
           #Tìm kiếm lịch các comment được lên lịch
           active_schedules = self.env['auto.comment.schedule'].search([
            ('reminder_next_time', '<', current_time),
           ])
           # Kiểm tra nếu bài viết được lên lịch đã được post và có post_id
           for schedule in active_schedules:
            post = schedule.post_id
            if post.state != 'posted' or not post.post_id:
                continue
            post.post_next_comment_to_facebook()
            # Tính toán reminder_next_time
            if schedule.remind_time_id:
                # Lấy tổng số phút
                total_minutes = schedule.remind_time_id.get_total_minutes()
                new_reminder_time = current_time + timedelta(minutes=total_minutes)
                _logger.info(f"Dữ liệu end_time mới: {schedule.end_time}")
                _logger.info(f"Dữ liệu reminder_next_time mới: {new_reminder_time}")
            else:
                new_reminder_time = current_time + timedelta(minutes=int(schedule.remind_time))
            # So sánh nếu new_reminder_time > schedule.end_time thì xóa bản ghi đó
            if new_reminder_time > schedule.end_time:
                # self._remove_auto_comment_schedule(schedule)
                _logger.info(f"Đang xóa bình luận tự động cho bài đăng có ID {post.id} vì đã hết thời gian")
            else:
                _logger.info(f"Đang đăng bình luận tự động cho bài đăng có ID {post.id}")
                # Thỏa điều kiện đăng comment tiếp theo lên facebook
                post.post_next_comment_to_facebook()
                # Ghi reminder_next_time mới vào bản ghi
                schedule.write({
                    'reminder_next_time': new_reminder_time,
                })
                _logger.info(f"reminder_next_time được cập nhật vào auto.comment.schedule: {new_reminder_time}")
                # try:
                #    action = self.env.ref('facebook_marketing.action_auto_comment_schedule')
                #    _logger.info("Hành động được tìm thấy: %s", action)
                #    return {
                #        'type': 'ir.actions.act_window',
                #        'name': action.name,
                #        'res_model': action.res_model,
                #        'view_mode': action.view_mode,
                #        'target': 'current',
                #        'context': {'reload': True},
                #          }
                # except ValueError:
                #    _logger.error("Không tìm thấy hành động!")
            _logger.info(f"Đã cập nhật thời gian nhắc nhở tiếp theo cho bài đăng có ID {post.id}")
    #Post comment ngẫu nhiên       
    def post_random_comment_to_facebook(self):
     if not self.comment_suggestion_id:
        _logger.warning(f"Không tìm thấy gợi ý bình luận cho bài đăng có ID {self.id}")
        return

     comment_suggestions = self.comment_suggestion_id.mapped('name')
     if not comment_suggestions:
        _logger.warning(f"Danh sách gợi ý bình luận trống cho bài đăng có ID {self.id}")
        return

     comment_content = random.choice(comment_suggestions)
     if not comment_content or comment_content.lower() == 'false':
        _logger.warning(f"Bình luận ngẫu nhiên được chọn không hợp lệ cho bài đăng có ID {self.id}: {comment_content}")
        return

     self.post_comment_to_facebook(comment_content)
     _logger.info(f"Đã đăng bình luận ngẫu nhiên cho bài đăng có ID {self.id}: {comment_content}")
    # Cập nhật commnent tự động cho bản ghi auto.comment.schedule
    def _update_auto_comment_schedule(self):
          # Tìm kiến bản ghi auto.comment.schedule liên kết với bài viết
          schedule = self.env['auto.comment.schedule'].search([('post_id', '=', self.id)], limit=1)
          # Tính toán reminder_next_time
          reminder_next_time = self._calculate_reminder_next_time()
          _logger.info(f"reminder_next_time: {reminder_next_time}")
          _logger.info(f"start_auto_comment: {self.start_auto_comment}")
          current_time = datetime.now()
           # Kiểm tra nếu reminder_next_time nhỏ hơn start_auto_comment hoặc hiện tại chưa tới start_auto_comment
          if isinstance(reminder_next_time, datetime) and isinstance(self.start_auto_comment, datetime):
           if reminder_next_time < self.start_auto_comment or current_time < self.start_auto_comment:
        # Thực hiện hành động cần thiết
            reminder_next_time = self.start_auto_comment
            _logger.info(f"reminder_next_time được cập nhật bằng với start_auto_comment: {reminder_next_time}")

          # Điều kiên: Nếu không có reminder_next_time thì in ra log và trả về
          if not reminder_next_time:
            _logger.warning(f"Không thể tính toán thời gian nhắc nhở tiếp theo cho bài đăng có ID {self.id}")
            return
          # Dữ liệu truyền vào bản ghi auto.comment.schedule
          vals = {
            'post_id': self.id,
            'end_time': self.end_auto_comment,
            'remind_time_id': self.remind_time_id.id,
            'reminder_next_time': reminder_next_time,
                }
        # Nếu bản ghi tồn tại thì cập nhật dữ liệu, ngược lại tạo mới
          if schedule:
            schedule.sudo().write(vals)
          else:
            schedule = self.env['auto.comment.schedule'].sudo().create(vals)

    # Hàm tính toán thời gian nhắc nhở tiếp theo
    def _calculate_reminder_next_time(self):
         # Điều kiện: reminder_time_id không được rỗng và reminder_time_id.name khác 'stop'
         if not self.remind_time_id or self.remind_time_id.name == 'stop':
            return False
         # Tính toán thời gian nhắc nhở tiếp theo
         base_time = self.last_auto_comment_time or self.start_auto_comment
         if base_time:
            # Tính tổng số phút từ remind_time_id
            total_minutes = self.remind_time_id.get_total_minutes()
             # Trả về thời gian tính toán được
            return base_time + timedelta(minutes=total_minutes)
         return False
    # Hàm tạo bài viết và comment
    @api.model
    def create(self, vals):
    #  Tạo một bản ghi mới cho MarketingPost. Dựa trên các giá trị trong `vals`, hàm này sẽ:
    #     #  - Đăng bài viết lên Facebook và cập nhật trạng thái thành 'posted' nếu `post_now` được chọn.
    #     #  - Lên lịch bài viết và cập nhật trạng thái thành 'scheduled' nếu `schedule_post` được chọn.
    #     #  - Lưu thông tin bài viết và thời gian lên lịch vào bảng `scheduled.post` nếu `schedule_post` được chọn.
     record = super(FacebookPost, self).create(vals)
    # Kiểm tra nếu người dùng chọn comment để đăng tự động 
    # Gọi hàm để kiểm tra và cập nhật lịch bình luận tự động
     _logger.info("Đang kiểm tra xem comment có hợp lệ không")
     self._check_and_update_auto_comment_schedule(
        record,
        record.start_auto_comment,
        record.end_auto_comment,
        record.remind_time_id
    )
     _logger.info("Commment hợp lệ thực hiện các thao tác tiếp theo")
     # Nếu chọn là post_now, đăng bài và cập nhật trạng thái
     # Gọi hàm _handle_post_now để thực hiện hành động post_now
     if vals.get('post_now'):
        _logger.info("Người dùng chọn post_now thực hiện đăng bài ngay")
        self._handle_post_now(record)
        _logger.info("Hoàn thành việc đăng bài với post_now")
     # Nếu chọn lên lịch post
     # Gọi hàm _handle_schedule_post để thực hiện hành động lên lịch post
     elif vals.get('schedule_post'):
        _logger.info("Người dùng chọn schedule vui lòng đợi lịch đăng bài")
        self._handle_schedule_post(record, vals['schedule_post'])
     return record
    # Hàm ghi bài viết và comment
    def write(self, vals):
     _logger.info("Cập nhật với dữ liệu %s", vals)
     res = super(FacebookPost, self).write(vals)
     for post in self:
        start_time_schedule = post.start_auto_comment
        # Kiểm tra và chuyển đổi end_time_schedule
        end_time_schedule = vals.get('end_auto_comment', post.end_auto_comment)
        if isinstance(end_time_schedule, str):
            end_time_schedule = fields.Datetime.from_string(end_time_schedule)
        reminder_time_id = post.remind_time_id

        if vals.get('post_now'):
            self._handle_post_now(post)
        elif vals.get('schedule_post'):
            self._handle_schedule_post(post, vals['schedule_post'])
        else:
            _logger.info("Không thể Đăng ngay và lên lịch với bài viết: %s", post.id)

        # Cập nhật hoặc tạo mới bản ghi auto.comment.schedule nếu các giá trị liên quan được cung cấp
        if any(field in vals for field in ['start_auto_comment', 'end_auto_comment', 'remind_time_id']):
            # Gọi hàm kiểm tra và cập nhật bản ghi auto.comment.schedule
            self._check_and_update_auto_comment_schedule(post, start_time_schedule, end_time_schedule, reminder_time_id)

     return res
    # Hàm thực hiện post now
    def _handle_post_now(self, post):
     # Nếu người dùng post now sẽ gọi hàm post_to_facebook() và post bài
     post.post_to_facebook()
     # Cập nhật state thành posted
     post.state = 'posted'
     _logger.info("Đăng ngay đã được chọn. Cập nhật state với 'posted' bởi record ID: %s", post.id)
     # Xóa lịch nếu không tồn tại
     self.env['scheduled.post'].search([('post_id', '=', post.id)]).unlink()
    # Hàm thực hiện lên lịch post
    def _handle_schedule_post(self, post, schedule_post):
     # Cập nhật state thành scheduled
     post.state = 'scheduled'
     # Tạo bản ghi lịch post vào auto.comment.schedule
     scheduled_post = self.env['scheduled.post'].create({
        'post_id': post.id,
        'schedule_post': schedule_post
     })
     _logger.info("Lịch đăng đã được tạo với ID: %s for MarketingPost ID: %s", scheduled_post.id, post.id)
    # Hàm kiểm tra và cập nhật bản ghi auto.comment.schedule
    def _check_and_update_auto_comment_schedule(self, post, start_time_schedule, end_time_schedule, reminder_time_id):
     _logger.info("Kiểm tra điều kiện ghi")
     # Nếu remind_time_id.name là 'stop' thì xóa bản ghi auto.comment.schedule
     if post.remind_time_id and post.remind_time_id.name == 'stop':
        _logger.info("Dữ liệu reminder_time_id.name: %s", post.remind_time_id.name)
        # Tìm các bản ghi `auto.comment.schedule` liên kết với bài viết
        auto_comment_schedule_records = self.env['auto.comment.schedule'].search([('post_id', '=', post.id)])
        # Xóa các bản ghi auto.comment.schedule tương ứng
        if auto_comment_schedule_records:
            auto_comment_schedule_records.unlink()
            _logger.info("Bản ghi auto.comment.schedule đã được xóa với Post ID: %s", post.id)

    # Nếu có dữ liệu start_time_schedule và reminder_time_id
     if start_time_schedule and reminder_time_id:
        # Tính toán số phút
        total_minutes = reminder_time_id.get_total_minutes()
        # Nếu end_time_schedule không hợp lệ in ra log và trả về
        if start_time_schedule + timedelta(minutes=total_minutes) > end_time_schedule:
            raise UserError("Thời gian kết thúc phải lớn hơn thời gian bắt đầu cộng với thời gian nhắc nhở. Vui lòng nhập lại.")
        else:
            # Cập nhật và ghi bản ghi vào auto.comment.schedule
            self._update_auto_comment_schedule()
    # Hàm lấy và trả lời comment
    def fetch_and_reply_to_comments(self):
        #Kiểm tra xem có nhấn vào nút reply không
     if not self.auto_reply_enabled or not self.post_id:
        return
 
     access_token = self.page_id.access_token
     url = f"https://graph.facebook.com/v20.0/{self.post_id}/comments"
     # Thông số truyền vào
     params = {
        'access_token': access_token,
        'fields': 'id,message,created_time',
        'limit': 100,  # Adjust as needed
        'order': 'reverse_chronological'
     }

     if self.last_comment_id:
        params['since'] = self.last_comment_id

     _logger.info(f"Fetching comments with URL: {url}")
     _logger.info(f"Parameters: {params}")

     try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        comments = response.json().get('data', [])

        for comment in reversed(comments):
            comment_id = comment['id']
            if comment_id == self.last_comment_id:
                continue

            self.reply_to_comment(comment_id, self.auto_reply_message)
            self.last_comment_id = comment_id

     except requests.exceptions.RequestException as e:
        _logger.error(f"Error fetching comments: {e}")
        _logger.error(f"Response content: {e.response.content if e.response else 'No response content'}")
    # Hàm trả lời comment
    def reply_to_comment(self, comment_id, reply_message):
        access_token = self.page_id.access_token
        url = f"https://graph.facebook.com/v20.0/{comment_id}/comments"
        
        data = {
            'message': reply_message,
            'access_token': access_token
        }

        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            _logger.info(f"Successfully replied to comment {comment_id}")
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error replying to comment {comment_id}: {e}")
    #Lịch tự động trả lời bài viết
    @api.model
    def run_auto_reply_cron(self):
        posts = self.search([('auto_reply_enabled', '=', True), ('state', '=', 'posted')])
        for post in posts:
            post.fetch_and_reply_to_comments()    