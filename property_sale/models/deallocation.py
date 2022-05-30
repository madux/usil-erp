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
    building_line = fields.Many2many('building.type.model', string="Building Line", compute="compute_lines")
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
                
    @api.depends('property_sale_order_id')
    def compute_lines(self):
        if self.property_sale_order_id:
            building_ids = self.env['building.type.model'].search([
                        ('reference', '=', self.property_sale_order_id.name)])
            if building_ids:
                self.building_line = [(6, 0, [rex.id for rex in building_ids])]
            else:
                self.building_line = False

    def action_forward_reallocation(self):
        self.state = "sent"
        self.create_invoice()

    def create_invoice(self):
        account_obj = self.env['account.move']
        invoice_lines = self.env['account.move.line']
        journal_id = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        invoice_obj = account_obj.create({
                'partner_id': self.customer_reallocate.id,
                'journal_id': journal_id.id,
                'account_id': self.customer_reallocate.property_account_payable_id.id if self.customer_reallocate else 13,# inv.partner_id.property_account_payable_id.id, 
                'branch_id': self.env.user.branch_id.id, # if not self.env.user.branch_id.id, 
                'date_invoice': datetime.today(),
                'type': 'out_invoice', 
                'invoice_line_ids': [(0, 0, {
                                    # 'product_id': rex.product_id.id,
                                    'price_unit': 100000,
                                    'name': "Charge for Reallocation",
                                    'account_id': invoice_lines.with_context({'journal_id': journal_id.id, 'type': 'in_invoice'})._default_account(),
                                    'quantity': 1.0,
                                    
                                    })]
            })
        self.reference = invoice_obj.id
    
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

    def action_reallocation(self):
        account_ref = self.env['account.move'].search([('id', '=', int(self.reference))], limit=1)
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