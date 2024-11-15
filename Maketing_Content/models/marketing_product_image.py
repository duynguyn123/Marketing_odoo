from odoo import models, fields

class ProductTemplateImage(models.Model):
    _name = 'product.template.image'
    _description = 'Product Template Image'

    name = fields.Char(string='Name')
    image = fields.Binary(string='Image')
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')