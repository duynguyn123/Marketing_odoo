from odoo import http
from odoo.http import request

class AutoCommentController(http.Controller):
    @http.route('/auto_comment/get_updates', type='json', auth='user')
    def get_updates(self):
        # Lấy channel cho auto.comment.schedule
        channel = request.env['ir.model.data'].xmlid_to_object('facebook_marketing.channel_auto_comment_schedule')
        if not channel:
            return []
        
        # Lấy các bản ghi auto.comment.schedule mà người dùng hiện tại có quyền đọc
        schedules = request.env['auto.comment.schedule'].search([])
        
        return [{
            'channel': channel.name,
            'id': schedule.id,
        } for schedule in schedules]