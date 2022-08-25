# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError,ValidationError


class PropertyProductChangeQuantity(models.TransientModel):
    _name = "property.change.product.qty"
    _description = "Change Quantity"

    building_id = fields.Many2one('building.type.model', 'Item', required=True)
    new_quantity = fields.Float(
        'New Quantity on Hand', default=1, required=True,
        help='Setting this quantity will update the available units in the select building.')

    
    @api.constrains('new_quantity')
    def check_new_quantity(self):
        if (building_id.qty_available + self.new_quantity) < 0:
            raise ValidationError(_('Quantity cannot be negative.'))

    def change_product_qty(self):
        """ Changes the Building available quantity. """
        Inventory = self.env['building.type.model'].browse([self.building_id.id])
        if Inventory:
            Inventory.qty_available += self.new_quantity
        return {'type': 'ir.actions.act_window_close'}
