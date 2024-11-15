odoo.define('facebook_marketing.facebook_data', function (require) {
    "use strict";

    var core = require('web.core');
    var ListController = require('web.ListController');

    ListController.include({
        init: function () {
            this._super.apply(this, arguments);
            core.bus.on('refresh_facebook_data', this, this._onRefreshFacebookData);
        },

        _onRefreshFacebookData: function () {
            this.reload();
        },

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var urlParams = new URLSearchParams(window.location.hash.slice(1));
                if (urlParams.get('refresh') === 'true') {
                    self.reload().then(function () {
                        urlParams.delete('refresh');
                        history.replaceState(null, '', '#' + urlParams.toString());
                    });
                }
            });
        },
    });
});