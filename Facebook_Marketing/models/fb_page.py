from odoo import models, fields, api

class FacebookPage(models.Model):
    _name = 'facebook.page'
    _description = 'Facebook Page'

    account_id = fields.Many2one('manager.account', string='Account')  # Liên kết với mô hình manager.account
    page_avatar = fields.Binary('Avatar')  # Lưu trữ ảnh đại diện của trang
    page_name = fields.Char(string="Name")  # Tên của trang
    page_id = fields.Char(string="Page ID")  # ID của trang
    access_token = fields.Char(string="Access Token")  # Mã truy cập của trang
    category = fields.Char(string="Main Category")  # Danh mục chính của trang
    category_ids = fields.Many2many('facebook.category', string='Categories')  # Liên kết nhiều danh mục với mô hình facebook.category

    is_favorite = fields.Boolean(string="Favorite", default=False, tracking=True)  # Đánh dấu trang yêu thích, mặc định là False và có tính năng theo dõi thay đổi
    display_name = fields.Char(compute='_compute_display_name')  # Tên hiển thị được tính toán bởi phương thức _compute_display_name
    
    ######################PHƯƠNG THỨC#########################
    @api.depends('page_name')
    def _compute_display_name(self):
        """
        Tính toán tên hiển thị của trang Facebook dựa trên tên trang.
        """
        for record in self:
            record.display_name = record.page_name

    def toggle_favorite(self):
        """
        Chuyển đổi trạng thái yêu thích của trang Facebook.
        Nếu is_favorite là True, nó sẽ được đặt thành False và ngược lại.
        """
        for record in self:
            record.is_favorite = not record.is_favorite