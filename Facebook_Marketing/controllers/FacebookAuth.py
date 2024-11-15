from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class FacebookAuth(http.Controller):
    @http.route('/facebook_auth_callback', type='http', auth="public", website=True, csrf=False)
    def facebook_callback(self, **kw):
        _logger.info("Facebook callback received with parameters: %s", kw)
        if 'code' in kw:
            try:
                manager_account = request.env['manager.account'].sudo().search([], limit=1)
                if manager_account:
                    manager_account.facebook_auth_callback(kw['code'])
                    return self._render_success_page()
                else:
                    _logger.error("No manager.account record found")
                    return "Authentication failed. No manager account found."
            except Exception as e:
                _logger.error("Error during Facebook authentication: %s", str(e))
                return "Authentication failed. Please try again or contact support."
        else:
            _logger.warning("No code received in Facebook callback")
            return "Authentication failed. No code received."

    def _render_success_page(self):
        return """
        <html>
            <head>
                <title>Authentication Successful</title>
            </head>
            <body>
                <h1>Authentication Successful!</h1>
                <p>Your Facebook account has been successfully authenticated. This window will close automatically.</p>
                <script>
                    setTimeout(function() {
                        window.close();
                    }, 3000);  // Close the window after 3 seconds
                </script>
            </body>
        </html>
        """

# Add this line at the end of the file
_logger.info("FacebookAuth controller loaded")