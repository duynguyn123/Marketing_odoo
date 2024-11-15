from odoo import models, fields, api

class ContentCategory(models.Model):
    _name = 'content.category'
    _description = 'Content Category'

    # Thêm các trường cần thiết
    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')
    parent_category = fields.Many2one('content.category', string='Parent Category')
    parent_category_path = fields.Char(string='Parent Path')
    blog_category = fields.Many2many('blog.tag', string='Blog Categories')
    product_category = fields.Many2many('product.category', string='Product Categories')
    subcategory_ids = fields.One2many('content.category', 'parent_category', string='Subcategories')
    content_ids = fields.Many2many('marketing.content', 'content_category_rel', 'category_id', 'content_id', string='Marketing Content', compute='_compute_content_ids', store=True)

    @api.depends('parent_category')
    def _compute_parent_category_name(self):
        for record in self:
            record.parent_category_name = record.parent_category.name if record.parent_category else ''

    @api.depends('product_category', 'blog_category')
    def _compute_content_ids(self):
        for category in self:
            content_ids = []
            # Tìm tất cả nội dung marketing đã có trong danh mục
            existing_content_ids = self.env['marketing.content'].search([('category_id', '=', category.id)]).ids
            
            # Lọc ra nội dung marketing chưa có danh mục
            marketing_contents = self.env['marketing.content'].search([('id', 'not in', existing_content_ids)])
            content_ids.extend(marketing_contents.ids)

            category.content_ids = [(6, 0, content_ids)]

    @api.model
    def create(self, vals):
        # Generate a unique content_category_id (nếu cần thiết)
        vals['content_category_id'] = self.env['ir.sequence'].next_by_code('content.category') or 'New'
        
        # Tạo bản ghi danh mục nội dung
        category = super(ContentCategory, self).create(vals)
        
        # Cập nhật nội dung marketing nếu có sản phẩm hoặc danh mục blog
        if 'product_category' in vals or 'blog_category' in vals:
            category._compute_content_ids()
        
        return category

    def write(self, vals):
        res = super(ContentCategory, self).write(vals)
        if 'product_category' in vals or 'blog_category' in vals:
            self._compute_content_ids()
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('content_category_id', operator, name)]
        categories = self.search(domain + args, limit=limit)
        return categories.name_get()

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.content_category_id:
                name = f'[{record.content_category_id}] {name}'
            result.append((record.id, name))
        return result

    def get_unassigned_content(self):
        """ Trả về danh sách các nội dung marketing chưa có danh mục nào """
        # Tìm tất cả nội dung marketing đã có danh mục
        assigned_content_ids = self.env['marketing.content'].search([('category_ids', '!=', False)]).ids
        # Lọc ra nội dung marketing chưa có danh mục
        unassigned_content = self.env['marketing.content'].search([('id', 'not in', assigned_content_ids)])
        return unassigned_content

    def add_marketing_content(self, content_id):
        """Thêm nội dung marketing vào danh mục."""
        marketing_content = self.env['marketing.content'].browse(content_id)
        if marketing_content:
            self.content_ids = [(4, marketing_content.id)]  # Thêm nội dung marketing vào danh mục
