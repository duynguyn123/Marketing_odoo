const AutoCommentSchedule = require('web.ListController');
const core = require('web.core');

AutoCommentSchedule.include({
    init: function () {
        this._super.apply(this, arguments);
        this.call('bus_service', 'addChannel', 'auto_comment_schedule');
        this.call('bus_service', 'on', 'notification', this, this._onNotification);
    },

    _onNotification: function (notifications) {
        for (let notif of notifications) {
            if (notif[0].startsWith('auto_comment_schedule_')) {
                const data = notif[1];
                if (data.type === 'update') {
                    console.log('Đã vào _onNotification');
                    this.reload();
                }
            }
        }
    },
});