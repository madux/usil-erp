import base64
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools.safe_eval import safe_eval
import uuid

class LoanPayment(models.Model):
    _name = 'loan.payment'
    _inherit = ['portal.mixin', 'mail.thread.cc', 'mail.activity.mixin']
    _description = 'Loan Account Payment'
    _order = 'date desc'

    MONTHS = [
        ('jan', "January"),
        ('feb', "February"),
        ('march', "March"),
        ('april', "April"),
        ('may', "May"),
        ('june', "June"),
        ('july', "July"),
        ('aug', "August"),
        ('sep', "September"),
        ('oct', "October"),
        ('nov', "November"),
        ('dec', "December"),

    ]

    def _get_default_access_token(self):
        return str(uuid.uuid4())

    def _compute_access_url(self):
        for rec in self:
            rec.access_url = '/my/loanpayment/%s' % rec.id

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)

        user_id = self.env['res.users'].sudo().browse(self.env.uid)

        if user_id:
            res['member_id'] = user_id.partner_id.id
        return res

    name = fields.Char(string="Reference")
    active = fields.Boolean(string="Active", default=True)
    date = fields.Date(string="Date",default=datetime.today().date())
    amount = fields.Float(string="Amount")
    member_id = fields.Many2one('res.partner', string="Member")
    penalty_id = fields.Many2one('loan.penalty', string="Penalty")
    payment_type_id = fields.Many2one('loan.payment.type', string="Payment Type")
    payment_type_code = fields.Char(related='payment_type_id.code', string="Payment Code")
    contribution_month = fields.Selection(MONTHS, string="Month")
    # loan_id = fields.Many2one('loan.account', string="Loan", domain="[('guarantor_id','=','member_id'),('state','=','approve')]")
    loan_id = fields.Many2one('loan.account', string="Loan")
    account_id = fields.Many2one('member.account', string="Account")
    currency_id = fields.Many2one(related='loan_id.currency_id')
    principal = fields.Monetary(related='loan_id.principal')
    monthly_interest = fields.Monetary(related='loan_id.monthly_interest')
    total_interest = fields.Monetary(related='loan_id.total_interest')
    total_balance_interest = fields.Monetary(related='loan_id.total_balance_interest')
    total_balance_principal = fields.Monetary(related='loan_id.total_balance_principal')
    company_earning = fields.Float(string="Company Earning", compute='compute_total_earning')
    member_earning = fields.Float(string="Member Earning", compute='compute_total_earning')
    # payment_type = fields.Selection([
    #     ('contribution', "Contribution"),
    #     ('principal', "Principal"),
    #     ('interest', "Interest"),
    #     ('penalty', "Penalty"),
    # ], string="Payment Type")
    state = fields.Selection([('draft', "Draft"),
                              ('process', "Processing"),
                              ('validate', "Validated")
                              ], default='draft', tracking=True)


    access_url = fields.Char('Portal Access URL', compute='_compute_access_url', help='Contract Portal URL')
    access_token = fields.Char('Access Token', default=lambda self: self._get_default_access_token(), copy=False)

    @api.onchange('member_id')
    def _onchange_member_id(self):
        partner_id = self.member_id
        domain = [('partner_id', '=', partner_id.id)]

        return {'domain': {'account_id': domain}}

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.payment_type_code in ['LATE_CONTRIBUTION']:
            if self.account_id:
                domain_penalty_id = [('member_id', '=', self.account_id.id)]
                return {'domain': {'penalty_id': domain_penalty_id}}
        elif self.payment_type_code in ['EXPIRE_LOAN']:
            domain = [('guarantor_id', '=', self.account_id.id)]
            return {'domain': {'loan_id': domain}}

    @api.onchange('loan_id')
    def _onchange_loan_id(self):
        domain = [('loan_id', '=', self.loan_id.id)]

        return {'domain': {'penalty_id': domain}}

    @api.onchange('payment_type_id')
    def onchange_payment_type_id(self):
        self.account_id = False
        self.loan_id = False
        self.penalty_id = False
        self.amount = 0.00
        self.contribution_month = ""

    @api.onchange('penalty_id')
    def onchange_penalty_id(self):
        for rec in self:
            if rec.penalty_id:
                if rec.payment_type_code == 'EXPIRE_LOAN':
                    if rec.penalty_id.type == 'loan_expired':
                        rec.loan_id = rec.penalty_id.loan_id.id

                rec.amount = rec.penalty_id.amount

    # @api.onchange('loan_id')
    # def onchange_loan_id(self):
    #     for rec in self:
    #         if rec.loan_id:
    #             rec.member_id = rec.loan_id.guarantor_id.id
    #
    #             if rec.payment_type_id == 'interest':
    #                 rec.amount = rec.loan_id.monthly_interest
    #             elif rec.payment_type_id == 'principal':
    #                 rec.amount = rec.loan_id.principal
    #             elif rec.payment_type_id == 'contribution':
    #                 rec.amount = 1000
    #             elif rec.payment_type_id == 'penalty':
    #                 rec.amount = rec.penalty_id.amount
    #             else:
    #                 rec.amount = 0


    @api.depends('amount','payment_type_id')
    def compute_total_earning(self):
        for rec in self:
            rec.member_earning = 0.00
            rec.company_earning = 0.00
            if rec.payment_type_code == 'INTEREST':
                if rec.loan_id.interest_id.type == 'nonmember':
                    rec.member_earning = (rec.amount * (rec.loan_id.interest_id.guarantor_rate / 100))
                    rec.company_earning = (rec.amount * (rec.loan_id.interest_id.coop_rate / 100))
                else:
                    rec.company_earning = rec.amount

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('loan.payment.sequence')
        vals.update({
            'name': name
        })
        res = super(LoanPayment, self).create(vals)
        return res

    def action_submit(self):
        self.state = 'process'

        partner_ids = self.env.ref('osynx_loan.group_loan_manager').mapped('users').mapped('partner_id')

        notifs = []
        for rec in partner_ids:
            notifs.append((0, 0, {
                'notification_type': 'inbox',
                'res_partner_id': rec.id,
            }))

        message_id = self.message_notify(
            subject="%s Payment Created!" % (self.payment_type_id.name),
            body="<p><strong>%s</strong> created with reference number <strong>%s</strong> for <strong>%s</strong>. For your validation."
                 % (self.payment_type_id.name, self.name, self.member_id.name),
            partner_ids=partner_ids.ids,
            subtype_xmlid='mail.mt_comment',
            email_layout_xmlid='mail.mail_notification_light',
            message_type='notification',
            notification_ids=notifs,
        )

    def action_validate(self):
        for rec in self:
            if rec.payment_type_code == ['EXPIRE_LOAN','LATE_CONTRIBUTION']:
                rec.penalty_id.write({
                    'state': 'paid'
                })

            rec.state = 'validate'


            rec.message_post(
                subject="Payment Posted - %s" % (rec.name),
                body="<p>Dear <strong>%s</strong>,</p>"
                     "<p>Your payment with reference number <strong>%s</strong>"
                     " dated <strong>%s</strong> for <strong>%s</strong>, amounting to <strong>%s Php</strong> has been posted!</p>"
                     "<p>Thank you!</p>"
                     % (rec.member_id.name, rec.name,rec.date.strftime("%b %d, %Y"),rec.payment_type_id.name,rec.amount),
                partner_ids= rec.member_id.ids,
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',
                message_type='comment',
            )


    def set_type(self):
        for rec in self:
            if rec.type == 'Principal':
                rec.type = 'principal'

    @api.model
    def create_payment(self, values):
        payment_obj = self.env['loan.payment'].sudo()

        product_id = self.env['product.product'].sudo().browse(int(values.get('product_id')))

        val = {
            'product_id': values.get('product_id'),
            'description': product_id.name,
            'qty': values.get('quantity'),
            'uom': product_id.uom_id.id,
        }
        payment_id = payment_obj.sudo().create(val)

        return {
            'id': payment_id.id,
            'access_token': payment_id.sudo()._portal_ensure_token(),
        }

class LoanPaymentType(models.Model):
    _name = 'loan.payment.type'
    _description = 'Loan Account Payment'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")

