from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.tools.misc import formatLang
# from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
import odoo.addons.decimal_precision as dp
from dateutil.parser import parse
from collections import Counter
import pprint as printer
from odoo import http
# import data_migration 
# import os
import logging
_logger = logging.getLogger(__name__)


class productBuildType(models.Model):
    _name = "building.type"
    _order = "id desc"

    name = fields.Char(string="Name", required=True)

    product_id = fields.Many2one('product.product', string='Product')
    default_code = fields.Char(string="Building Code",
                       related="product_id.default_code", store=True)
    location_project = fields.Many2one('project.configs', string="Project" ,required=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validate', 'Validated'),
        ], string='State', default='draft'
        )

    reference = fields.Char('Reference ID', readonly=True)
    allocation_buildingtype = fields.Many2one('buildingtype.master', 'Allocation building Ref ID')
    prefix = fields.Char('House Number Prefix', readonly=False, required=False)
    last_gen_no = fields.Integer()
    deduct_reserve = fields.Integer('Deduct Reserved Units', default=False)
    description = fields.Text('Description')
    list_price = fields.Float('Actual Selling Price', required=False)
    is_house = fields.Boolean('Is House', default=True)
    units =fields.Float('Total no. unit sale-able', default=1.0)
    reserved_units =fields.Integer('No. of units reserved ', default=0)
    reserved_units_stored = fields.Integer('Resrv. Units', default=0, readonly=True, store= True)
    total_units = fields.Float('Total no of units', default=0, readonly=True, store= True) # , compute="caculate_total_unit")
    count_sold = fields.Float('No. of Unit Sold', store=True, compute="compute_property_details")
    count_unsold = fields.Float('No. of UnSold Unit(s)', store=True, compute="compute_property_details")
    count_total = fields.Float('Total Units', store=True, compute="compute_property_details")
    expected_sold_amount = fields.Float('Total Sold', store=True, compute="compute_property_details")
    expected_paid_amount = fields.Float('Total Amount Received', store=True, compute="compute_property_details")
    expected_outstandings_amount = fields.Float('Total Outstanding', store=True, compute="compute_property_details")
    expected_capital_amount = fields.Float('Expected Revenue', store=True, help="Total of all unit costs - (unsold amount + reserved amount)", compute="compute_property_details")
    # expected_revenue_amount = fields.Integer('Amount Received', help="Total of Uni" store=True, compute="compute_property_details")
    expected_unsold_amount = fields.Float('Total cost of unsold units', store=True, compute="compute_property_details")
    cost_of_available = fields.Float('Total cost of Available(units)', store=True, help="Sum amount of all available units", compute="compute_property_details")
    expected_diff_amount = fields.Float('Global Outstanding', store=True, help="Difference between paid amount and cost of sold units", compute="compute_property_details")
    overall_amount = fields.Float('Cost of all units', store=True, help="Sum of all sales price", compute="compute_property_details")
    building_sale_line = fields.One2many('building.type.model', 'buildingtype_id', string="Sales Line")

    @api.model
    def create(self, vals):
        #convert prefix to uppercase
        if 'prefix' in vals:
            vals['prefix'] = vals['prefix'].upper()
        rec = super(productBuildType, self).create(vals)
        return rec
 
    @api.depends('building_sale_line','total_units', 'list_price', 'reserved_units_stored')
    def compute_property_details(self):
        for rec in self:
            cnt = rec.mapped('building_sale_line').filtered(lambda s: s.mark_sold == True)
            rsv = rec.mapped('building_sale_line').filtered(lambda s: s.reserved == True)
            total_sold = len([rex.id for rex in cnt])
            reserve = len([rex.id for rex in rsv]) if rsv else rec.reserved_units
            rec.count_sold = total_sold
            rec.overall_amount = rec.total_units * rec.list_price
            rec.count_unsold = rec.total_units - (rec.reserved_units_stored + total_sold)
            rec.count_total = rec.units + rec.reserved_units
            
            total_sale_amount = sum([sale.property_sale_order_id.amount_total if sale.property_sale_order_id else sale.list_price for sale in cnt])
            cost_of_units = rec.list_price * rec.total_units
            cost_of_sold_units = rec.list_price * rec.count_sold
            cost_of_reserved_units = rec.list_price * rec.reserved_units_stored
            cost_of_unavail_units = rec.list_price * rec.count_unsold
            total_paid = sum([sale.property_sale_order_id.amount_paid if sale.property_sale_order_id else sale.amount_paid for sale in cnt])
            cost_of_avail_units = rec.list_price * rec.units

            rec.expected_sold_amount = total_sale_amount
            rec.expected_paid_amount = total_paid
            rec.expected_outstandings_amount = sum([sale.property_sale_order_id.outstanding if sale.property_sale_order_id else sale.outstanding for sale in cnt])
            rec.expected_capital_amount = cost_of_units - (cost_of_unavail_units + cost_of_reserved_units)
            rec.expected_unsold_amount = cost_of_unavail_units
            rec.expected_diff_amount = cost_of_sold_units - total_paid
            cost_of_avail_units = rec.list_price * rec.units
            rec.cost_of_available = cost_of_avail_units
	 
    def validate_building(self): 
        product_obj = self.env['product.product']
        if not self.location_project:
            raise ValidationError('Please assign a project!')
        project_id = self.env['project.configs'].search([('id', '=', self.location_project.id)], limit=1)
        if project_id:
            project_id.unit_line = [(4, self.id)]
            product = product_obj.create({'name': str(self.name).strip(),
                                        'list_price': self.list_price,
                                        # 'categ_id': self.building_type.id, 
                                        'type': "service",
                                        'taxes_id': [(6, 0, [])],
                                        'supplier_taxes_id': False,
                                        'invoice_policy': 'order',

                                        })
            self.product_id = product.id
            self.state = "validate"
            self.total_units = self.units

    def update_transactions(self):
        rec = self
        cnt = self.mapped('building_sale_line').filtered(lambda s: s.mark_sold == True)
        total_paid = sum([sale.property_sale_order_id.amount_paid if sale.property_sale_order_id else sale.amount_paid for sale in cnt])
        total_sale_amount = sum([sale.property_sale_order_id.amount_total if sale.property_sale_order_id else sale.list_price for sale in cnt])
        cost_of_units = rec.list_price * rec.total_units
        cost_of_sold_units = rec.list_price * rec.count_sold
        cost_of_reserved_units = rec.list_price * rec.reserved_units_stored
        cost_of_unsold_units = rec.list_price * rec.count_unsold
        total_paid = sum([sale.property_sale_order_id.amount_paid if sale.property_sale_order_id else sale.amount_paid for sale in cnt])
        rec.overall_amount = rec.total_units * rec.list_price
        cost_of_avail_units = rec.list_price * rec.units
        rec.expected_sold_amount = total_sale_amount
        rec.expected_paid_amount = total_paid
        rec.expected_outstandings_amount = sum([sale.property_sale_order_id.outstanding if sale.property_sale_order_id else sale.outstanding for sale in cnt])
        rec.expected_capital_amount = cost_of_units - (cost_of_unsold_units + cost_of_reserved_units)
        rec.expected_diff_amount = cost_of_sold_units - total_paid
        # rec.expected_revenue_amount = cost_of_avail_units - cost_of_sold_units
        rec.expected_unsold_amount = cost_of_unsold_units
        rec.cost_of_available = float(cost_of_avail_units)

    def generate_house_number(self):
        lines_with_house_number = self.mapped('building_sale_line').filtered(lambda self: self.house_number == False)
        if lines_with_house_number:
            for hnum in lines_with_house_number:
                lastgen = self.last_gen_no + 1
                hnum.house_number = self.prefix + str(lastgen)
                self.last_gen_no += 1
            
    def validate_reserved_building(self):
        if self.product_id:
            if self.reserved_units > 0:
                lists = []
                buildinglineObj = self.env['building.type.model']
                reserved = self.reserved_units_stored + self.reserved_units
                if self.reserved_units_stored < 1:
                    if self.reserved_units > self.units:
                        raise ValidationError('You cannot reserve more than the allocated unit')
                else:
                    if reserved > self.count_unsold:
                        raise ValidationError('You cannot reserve more than the unsold unit...')
                
                for record in range(self.reserved_units):
                    vals = ({
                        'name': self.name,
                        'product_id': self.product_id.id,
                        'default_code': self.product_id.default_code,
                        'mark_sold': False,
                        'list_price': self.list_price,
                        'reference': "Reserve for: ",
                        'reserved': True,
                        'location_project': self.location_project.id,
                        # 'discount': self.discount,
                    })
                    self.building_sale_line = [(0,0, vals)]
                self.reserved_units_stored += self.reserved_units 
                self.units = self.units - self.reserved_units
                self.reserved_units = 0
            else:
                raise ValidationError("Value to reserve must be greater than 1")
        
        else:
            raise ValidationError('Please click the Validate button first')

    def unvalidate_reserved_building(self):
        if self.deduct_reserve > 0:
            unitline = self.mapped('building_sale_line').filtered(lambda s:s.reserved == True)
            line_count = len(unitline)
            reserved = self.reserved_units_stored
            if reserved >= self.deduct_reserve:
                if self.deduct_reserve > line_count:
                    raise ValidationError("You are about to deduct a reserved unit that is greater than the allocated {}\
                        reserved units. Kindly reset the reserved units to be equal or lesser".format(line_count))
                else:
                    self.units += self.deduct_reserve
                    self.reserved_units_stored -= self.deduct_reserve
                    count_range = 0
                    while count_range < self.deduct_reserve:
                        unitline[count_range].unlink()
                        count_range += 1
                self.deduct_reserve = 0
                    
            else:
                raise ValidationError("Enter value less than the reserved unit")
        else:
            raise ValidationError("Please enter value to deduct")

    @api.constrains('name')
    def _check_fields(self):
        if self.list_price < 1:
            raise ValidationError("Note: Sales Price must be above 1")

    '''@api.multi 
    def write(self, vals):
        res = super(productBuildType, self).write(vals)
        project_id = self.env['project.configs'].search([('id', '=', self.location_project.id)], limit=1)
        if project_id:
            project_id.unit_line = [(4, self.id)]

        # if 'list_price' in vals or self.list_price:
	# if self.product_id:
            #self.product_id.lst_price = vals.get('list_price') if vals.get('list_price') else self.list_price #({'lst_price': vals.get('list_price')})
        return res'''


