from odoo import models, fields, api
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
import calendar

class LoanPenalty(models.Model):
    _name = 'loan.penalty'
    _description = 'Loan Penalty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'date desc'

    name = fields.Char(string="Name")
    display_name = fields.Char(string="Account Name", compute="compute_display_name")
    member_id = fields.Many2one('member.account',string="Member")
    loan_id = fields.Many2one('loan.account',string="Reference Loan")
    date = fields.Date(string="Date", default=datetime.today().date())
    type = fields.Selection([('late_contribution', "Late Contribution"),
                             ('loan_expired', "Expired Loan"),
                             ], string="Type")
    amount = fields.Float(string="Amount")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)

    state = fields.Selection([('draft', "Draft"),
                              ('process', "Processing"),
                              ('validate', "Validated"),
                              ('paid', "Paid")
                              ], default='draft', tracking=True)
    remarks = fields.Text("Remarks")

    @api.depends('name', 'type')
    def compute_display_name(self):
        for rec in self:
            rec.display_name = "%s - %s" % (rec.name, dict(rec._fields['type'].selection).get(rec.type))

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('loan.penalty.sequence')
        vals.update({
            'name': name
        })
        res = super(LoanPenalty, self).create(vals)
        return res

    def action_submit(self):
        self.state = 'process'

    def action_validate(self):
        self.state = 'validate'

    def action_cron_late_contribution_fee(self):
        date_today = datetime.today().date()
        company_id = self.env.company

        if date_today.day == (int(company_id.grace_period) + 1):
            account_ids = self.env['member.account'].search([])

            prev_month = date_today + relativedelta(months=-1)

            _, num_days = calendar.monthrange(prev_month.year, prev_month.month)

            date_from = prev_month.replace(day=1)
            date_to = date(prev_month.year, prev_month.month, num_days)

            for account in account_ids:
                # contribution_id = self.env['member.contribution'].search([('member_account_id','=',member.id),
                #                                                           ('date','>=', date_from),
                #                                                           ('date','<=', date_to),
                #                                                           ('state','=', 'validate'),
                #                                                           ])

                contribution_id = self.env['loan.payment'].search([
                    ('state', '=', 'validate'),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('payment_type_code', 'in', ['CONTRIBUTION']),
                ])

                if contribution_id:
                    pass
                else:
                    penalty_id = self.create({
                        'type': 'late_contribution',
                        'date': date_today,
                        'member_id': account.id,
                        'amount': company_id.contribution_late_fee,
                        'state': 'process',
                        'remarks': "Late Contribution penalty for %s" %(date_from.strftime("%b %Y"))
                    })

                    payment_type_id = self.env.ref('osynx_loan.loan_payment_type_loan_contribution_fee')
                    self.send_penalty_notif(penalty_id, payment_type_id)

    def action_cron_expired_loan_fee(self):
        date_today = datetime.today().date()
        company_id = self.env.company

        expired_loan_ids = self.env['loan.account'].search([
            ('date_to', '<=', date_today),
            ('state', 'in', ['approve','extend']),
        ])

        for rec in expired_loan_ids:
            if rec.date_to == date_today:
                # if rec.date_to.day == date_today.day:
                penalty_id = self.create({
                    'type': 'loan_expired',
                    'date': date_today,
                    'member_id': rec.guarantor_id.id,
                    'loan_id': rec.id,
                    'amount': company_id.contribution_late_fee,
                    'remarks': "Expired Loan penalty for %s, end contract date is %s" % (rec.display_name, rec.date_to.strftime("%b %d, %Y")),
                    'state': 'process',
                })

                payment_type_id = self.env.ref('osynx_loan.loan_payment_type_loan_expired_loan_penalty')
                self.send_penalty_notif(penalty_id,payment_type_id)

                rec.write({
                    'state': 'expired'
                })

    def action_paid(self):
        for rec in self:
            payment_obj = self.env['loan.payment']

            if rec.type == 'loan_expired':
                payment_type_id = self.env.ref('osynx_loan.loan_payment_type_loan_expired_loan_penalty')

                payment_obj.create({
                    'payment_type_id': payment_type_id.id,
                    'account_id': rec.member_id.id,
                    'member_id': rec.member_id.partner_id.id,
                    'loan_id': rec.loan_id.id,
                    'penalty_id': rec.id,
                    'amount': rec.amount,
                    'date': rec.date,
                    'state': 'validate',
                })
            else :
                payment_type_id = self.env.ref('osynx_loan.loan_payment_type_loan_contribution_fee')

                payment_obj.create({
                    'payment_type_id': payment_type_id.id,
                    'account_id': rec.member_id.id,
                    'member_id': rec.member_id.partner_id.id,
                    'penalty_id': rec.id,
                    'amount': rec.amount,
                    'date': rec.date,
                    'state': 'validate',
                })

            rec.state = 'paid'


    def send_penalty_notif(self,penalty_id,payment_type_id):
        partner_ids = self.env.ref('osynx_loan.group_loan_manager').mapped('users').mapped('partner_id')

        notifs = []
        for rec in partner_ids:
            notifs.append((0, 0, {
                'notification_type': 'inbox',
                'res_partner_id': rec.id,
            }))

        message_id = penalty_id.message_notify(
            subject="%s Penalty Created!" % (payment_type_id.name),
            body="<p><strong>%s</strong> created with reference number <strong>%s</strong> for <strong>%s</strong>. For your validation."
                 % (payment_type_id.name, penalty_id.display_name, penalty_id.member_id.display_name),
            partner_ids=partner_ids.ids,
            subtype_xmlid='mail.mt_comment',
            email_layout_xmlid='mail.mail_notification_light',
            message_type='notification',
            notification_ids=notifs,
        )