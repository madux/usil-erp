# -*- coding: utf-8 -*-
{
    'name': 'Office Memo Application',
    'version': '14.0',
    'author': 'Maach Services',
    'description': """An Odoo Memo application use to send memo / information accross individuals: 
    It can also be used to send requests.""",
    'summary': 'Memo application for Companies etc ',
    'category': 'Base',
    # 'live_test_url': "https://www.youtube.com/watch?v=KEjxieAoGeA&feature=youtu.be",

    'depends': ['base', 'account', 'account_loan', 'mail', 'hr'],
    'data': [
        'security/security_group.xml', 
        'sequence/sequence.xml',
        'views/company_memo_view.xml',
        # 'views/res_users.xml',
        'views/memo_forward_view.xml',
        'wizard/return_memo_wizard_view.xml',
        'reports/report_memo.xml',
        'views/assets.xml',
        'security/ir.model.access.csv'
    ],
    # 'qweb': [
    #     'static/src/xml/base.xml',
    # ],
    'price': 135.00,
    'sequence': 1,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
}
