from odoo import models, fields, api, _
from odoo.exceptions import ValidationError 


class Forward_Wizard(models.TransientModel):
    _name = "memo.foward"

    resp = fields.Many2one('res.users', 'Current Sender')
    memo_record = fields.Many2one('memo.model','Memo Reference',)
    description_two = fields.Text('Comment')
    date = fields.Datetime('Date', default=lambda self: fields.datetime.now())#, default=fields.Datetime.now())
    direct_employee_id = fields.Many2one('hr.employee', 'Direct To')
    # amountfig = fields.Float('Budget Amount', store=True)
    users_followers = fields.Many2many('hr.employee', string='Add followers')
    is_officer = fields.Boolean(string="Is Officer")

    def forward_memo(self):  # Always available,
        if self.memo_record.memo_type == "Payment":
            if self.memo_record.amountfig < 0:
                raise ValidationError('If you are running a payment Memo, kindly ensure the amount is \
                    greater than 0')
        msg = "No Comment"
        if self.description_two:
            msg = self.description_two
             
        if self.direct_employee_id:
            lists = []  
            body = "</br><b>{}:</b> {}</br>".format(self.env.user.name, self.description_two if self.description_two else "-")
            memo = self.env['memo.model'].search([('id', '=', self.memo_record.id)])
            comment_msg = " "
            if memo.comments:
                comment_msg = memo.comments if memo.comments else "-"
            memo.write({
                'res_users': [(4, self.env.uid)],
                        'set_staff': self.direct_employee_id.id, 'direct_employee_id': self.direct_employee_id.id, 'state': 'Sent',
                        'users_followers': [(4, self.direct_employee_id.id)],
                        'comments': comment_msg +' '+body,})
            # return{'type': 'ir.actions.act_window_close'}
            
        else:
            raise ValidationError('Please select an Employee to Direct To')
        return self.memo_record.forward_memos(self.direct_employee_id.name, msg)
 