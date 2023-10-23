# -*- coding: utf-8 -*-
{
    'name': "Loan Management (Cooperative)",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Osynx Solutions",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'OPL-1',
    # any module necessary for this one to work correctly
    'depends': ['base','mail','portal','website','contacts'],

    # always loaded
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        # 'data/config_data.xml',
        'data/website_page.xml',
        'data/ir_sequence.xml',
        'data/ir_actions_server.xml',
        'data/ir_cron.xml',
        'data/ir_config_parameter.xml',
        'data/loan_interest_data.xml',
        'data/loan_payment_type_data.xml',
        'data/mail_template.xml',
        'wizard/loan_extend_wizard_views.xml',
        'wizard/loan_report_wizard_views.xml',
        'reports/report.xml',
        'reports/report_summary.xml',
        'reports/report_loan_summary.xml',
        'reports/report_loan_payout_summary.xml',
        'reports/report_earning_summary.xml',
        'reports/report_member_statement.xml',
        'reports/report_loan_account.xml',
        'reports/report_member_contract.xml',
        'reports/report_loan_agreement.xml',
        # 'views/assets.xml',
        'views/loan_interest_views.xml',
        'views/loan_payment_type_views.xml',
        'views/member_account_views.xml',
        'views/member_contribution_views.xml',
        'views/loan_account_views.xml',
        'views/loan_penalty_views.xml',
        'views/loan_payment_views.xml',
        'views/menuitem.xml',
        'views/res_config_settings_views.xml',
        # 'views/website_contributions.xml',
        'views/website_loan_payments.xml',
        'views/website_submit_payment.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'osynx_loan/static/src/js/*',
        ],
        'web.assets_backend': [
        ],
    },
}
