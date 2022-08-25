#-------------------------------------------------------------------------------
# Name:        'Maach HR Appraisal',
# Purpose:
#
# Author:      Maach media 
#
# Created:     20/4/2022
# Copyright:   (c)MAACH 2022
# Licence:     <your licence>
#-------------------------------------------------------------------------------
{
    'name': 'Maach HR Appraisal',
    'version': '14.0.1',
    'author': 'Maach Media services',
    'description':"""
    Maach HR Appraisal application developed based on a standard HR appraisal template... 
    """,
    'depends': ['hr'],
    'data': [
        'security/security_view.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/hr_appraisal_view.xml',
        'views/assets.xml',
        'views/hr_employee_view.xml',
        'views/forward_view.xml',
        'sequence/sequence.xml',
    ],
    'sequence': 3,
    'installable': True,
    'application': True,
    'auto_install': False,
}