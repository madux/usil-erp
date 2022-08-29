# Copyright 2018 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    loan_line_id = fields.Many2one(
        "account.loan.line", readonly=True, ondelete="restrict",
    )
    loan_id = fields.Many2one(
        "account.loan", readonly=True, store=True, ondelete="restrict",
    )

    def post(self):
        res = super().post()
        memo_ref = self.env['memo.model'].search([('name', '=', self.name)], limit=1)        
        memo_ref.loan_reference = self.id
        for record in self:
            loan_line_id = record.loan_line_id
            if loan_line_id:
                if not record.loan_line_id:
                    record.loan_line_id = loan_line_id
                record.loan_id = loan_line_id.loan_id
                record.loan_line_id.check_move_amount()
                record.loan_line_id.loan_id.compute_posted_lines()
                if record.loan_line_id.sequence == record.loan_id.periods:
                    record.loan_id.close()
        for rec in memo_ref:
            if memo_ref:
                rec.write({"state": "Done"})
        return res
