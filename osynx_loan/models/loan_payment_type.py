from odoo import models, fields, api

class LoanPaymentType(models.Model):
    _name = 'loan.payment.type'
    _description = 'Loan Account Payment'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