class productBuildTypeLine(models.Model):
    _name = "building.type.model"
    _order = "id desc"

    name = fields.Char(string="Name", required=True)
    product_id = fields.Many2one('product.product', string='Product')
    buildingtype_id = fields.Many2one('building.type', string='ID', ondelete='cascade')
    default_code = fields.Char(string="Building Code",
                       related="product_id.default_code", store=True)
    amount_paid = fields.Float(string="Amount Paid till date", compute="compute_paid_amount")
    outstanding = fields.Float(string="Outstanding Amount", compute="compute_paid_amount")
    mark_sold = fields.Boolean(string="Sold", default=False)
    reserved = fields.Boolean(string="Reserved", default=False)
    reallocate = fields.Boolean(string="Re Allocated", default=False)
    property_sale_order_id = fields.Many2one('sale.order', string="Order reference")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validate', 'Validated'),
        ], string='State', default='draft'
        )
    customer_id = fields.Many2one("res.partner",string="Purchased by")
    customer_reallocate = fields.Many2one("res.partner",string="Purchased by")
    sales_team = fields.Many2one("crm.team",
                                  string="Sales Team")
    purchase_date = fields.Datetime(string="Purchased Date",
                                    readonly=True)
    reallocation_date = fields.Datetime(string="Reallocation Date",
                                    readonly=True)
    building_type = fields.Many2one('product.category',
                                    string='Building Type',)
    is_house = fields.Boolean('Is House',
                              default=True)
    house_number = fields.Char('House Number')  # required if house number is true,
    reference = fields.Char('Reference ID', readonly=True)
    description = fields.Text('Description')
    list_price = fields.Float('Sale Price', required=True)
    discount = fields.Float('Discount(%)', required=False)

    location_project = fields.Many2one('project.configs', string="Project")
    units =fields.Integer('Remaining Units')
    count_sold = fields.Integer('Total Sold', store=True, compute="calculate_sold_details")
    count_unsold = fields.Integer('Total UnSold', store=True, compute="calculate_sold_details")
    count_total = fields.Integer('Total Unit(s)')

    @api.depends('property_sale_order_id')
    def compute_paid_amount(self):
        for rec in self:
            if rec.property_sale_order_id:
                rec.amount_paid = rec.property_sale_order_id.amount_paid
                rec.outstanding = rec.property_sale_order_id.outstanding
            else:
                rec.amount_paid = False
                rec.outstanding = False

     