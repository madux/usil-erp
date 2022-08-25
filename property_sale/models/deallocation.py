import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http

class SaleDeallocation(models.Model):
    _name = "sale.deallocation"
    _rec_name = "number"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('done', 'Done')
        ], string="state", default="draft")

    number = fields.Char('Number')
    reference = fields.Char('Payment Reference')
    property_sale_order_id = fields.Many2one('sale.order', required=True, string="SO Order reference")
    location_project = fields.Many2one('project.configs', string="Project")
    customer_id = fields.Many2one("res.partner", string="Purchased by")
    customer_reallocate = fields.Many2one("res.partner",string="Reallocate To:")
    building_line = fields.Many2many('building.type.model', string="Building Line")
    reallocation_date = fields.Datetime(string="Reallocation Date",
                                    readonly=True)

    binary_attachment = fields.Binary('Attachment')
    binary_fname = fields.Char('Attachments')

    @api.onchange('property_sale_order_id')
    def get_related_values(self):
        for rec in self:
            if rec.property_sale_order_id:
                rec.location_project = rec.property_sale_order_id.location_project.id
                rec.customer_id = rec.property_sale_order_id.partner_id.id
                
                
    @api.onchange('property_sale_order_id')
    def generate_building_lines(self):
        if self.property_sale_order_id:
            building_ids = self.env['building.type.model'].search([
                        ('reference', '=', self.property_sale_order_id.name)])
                        
            if building_ids:
                self.building_line = [(6, 0, [rex.id for rex in building_ids])]
            else:
                raise ValidationError('No building line found for these sale order')

    def action_forward_reallocation(self):
        self.state = "sent"
        self.create_new_so()

    def get_journal_id(self):
        company_id = self.env.user.company_id.id
        domain = [('type', 'in', ['bank', 'cash']), ('company_id', '=', company_id)]
        journal_id = None
        bnk_journal_id = self.env['account.journal'].sudo().search(domain, limit=1).id
        company_journal = (self.env['account.move'].sudo().with_context(company_id=company_id or self.env.user.company_id.id).default_get(['journal_id'])['journal_id'])
        if acquirer:
            journal_id = acquirer.journal_id.id
        elif bnk_journal_id:
            journal_id = bnk_journal_id
        else:
            journal_id = company_journal
        return journal_id

    def create_new_so(self):
        """
            Create new sale order for new client
             and set the old so to deallocated
        """
        sale_obj = self.env['sale.order']
        so_vals = {
            'partner_id': self.customer_reallocate.id,
            'location_project': self.property_sale_order_id.location_project.id,
            'date_order': fields.Datetime.now(),
            'sale_type': "property",
        }
        so_id = sale_obj.create(so_vals)
        for soline in self.property_sale_order_id.mapped('order_line'):
            line_description = "Reallocation of {} from {}".format(soline.product_id.name, self.property_sale_order_id.partner_id.name)
            so_line_val = {
                        'product_id': soline.product_id.id,
                        'order_id': so_id.id,
                        'name': line_description,
                        'product_uom_qty': soline.product_uom_qty,
                        'price_unit': soline.price_unit,
                        'discount': soline.discount,
                        'display_type': False
                    }
            self.env['sale.order.line'].sudo().create(so_line_val)
        self.create_invoice(so_id)
        so_id.confirm_offer()
        self.reference = so_id.id

    def create_invoice(self, sale_order):
        account_journal = self.env['account.journal'].sudo()
        account_payment_obj = self.env['account.payment'].sudo()
        # Confirm sale order, create invoice and post the invoice
        sale_order.action_confirm()
        inv = sale_order.sudo()._create_invoices()[0]
        inv.post()
        # Auto Validated the invoice
        # inv.action_invoice_open()
        # Default company payment journal for sales
        # if payment_data:
        #     sale_payment_method = self.env['account.payment.method'].sudo().search(
        #         [('code', '=', 'manual'), ('payment_type', '=', 'inbound')], limit=1)
        #     journal_id = self.get_journal_id()
        #     payment_method = account_journal.browse([journal_id]).inbound_payment_method_ids[0].id if account_journal.browse(
        #         [journal_id]).inbound_payment_method_ids else sale_payment_method.id if sale_payment_method else 1
        #     acc_values = {
        #         'invoice_ids': [(6, 0, [inv.id])],
        #         'amount': inv.amount_residual_signed,
        #         'communication': '[Payment REF: {}, SO REF: {}]'.format(payment_data.get('order_id'), sale_order.name),
        #         'payment_type': 'inbound',
        #         'partner_type': 'customer',
        #         'journal_id': journal_id,
        #         'payment_method_id': payment_method,
        #         'partner_id': sale_order.partner_id.id or partner_id,
        #     }
        #     payment = account_payment_obj.create(acc_values)
        #     payment.post()

    # def create_invoice(self):
    #     account_obj = self.env['account.move']
    #     invoice_lines = self.env['account.move.line']
    #     journal_id = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
    #     invoice_obj = account_obj.create({
    #             'partner_id': self.customer_reallocate.id,
    #             'journal_id': journal_id.id,
    #             'account_id': self.customer_reallocate.property_account_payable_id.id if self.customer_reallocate else 13,# inv.partner_id.property_account_payable_id.id, 
    #             'branch_id': self.env.user.branch_id.id, # if not self.env.user.branch_id.id, 
    #             'date_invoice': datetime.today(),
    #             'type': 'out_invoice', 
    #             'invoice_line_ids': [(0, 0, {
    #                                 # 'product_id': rex.product_id.id,
    #                                 'price_unit': 100000,
    #                                 'name': "Charge for Reallocation",
    #                                 'account_id': invoice_lines.with_context({'journal_id': journal_id.id, 'type': 'in_invoice'})._default_account(),
    #                                 'quantity': 1.0,
                                    
    #                                 })]
    #         })
    #     self.reference = invoice_obj.id
    
    def see_invoice(self):
        if self.reference:
            search_view_ref = self.env.ref(
                'account.view_account_invoice_filter', False)
            form_view_ref = self.env.ref('account.view_move_form', False)
            tree_view_ref = self.env.ref('account.view_out_invoice_tree', False)
            return {
                'domain': [('id', '=', int(self.reference))],
                'name': 'Invoices',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
                'search_view_id': search_view_ref and search_view_ref.id,
            }
    
    def see_sale_order_reference(self):
        if self.reference:
            search_view_ref = self.env.ref(
                'sale.sale_order_view_search_inherit_sale', False)
            form_view_ref = self.env.ref('sale.view_order_form', False)
            tree_view_ref = self.env.ref('sale.view_order_tree', False)
            return {
                'domain': [('id', '=', int(self.reference))],
                'name': 'Sales',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
                'search_view_id': search_view_ref and search_view_ref.id,
            }

    def action_reallocation(self):
        self.state = "done"
        self.reallocation_date = datetime.now()
        for rec in self.building_line:
            rec.reallocate = True
            rec.customer_reallocate = self.customer_reallocate.id
            rec.reallocation_date = datetime.now()
         
    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].next_by_code('sale.deallocation')
        return super(SaleDeallocation, self).create(vals)