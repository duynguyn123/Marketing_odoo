{
    'name': 'Zalo Marketing Module v1',
    'version': '1.0',
    'summary': 'Post articles to Zalo Official Account (OA)',
    'images': ["static/description/icon.png"],
    'author': 'Your Name',
    'category': 'Social',
    'depends': ['base','website_sale','MarketingContent'],
    'data': [
        
        'views/zalo_post_views.xml',

        'data/cron_new_token.xml',

        'data/cron_post_feed.xml',

        # Tạm thời tắt auto verify video
        # 'data/cron_video_verify.xml',

        'views/zalo_app_view.xml',
        'views/zalo_account_view.xml',
        'views/zalo_post_video.xml',
        'views/zalo_schedule.xml',
        'views/zalo_video_converted.xml',
        'views/inherit_marketing_content.xml',
        'security/ir.model.access.csv',

        'views/menu_view.xml',

    ],
    'installable': True,
    'application': True,
}
