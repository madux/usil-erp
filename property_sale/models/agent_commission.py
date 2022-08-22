from odoo import models, fields, api, _
from odoo.exceptions import except_orm, ValidationError
import time
from datetime import datetime, timedelta
 

class PayAgentCommission(models.Model):
    _name = 'pay.agent2'
    _rec_name = "agent_name"

    agent_name=fields.Many2one('res.partner','Agent')
    # payment_invoice = fields.Many2one('account.invoice', string='Invoice ID',required =False, domain="[('state', '=', 'open')]")
    sale_order = fields.Many2one('sale.order', required= True, string="Project/House")
    offer_amount=fields.Float('Offer Price', default='1.0',compute="_get_sales_amount")
    house_num= fields.Char('House Number')
    project= fields.Many2one('project.configs', string="Project")
    discount=fields.Float('Total Discount', default='0.0')

    commission_amount=fields.Float('Commission To Pay', required=True,compute="compute_agent_commission")
    unit = fields.Float('Unit(s)')
    branch_id = fields.Many2one('usl.branch',string="Branch",default=lambda self:self.env.user.branch_id.id)
    agent_commission=fields.Float('Agent Commission(%)', default='2.0')

    vat_amount =fields.Float('VAT(%)', default='5.0')
    user = fields.Many2one('res.users',readonly=True, default=lambda self:self.env.user.id, string='User')

    users_followers = fields.Many2many('res.users', string='Add followers')
    account_journal = fields.Many2one('account.journal', string='Journal ID',
            required=True, readonly=False,
            )

    advance_account = fields.Many2one('account.account', 'Account', related='account_journal.default_debit_account_id')#, required=True,default=lambda self: self.env['account.account'].search([('name', '=', 'Account Receivable')], limit=1))
    date = fields.Date('Date', required=True)
    payment_history_plot = fields.Many2many('account.payment','All Payment History')
    state = fields.Selection([('draft', 'Draft'),
                            ('gm', 'General Manager'),
                            ('account', 'Account'),
                            ('md', 'Managing Director'),
                            ('post', 'Posted'),
                            ('done', 'Paid'),
                            ('cancel', 'Cancelled')], string='Status', index=True, readonly=True, track_visibility='onchange', copy=False, default='draft',
            )

    @api.onchange('sale_order')
    def _get_sales_units(self):
        if self.project:
            self.unit = sum(self.sale_order.mapped('order_line.amount_total').product_uom_qty)
    
    @api.depends('sale_order')
    def _get_sales_amount(self):
        if self.project:
            self.offer_amount = self.sale_order.amount_total
        else:
            self.offer_amount = False

    @api.depends('offer_amount','discount','agent_commission')
    def compute_agent_commission(self):
        for rec in self:
            get_actual = rec.offer_amount - rec.discount
            main_actual = (rec.agent_commission) /100 * get_actual
            total = main_actual * (rec.vat_amount /100)
            rec.commission_amount = total

    # ,compute="get_offer_payment_history")
    
    # @api.depends('payment_invoice')
    # def get_offer_payment_history(self):
    #     for rec in self:
    #         lists = []
    #         for inv_line in rec.payment_ids:
    #             lists.append(inv_line.id)
    #         rec.payment_history_plot = [(6,0,lists)]

    @api.depends('branch_id')
    def domain_restrictor(self):
        get_sales_model=self.env['sale.order'].search([('branch_id','=',self.branch_id.id),('location_project', '=', self.project.id)])
        domain = {}
        lists =[]
        for rec in get_sales_model:
            lists.append(rec.id)
            domain ={'sale_order':[('id','in',lists)]}
        return {'domain':domain}


    # @api.depends('payment_invoice')
    # def _get_invoice_fieldsx(self):
    #     invoice_lines = self.payment_invoice
    #     if invoice_lines:
    #         for inv_line in invoice_lines.invoice_line_ids:
    #             total = inv_line.price_subtotal
    #             self.offer_amount += total
     

    def send_to_GM(self):
        self.write({'state': 'gm'})#


    def send_GM_to_account(self):
        self.write({'state': 'account'})#

    def send_account_to_MD(self):
        self.write({'state': 'md'})#

    def Send_MD_to_post(self):
        self.write({'state': 'post'})

    def Send_Account_to_Pay(self):
        self.button_pay()

    def button_pay(self):
        for rec in self:
            # ref_num = rey.payment_invoice.number
            # acm = self.env['account.payment.method'].create({'payment_type':'inbound','name':ref_num,'code': ref_num})
            # payment_methods = and self.journal_id.outbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
            # payment_method_id = payment_methods and payment_methods[0] or False
            payment_method_id = self.env['account.payment.method'].search([('payment_type', '=', 'outbound')], limit=1)
            payment_data = {
                            'amount': rec.commission_amount, 
                            'payment_date':rec.date,
                            'partner_type': 'vendor',
                            'payment_type': 'outbound',
                            'partner_id': rec.agent_name.id,
                            'journal_id':rec.account_journal.id,
                            'communication': "AGT-%s" % rec.sale_order.name,
                            'payment_method_id': payment_method_id.id;#values.get('advance_account')
            }
            payment_model = self.env['account.payment'].create(payment_data)
            rec.write({'state': 'done', 'payment_history_plot': [(6, 0, [payment_model.id])]})

    def cancel(self):
        self.write({'state': 'cancel'})

    def setdraft(self):
        self.write({'state': 'draft'})
