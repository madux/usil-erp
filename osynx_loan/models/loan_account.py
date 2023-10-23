import base64
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools.safe_eval import safe_eval
import uuid

class LoanAccount(models.Model):
    _name = 'loan.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Loan Account'
    _order = 'date_from desc'
    _rec_name = 'display_name'

    display_name = fields.Char(string="Account Name", compute="compute_display_name", store=True)
    name = fields.Char(string="Name")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', readonly=True)

    guarantor_id = fields.Many2one('member.account',string="Guarantor")
    borrower_id = fields.Many2one('res.partner',string="Borrower")
    date_from = fields.Date(string="Start")
    date_to = fields.Date(string="End", compute='compute_date_to', store=True, tracking=True)
    principal = fields.Monetary(string="Principal Amount", currency_field='currency_id')
    term = fields.Float(string="Term", tracking=True)
    interest_id = fields.Many2one('loan.interest',string="Interest Rate")
    monthly_interest = fields.Monetary(string="Monthly Interest", currency_field='currency_id', compute='compute_interest')
    total_interest = fields.Monetary(string="Total Interest", currency_field='currency_id', compute='compute_interest')

    coop_earning = fields.Monetary(string="Company Earning", currency_field='currency_id', compute='compute_interest')
    guarantor_earning = fields.Monetary(string="Guarantor Earning", currency_field='currency_id', compute='compute_interest')
    state = fields.Selection([('draft', "Draft"),
                              ('queue', "On Queue"),
                              ('approve', "Running"),
                              ('expired', "Expired"),
                              ('extend', "Extended"),
                              ('paid', "Fully Paid")
                              ], default='draft', string="State", tracking=True)
    line_ids = fields.One2many('loan.account.line','loan_id',string="Loan Schedule")
    payment_ids = fields.One2many('loan.payment', 'loan_id', string="Loan Payment")
    penalty_ids = fields.One2many('loan.penalty', 'loan_id', string="Penalty")
    total_loan = fields.Monetary(string="Total Loan", currency_field='currency_id', compute='compute_totals')
    total_payment = fields.Monetary(string="Total Payment", currency_field='currency_id', compute='compute_totals')
    total_penalty = fields.Monetary(string="Total Penalty", currency_field='currency_id', compute='compute_totals')
    total_balance = fields.Monetary(string="Balance", currency_field='currency_id', compute='compute_totals')
    total_company_earning = fields.Monetary(string="Total Company Earning", currency_field='currency_id', compute='compute_total_earning')
    total_guarantor_earning = fields.Monetary(string="Total Guarantor Earning", currency_field='currency_id', compute='compute_total_earning')

    total_balance_interest = fields.Monetary(string="Interest Balance", currency_field='currency_id', compute='compute_totals')
    total_balance_principal = fields.Monetary(string="Principal Balance", currency_field='currency_id', compute='compute_totals')
    total_loan_words = fields.Char(string="Amount In Words:", compute='_amount_in_word')

    @api.onchange('borrower_id')
    def onchange_borrower_id(self):
        member_id = self.env['member.account'].search([('partner_id', '=', self.borrower_id.id)])
        if member_id:
            interest_id = self.env['loan.interest'].search([('type','=','member')],limit=1)
        else:
            interest_id = self.env['loan.interest'].search([('type', '=', 'nonmember')], limit=1)
        self.interest_id = interest_id.id

    @api.depends('date_from', 'term')
    def compute_date_to(self):
        for rec in self:
            rec.date_to = False
            if rec.date_from:
                rec.date_to = rec.date_from + relativedelta(months=int(rec.term))

    @api.depends('principal', 'interest_id')
    def compute_interest(self):
        for rec in self:
            rec.monthly_interest = (rec.principal * (rec.interest_id.interest / 100))
            rec.coop_earning = (rec.principal * (rec.interest_id.coop_rate / 100))
            rec.guarantor_earning = (rec.principal * (rec.interest_id.guarantor_rate / 100))
            rec.total_interest = rec.monthly_interest * rec.term

    @api.depends('line_ids')
    def compute_totals(self):
        for rec in self:
            rec.total_loan = sum(r.amount for r in rec.line_ids)
            rec.total_payment = sum(r.amount for r in rec.payment_ids.filtered(lambda r: r.state == 'validate'))
            rec.total_penalty = sum(r.amount for r in rec.penalty_ids.filtered(lambda r: r.type == 'loan_expired' and r.state in ['validate','paid']))
            rec.total_balance_interest = rec.total_interest - sum(r.amount for r in rec.payment_ids.filtered(lambda r: r.state == 'validate'
                                                                                                                       and r.payment_type_code == 'INTEREST'))
            rec.total_balance_principal = rec.principal - sum(r.amount for r in rec.payment_ids.filtered(lambda r: r.state == 'validate'
                                                                                                                   and r.payment_type_code == 'PRINCIPAL'))
            rec.total_balance = (rec.total_loan + rec.total_penalty) - rec.total_payment

            if rec.state != 'paid':
                if rec.total_payment:
                    if rec.total_balance == 0.00:
                        rec.state = 'paid'

    @api.depends('payment_ids')
    def compute_total_earning(self):
        for rec in self:
            rec.total_guarantor_earning = sum(r.member_earning for r in rec.payment_ids)
            rec.total_company_earning = sum(r.company_earning for r in rec.payment_ids)

    @api.depends('name', 'borrower_id')
    def compute_display_name(self):
        for rec in self:
            rec.display_name = "%s - %s" % (rec.borrower_id.name, rec.name)

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('loan.account.sequence')
        vals.update({
            'name': name
        })
        res = super(LoanAccount, self).create(vals)
        return res

    def action_compute_installment(self):
        self.line_ids.unlink()
        lines = []
        date_from = self.date_from
        for rec in range(int(self.term)):
            date_from += relativedelta(months=1)

            val = (0,0, {
                'date': date_from,
                'amount': self.monthly_interest,
                # 'company_earning': self.coop_earning,
                # 'guarantor_earning': self.guarantor_earning,
                'description': "Monthly Interest",

            })
            lines.append(val)

        principal_val = (0, 0, {
            'date': date_from,
            'amount': self.principal,
            'description': 'Principal Amount',
        })
        lines.append(principal_val)
        self.line_ids = lines

    def action_queue(self):
        self.state = 'queue'

    def action_approve(self):
        for rec in self:
            rec.state = 'approve'

    def action_extend(self):
        context = self.env.context

        if context.get('new_term'):
            self.term += context.get('new_term')

            self.state = 'extend'

    @api.model
    def get_loan_account_domain(self, val):
        x = 0

    def action_send(self):
        for loan in self:
            report = self.env.ref('osynx_loan.action_report_loan_account', False)
            pdf_content, content_type = report.sudo()._render_qweb_pdf(loan.id)

            pdf_name = _("Loan Statement - %s" % loan.borrower_id.name)
            attachment = self.env['ir.attachment'].sudo().create({
                'name': pdf_name,
                'type': 'binary',
                'datas': base64.encodebytes(pdf_content),
                'res_model': loan._name,
                'res_id': loan.id
            })
            # Send email to employees
            template = self.env.ref('osynx_loan.mail_template_loan_statement', raise_if_not_found=False)
            if template:
                email_values = {
                    'attachment_ids': attachment,
                }
                template.send_mail(
                    loan.id,
                    email_values=email_values,
                    notif_layout='mail.mail_notification_light',
                    force_send=True
                )

    def check_loan_expiry(self):
        loan_ids = self.env['loan.account'].search([
            # ('date_to', '<=', date_today),
            ('state', 'in', ['approve', 'extend']),
        ])

        for rec in loan_ids:
            date_today = datetime.today().date()
            diff = date_today - rec.date_to

            if diff.days == int(rec.company_id.grace_period):
                rec.message_post(
                    subject="Loan is about to expire - %s" % (rec.display_name),
                    body="<p>Dear <strong>%s</strong>,</p>"
                         "<p>Your Loan with reference number <strong>%s</strong>"
                         " dated <strong>%s</strong> to <strong>%s</strong> for borrower <strong>%s</strong> is set to expire in <strong>%s</strong> Days!</p>"
                         "<p>Please settle the balances or extend your loan contract to avoid penalty."
                         "<br/>To Extend loan contract please attach to this email your <strong>Loan Agreement Extension Form</strong></p>"
                         "<p>Thank you!</p>"
                         "<p style='font-style:italic'>*** This is system generated notification ***</p>"
                         % (rec.guarantor_id.partner_id.name, rec.name, rec.date_from.strftime("%b %d"), rec.date_to.strftime("%b %d, %Y"), rec.borrower_id.name,
                            rec.company_id.grace_period),
                    partner_ids=rec.guarantor_id.partner_id.ids,
                    subtype_xmlid='mail.mt_comment',
                    email_layout_xmlid='mail.mail_notification_light',
                    message_type='comment',
                )

    def _amount_in_word(self):
        for rec in self:
            rec.total_loan_words = str(rec.currency_id.amount_to_text(rec.principal))

    def action_send_loan_agreement(self):
        for rec in self:
            report = self.env.ref('osynx_loan.action_report_loan_agreement')

            pdf_content, content_type = report.sudo()._render_qweb_pdf(self.id)

            attachment = self.env['ir.attachment'].create({
                'name': rec.display_name if rec.display_name else '',
                'datas': base64.b64encode(pdf_content),
                'type': 'binary',
                'res_model': rec._name,
                'res_id': rec.id,
            })

            rec.message_post(
                subject="Loan Agreement - %s" % (rec.display_name),
                body="<p>Dear <strong>%s</strong>,</p>"
                     "<p>The attached file is your loan agreement. Please sign and attach back to this email for final processing of your loan."
                     "<p>Thank you!</p>" %(rec.guarantor_id.partner_id.name),
                partner_ids=rec.guarantor_id.partner_id.ids,
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',
                message_type='comment',
                attachment_ids=attachment.ids
            )


class LoanAccountLine(models.Model):
    _name = 'loan.account.line'
    _description = 'Loan Account Line'

    name = fields.Date(string="Name", related='date')
    date = fields.Date(string="Due Date")
    amount = fields.Float(string="Amount")
    description = fields.Char(string="Description")
    loan_id = fields.Many2one('loan.account', string="Loan")
    borrower_id = fields.Many2one(related='loan_id.borrower_id')
    guarantor_id = fields.Many2one(related='loan_id.borrower_id')
    active = fields.Boolean(string="Active", default=True)

# class LoanOverview(models.Model):
#     _name = 'loan.overview'