from odoo import http
from odoo.http import request
import base64

class ZaloVideoController(http.Controller):
    
    @http.route('/zalo/upload_video', type='http', auth='user', methods=['POST'], website=True)
    def upload_video(self, **post):
        # Extract form data
        video_name = post.get('name')
        video_file = post.get('video_file')
        file_name = post.get('file_name')

        # Convert base64 to binary
        video_binary = base64.b64decode(video_file)

        # Call the model method to upload the video to Zalo API
        record = request.env['zalo.post'].create({
            'name': video_name,
            'video_file': video_binary,
            'file_name': file_name,
        })

        # Trigger upload to Zalo
        result = record.upload_video_to_zalo()

        # Return success/failure response
        return request.render('zalo_video_upload.result_template', {
            'result': result
        })
