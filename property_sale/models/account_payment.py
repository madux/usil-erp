import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http


class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    narration_text = fields.Text('Note')
    reference = fields.Char('Reference ID', readonly=True)
    is_property = fields.Boolean("Is Property", default=False)

    banker = fields.Many2one('res.bank', string='Bank')
    state = fields.Selection([('first_draft', 'Draft'), ('draft', 'In Progress'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled'),('cancelled', 'Cancelled'),], 
    readonly=True, default='first_draft', copy=False, string="Status")
    modes_payment = fields.Selection([
                                    ('POS', 'POS'),
                                    ('Cheque', 'Cheque'),
                                    ('Bank-Draft', 'Bank-Draft'),
                                    ('Transfer', 'Transfer')],
                                    'Mode of Payment',
                                    index=True,
                                    default='POS',
                                    required=False,
                                    readonly=False,
                                    copy=False,
                                    track_visibility='always')

    def set_draft_prop(self):
        self.state = "first_draft"

    def write(self, vals):
        if 'amount' in vals:
            sale_obj = self.env['sale.order'].sudo().search([('name','=', self.reference)], limit=1)
            if sale_obj and sale_obj.state != 'first_draft':
                amountdiff = self.amount - float(vals.get('amount'))
                amount_modified = sale_obj.amount_paid - amountdiff
                sale_obj.sudo().write({'amount_paid': amount_modified})
                sale_obj.sudo().update_transactions()
        return super(AccountPayment, self).write(vals)

    def sent_to_post(self):
        allocated = False
        if self.reference:
            sale_obj = self.env['sale.order'].sudo().search([('name','=', self.reference)], limit=1)
            if sale_obj:
                amount = sale_obj.amount_paid + self.amount
                prop_payment_count = sale_obj.prop_payment_count + 1
                percent_amount = 0.3 * sale_obj.amount_total
                if amount > percent_amount:
                    allocated = True
                sale_obj.sudo().write({'amount_paid': amount,
                                'prop_payment_count': sale_obj.prop_payment_count + 1,
                                'payment_idss': [(4, self.id)],
                                'sale_status': 'Allocated' if allocated else 'Sold',
                                'state': 'sale',
                            })
                sale_obj.sudo().update_transactions()
                buildingline = self.env['building.type.model'].sudo().search([('property_sale_order_id', '=', sale_obj.id)], limit=1)
                if not buildingline:
                    sale_obj.sudo().confirm_offer()
                self.sudo().write({'state': 'draft'})
            else:
                raise ValidationError('No Sale order reference found for the payment.')
        else:
            self.sudo().write({'state': 'draft'})
    
    def cancel(self):
        for rec in self:
            if rec.state == "draft":
                if rec.reference:
                    sale_obj = self.env['sale.order'].sudo().search([('name','=', rec.reference)], limit=1)
                    if sale_obj:
                        amount_deduct = sale_obj.amount_paid - rec.amount
                        percent_amount = 0.3 * sale_obj.amount_total
                        # sale_obj.amount_paid = amount_deduct
                        sale_obj.sudo().write({
                                        'amount_paid': amount_deduct
                                    })
                        if sale_obj.amount_paid > 0:
                            if sale_obj.amount_paid < percent_amount:
                                sale_obj.sudo().write({
                                        'sale_status': "Sold"
                                    })
                        else:
                            sale_obj.sudo().update({'sale_status' :"Draft", 'state': 'draft'})
                            buildingline = self.env['building.type.model'].sudo().search([('property_sale_order_id', '=', sale_obj.id)], limit=1)
                            if buildingline:
                                buildingtype = self.env['building.type'].sudo().browse([buildingline.buildingtype_id.id])
                                if buildingtype:
                                    buildingtype.sudo().write({
                                        'last_gen_no': buildingtype.last_gen_no - 1 if buildingtype.last_gen_no >= 0 else 0,
                                        'units': buildingtype.units + 1
                                    })
                                else:
                                    raise ValidationError('No Building type record found')
                                buildingline.sudo().unlink()
                            else:
                                raise ValidationError('No unit line found')
                        sale_obj.sudo().write({
                            'prop_payment_count': sale_obj.prop_payment_count - 1
                                    })
                        # sale_obj.prop_payment_count -= 1
                        payment_lines = sale_obj.mapped('payment_idss').filtered(lambda self: self.id == rec.id)
                        if payment_lines:
                            sale_obj.sudo().write({
                                'payment_idss': [(3, payment_lines.id)]
                            }) #payment_lines.unlink()
                        else:
                            raise ValidationError('No payment found on sales record to delete')
            else:
                for move in rec.move_line_ids.mapped('move_id'):
                    if rec.invoice_ids:
                        move.line_ids.remove_move_reconcile()
                    move.button_cancel()
                    move.unlink()
                rec.cancel_allocations()
                
            rec.state = 'cancelled'

    def cancel_allocations(self):
        for rec in self:
            if rec.reference:
                sale_obj = self.env['sale.order'].search([('name','=', rec.reference)], limit=1)
                if sale_obj:
                    amount_deduct = sale_obj.amount_paid - rec.amount
                    percent_amount = 0.3 * sale_obj.amount_total
                    # sale_obj.amount_paid = amount_deduct
                    sale_obj.sudo().write({
                                        'amount_paid': amount_deduct
                                    })
                    if sale_obj.amount_paid > 0:
                        if sale_obj.amount_paid < percent_amount:
                            sale_obj.sudo().write({
                                        'sale_status': "Sold"
                                    })
                            # sale_obj.sale_status == "Sold"
                    else:
                        sale_obj.update({'sale_status' :"Draft", 'state': 'draft'})
                        buildingline = self.env['building.type.model'].search([('property_sale_order_id', '=', sale_obj.id)], limit=1)
                        if buildingline:
                            buildingtype = self.env['building.type'].sudo().browse([buildingline.buildingtype_id.id])
                            if buildingtype:
                                buildingtype.sudo().write({
                                        'last_gen_no': buildingtype.last_gen_no - 1 if buildingtype.last_gen_no >= 0 else 0,
                                        'units': buildingtype.units + 1
                                    })
                                # buildingtype.last_gen_no -= 1 if buildingtype.last_gen_no >= 0 else 0
                                # buildingtype.units += 1
                            else:
                                raise ValidationError('No Building type record found')

                            buildingline.sudo().unlink()
                        else:
                            raise ValidationError('No unit line found')
                    # sale_obj.prop_payment_count -= 1
                    sale_obj.sudo().write({
                            'prop_payment_count': sale_obj.prop_payment_count - 1
                                    })

                    payment_lines = sale_obj.mapped('payment_idss').filtered(lambda self: self.id == rec.id)
                    if payment_lines:
                        rec.write({
                            'payment_idss': [(3, payment_lines.id)]
                        }) #payment_lines.unlink()
                    else:
                        raise ValidationError('No payment found on sales record to delete')

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        allocated = False
        for rec in self:
            if rec.reference:
                sale_obj = self.env['sale.order'].search([('name','=', rec.reference)])
                if sale_obj:
                    amount = sale_obj.amount_paid + rec.amount
                    prop_payment_count = sale_obj.prop_payment_count + 1
                    percent_amount = 0.3 * sale_obj.amount_total
                    if amount > percent_amount:
                        allocated = True
                    sale_obj.write({
                        # 'amount_paid': amount,
                        'prop_payment_count': prop_payment_count,
                        # 'payment_idss': [(4, self.id)],
                        'sale_status': 'Allocated' if allocated else 'Sold',
                        'state': 'sale',
                    })
                
                else:
                    raise ValidationError('No Sale order reference found for the payment.')
            
            self.state = "posted"
            # raise ValidationError('No reference')
        return res           

