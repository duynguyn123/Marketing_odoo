from odoo import models, fields, api
import requests

class FacebookGroup(models.Model):
    _name = 'facebook.group'
    _description = 'Facebook Group'

    account_id = fields.Many2one('res.users', string='Account', default=lambda self: self.env.user)
    group_avatar = fields.Binary('Avatar')
    group_name = fields.Char(string="Name", required=True)
    group_id = fields.Char(string="Group ID", required=True)
    access_token = fields.Char(string="Access Token")
    category = fields.Char(string="Main Category")
    category_ids = fields.Many2many('facebook.category', string='Categories',
                                    relation='facebook_group_category_rel',
                                    column1='group_id', column2='category_id')

    is_favorite = fields.Boolean(string="Favorite", default=False, tracking=True)
    display_name = fields.Char(compute='_compute_display_name')

    post_content = fields.Text(string="Post Content")
    comment_content = fields.Text(string="Comment Content")

    group_description = fields.Text(string="Group Description")
    member_count = fields.Integer(string="Member Count")
    is_public = fields.Boolean(string="Is Public Group", default=True)
    # Ham tinh toan display_name
    @api.depends('group_name')
    def _compute_display_name(self):
        # Phương thức này được gọi khi giá trị của 'group_name' thay đổi
        for record in self:
            # Lặp qua từng bản ghi trong model
            record.display_name = record.group_name
            # Tính toán giá trị của 'display_name' dựa trên 'group_name' và 'group_id'
    # Ham thay doi trang thai favorite
    def toggle_favorite(self):
        for record in self:
            # Lặp qua từng bản ghi trong model
            record.is_favorite = not record.is_favorite
            # Đảo ngược giá trị của is_favorite (True thành False, hoặc False thành True).
    # Hàm đăng nội dung lên group
    def post_to_group(self):
        # Phương thức này đăng nội dung lên một nhóm Facebook
        for record in self:
            # Lặp qua từng bản ghi trong model
            if record.access_token and record.group_id and record.post_content:
                # Kiểm tra xem 'access_token', 'group_id', và 'post_content' có tồn tại hay không
                url = f"https://graph.facebook.com/{record.group_id}/feed"
                # Tạo URL cho API Graph của Facebook
                payload = {
                    'message': record.post_content,
                    'access_token': record.access_token
                }
                # Chuẩn bị dữ liệu để gửi trong yêu cầu POST
                response = requests.post(url, data=payload)
                # Gửi yêu cầu POST tới API của Facebook
                if response.status_code == 200:
                    # Kiểm tra mã trạng thái của phản hồi
                    record.message_post(body="Đăng thành công!")
                    # Đăng thông báo thành công
                else:
                    record.message_post(body="Đăng thất bại!")
                    # Đăng thông báo thất bại
    # Hàm bình luận lên bài viết
    def comment_on_post(self, post_id):
        # Phương thức này bình luận lên một bài viết cụ thể trên Facebook
        for record in self:
            # Lặp qua từng bản ghi trong model
            if record.access_token and post_id and record.comment_content:
                # Kiểm tra xem 'access_token', 'post_id', và 'comment_content' có tồn tại hay không
                url = f"https://graph.facebook.com/{post_id}/comments"
                # Tạo URL cho API Graph của Facebook để bình luận lên bài viết
                payload = {
                    'message': record.comment_content,
                    'access_token': record.access_token
                }
                # Chuẩn bị dữ liệu để gửi trong yêu cầu POST
                response = requests.post(url, data=payload)
                # Gửi yêu cầu POST tới API của Facebook
                if response.status_code == 200:
                    # Kiểm tra mã trạng thái của phản hồi
                    record.message_post(body="Bình luận thành công!")
                    # Đăng thông báo thành công
                else:
                    record.message_post(body="Bình luận thất bại!")
                    # Đăng thông báo thất bại

    # Hàm tạo group mới
    @api.model
    def create_group_manually(self, vals):
        return self.create(vals)

    # Hàm cập nhật thông tin group
    def update_group_info(self, vals):
        self.write(vals)