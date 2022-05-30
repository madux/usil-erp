#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Maduka Sopulu Chris kingston
#
# Created:     20/04/2018
# Copyright:   (c) kingston 2018
# Licence:     <your licence>
#--------------------------------------------------------------------
{
    'name': 'Property Sales',
    'version': '10.0.1.0.0',
    'author': 'Maduka Sopulu',
    'description': """ERP Application for managing
                     the Estate management activities of a company""",
    'category': 'Sales',
    'depends': ['base', 'sale', 'account', 'l10n_uk', 'account_accountant', 'account_payment', 'mass_mailing', 'website'],
    'data': [
        'sequence/sequence.xml',
        'security/security_group.xml',
        'views/property_sales_views.xml',
        'views/sale_order.xml',
        'views/kanban_view.xml',
        'views/sales_analysis.xml',
        'views/account_payment.xml',
        'views/deallocation.xml',
        'views/asset.xml',
        # 'wizard/property_sale_update_qty.xml',
        'templates/graph_template.xml',
        'reports/offer_letter_new.xml',
        'reports/report_accountstatement.xml',
        'reports/receipt_todate.xml',
        'reports/provisional_allocation_letter.xml',
        'security/ir.model.access.csv',
        'data/email_template.xml',
        'data/payment_amount_action.xml',
    ],
    'price': 200.99,
    'currency': 'EUR',
    'sequence': 1,
    'installable': True,
    'auto_install': False,
    'application': True,
}
