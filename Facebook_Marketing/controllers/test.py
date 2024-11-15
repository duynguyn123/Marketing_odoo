from odoo import http
from odoo.http import request

@http.route('/test', type='http', auth="public", website=True)
def test_route(self):
    return "Test route is working!"