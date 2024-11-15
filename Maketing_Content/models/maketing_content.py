from odoo import models, fields, api

class MarketingContent(models.Model):
    _name = 'marketing.content'
    _description = 'Marketing Content'

    active = fields.Boolean(string='Active', default=True)
    post_ids = fields.One2many('marketing.post', 'content_id', string='Posts')
    title = fields.Char(string='Title', required=True)
    content = fields.Text(string='Content')
    image_ids = fields.One2many('marketing.content.image', 'content_id', string='Images', help='Upload multiple images')
    url = fields.Char(string='Link')
    include_link = fields.Boolean(string='Include Link in Post', default=False)
    category_id = fields.Many2one('content.category', string='Category', help="The category this content belongs to")
    has_posts = fields.Boolean(string='Has Posts', compute='_compute_has_posts', store=True)
    product_category_ids = fields.Many2many('product.category', string='Product Categories')

    @api.depends('post_ids')
    def _compute_has_posts(self):
        for record in self:
            record.has_posts = bool(record.post_ids)
            
    @api.model
    def post_to_facebook(self):
        pass
    
    @api.model
    def post_to_zalo(self):
        pass
    
    def action_add_image(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Image',
            'view_mode': 'form',
            'res_model': 'marketing.content.image',
            'target': 'new',
            'context': {
                'default_content_id': self.id,
            }
        }