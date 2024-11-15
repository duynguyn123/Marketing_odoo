from odoo import models, fields, api
from odoo.addons.http_routing.models.ir_http import slug

class BlogMarketingContent(models.Model):
    _name = 'marketing.blog'
    _description = 'Blog Marketing Content'
    _inherits = {'marketing.content': 'content_id'}

    content_id = fields.Many2one('marketing.content', string='Marketing Content', required=True, ondelete='cascade', auto_join=True)
    blog_id = fields.Many2one('blog.post', string='Blog', required=True)
    temp_image = fields.Binary(string='Temporary Image', attachment=False)
    content = fields.Text(string='Content')
    url = fields.Char(string='URL')
    include_link = fields.Boolean(string='Include Link')

    @api.model_create_multi
    def create(self, vals_list):
        # Create marketing.content records
        for vals in vals_list:
            content_vals = {
                'content': vals.get('content', ''),
                'url': vals.get('url', ''),
                'include_link': vals.get('include_link', False)
            }
            content = self.env['marketing.content'].create(content_vals)
            vals['content_id'] = content.id

        # Create BlogMarketingContent records
        records = super(BlogMarketingContent, self).create(vals_list)

        # Update URL for each record after creation
        for record in records:
            self._update_url(record)
            self._check_and_add_to_category(record)

        return records

    def write(self, vals):
        res = super(BlogMarketingContent, self).write(vals)

        # Update URL if blog_id is updated
        if 'blog_id' in vals or not self.url:
            self._update_url(self)

        # Check if blog post belongs to a category
        self._check_and_add_to_category(self)

        return res

    def _update_url(self, record):
        if record.blog_id:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record.url = f"{base_url}/blog/{slug(record.blog_id.blog_id)}/post/{slug(record.blog_id)}"
            record.content_id.write({'url': record.url})

    def _check_and_add_to_category(self, record):
        blog_categories = record.blog_id.tag_ids
        categories = self.env['content.category'].search([('blog_category', 'in', blog_categories.ids)])
        
        for category in categories:
            category.write({'content_ids': [(4, record.content_id.id)]})

    @api.onchange('blog_id')
    def _onchange_blog_id(self):
        if self.blog_id:
            self.content = self.blog_id.name or ''
            if hasattr(self.blog_id, 'image_1920'):
                self.temp_image = self.blog_id.image_1920 or False
            else:
                self.temp_image = False
            self._update_url(self)
        else:
            self.content = ''
            self.temp_image = False
            self.url = ''
