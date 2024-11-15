from odoo import models, fields, api
import base64

class MarketingContentImageWizard(models.TransientModel):
    _name = 'marketing.content.image.wizard'
    _description = 'Wizard for uploading multiple images'

    image_files = fields.Binary(string="Upload Multiple Images")
    image_filenames = fields.Char(string="Image Filenames")

    def upload_images(self):
        active_id = self.env.context.get('active_id')
        if not active_id:
            return

        content = self.env['marketing.content'].browse(active_id)
        if self.image_files and self.image_filenames:
            images_data = base64.b64decode(self.image_files)
            filenames = self.image_filenames.split(",")
            
            for filename in filenames:
                if images_data:
                    self.env['marketing.content.image'].create({
                        'content_id': content.id,
                        'image': images_data,
                        'datas': images_data,
                    })

        return {'type': 'ir.actions.act_window_close'}
