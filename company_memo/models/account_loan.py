from odoo import models, fields, api, _


class LoanAccount(models.Model):
    _inherit = "loan.account"

    memo_id = fields.Many2one('memo.model','Memo Reference')