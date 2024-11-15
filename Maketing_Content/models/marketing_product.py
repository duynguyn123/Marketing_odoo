from odoo import models, fields, api
from odoo.addons.http_routing.models.ir_http import slug

class ProductMarketingContent(models.Model):
    _name = 'marketing.product'
    _description = 'Product Marketing Content'
    _inherits = {'marketing.content': 'content_id'}

    content_id = fields.Many2one('marketing.content', string='Marketing Content', required=True, ondelete='cascade', auto_join=True)
    product_id = fields.Many2one('product.template', string='Product', required=True)
    temp_image = fields.Binary(string='Temporary Image', attachment=False)
    content = fields.Text(string='Content')
    url = fields.Char(string='URL')
    include_link = fields.Boolean(string='Include Link')
    product_template_image_ids = fields.Many2many('product.template.image', string='Product Images')  # Add this line

    @api.model
    def create(self, vals):
        # Tạo bản ghi marketing.content 
        content_vals = {
            'content': vals.get('content', ''),
            'url': vals.get('url', ''),
            'include_link': vals.get('include_link', False)
        }
        content = self.env['marketing.content'].create(content_vals)
        vals['content_id'] = content.id

        # Tạo ProductMarketingContent
        res = super(ProductMarketingContent, self).create(vals)
        
        # Load tất cả ảnh từ sản phẩm liên kết
        if res.product_id:
            for image_field in ['image_1920', 'image_1024', 'image_512', 'image_256', 'image_128']:
                image_data = getattr(res.product_id, image_field, False)
                if image_data:
                    image = self.env['marketing.content.image'].create({
                        'content_id': res.content_id.id,
                        'image': image_data,
                        'datas': image_data,
                    })
                    res.content_id.write({'image_ids': [(4, image.id)]})

        # Kiểm tra nếu sản phẩm thuộc category
        self._check_and_add_to_category(res)

        return res

    def write(self, vals):
        # Cập nhật bản ghi marketing.content
        content_vals = {}
        if 'content' in vals:
            content_vals['content'] = vals['content']
        if 'url' in vals:
            content_vals['url'] = vals['url']
        if 'include_link' in vals:
            content_vals['include_link'] = vals['include_link']
        
        if content_vals:
            self.content_id.write(content_vals)

        res = super(ProductMarketingContent, self).write(vals)

        # Load tất cả ảnh từ sản phẩm liên kết nếu có thay đổi
        if vals.get('product_id'):
            for image_field in ['image_1920', 'image_1024', 'image_512', 'image_256', 'image_128']:
                image_data = getattr(self.product_id, image_field, False)
                if image_data:
                    image = self.env['marketing.content.image'].create({
                        'content_id': self.content_id.id,
                        'image': image_data,
                        'datas': image_data,
                    })
                    self.content_id.write({'image_ids': [(4, image.id)]})

        # Kiểm tra nếu sản phẩm thuộc category
        self._check_and_add_to_category(self)

        return res

    def _check_and_add_to_category(self, record):
        # Lấy tất cả các categories của sản phẩm
        product_categories = record.product_id.categ_id
        # Lấy tất cả các categories của nội dung
        categories = self.env['content.category'].search([('product_category', 'in', product_categories.ids)])
        
        # Nếu có category thỏa điều kiện, thêm sản phẩm vào content_ids của category
        for category in categories:
            category.write({'content_ids': [(4, record.content_id.id)]})


    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.content = self.product_id.name or ''
            self.temp_image = self.product_id.image_1920 or False  # Chọn ảnh chính để hiển thị
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            self.url = f"{base_url}/shop/product/{slug(self.product_id)}"
        else:
            self.content = ''
            self.temp_image = False
            self.url = ''