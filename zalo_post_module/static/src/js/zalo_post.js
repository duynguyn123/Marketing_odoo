odoo.define('zalo_post_module.zalo_post_js', function (require) {
    'use strict';

    const FormController = require('web.FormController');
    const core = require('web.core');

    const _t = core._t;

    FormController.include({
        _onFieldChanged: function (ev) {
            this._super(ev);
            const isPostToZaloField = this.model.get(ev.data.changes, 'is_post_to_zalo');
            if (ev.data.fieldName === 'is_post_to_zalo') {
                const scheduleDateField = this.fields['schedule_date'];
                if (isPostToZaloField) {
                    scheduleDateField.$el.hide(); // Ẩn trường
                } else {
                    scheduleDateField.$el.show(); // Hiển thị trường
                }
            }
        },
    });
});
