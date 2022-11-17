##############################################################################
#    Copyright (C) 2021 Bitlect. All Rights Reserved
#    BItlect Extensions to Sms module


{
    'name': 'USIL Migration Module',
    'version': '14.0.0',
    'author': "Maach media",
    'category': 'Sales',
    'summary': '',
    'description': "",
    'depends': ['base', 'sale', 'property_sale'],
    "data": [
        'security/ir.model.access.csv',
        'wizard/import_view.xml',
        
    ],
    "sequence": 3,
    'installable': True,
    'application': True,
}
