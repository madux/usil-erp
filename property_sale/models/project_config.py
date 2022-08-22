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
 

class ProjectConfiguration(models.Model):
    _name = "project.configs"

    @api.model
    def create(self, vals):
        vals['name'] = vals.get('name').strip()
        vals['address'] = vals.get('address').strip()

        if self.env['project.configs'].search([('name', '=ilike',vals.get('name').strip()),
        ('address', '=ilike',vals.get('address').strip())]):
            pass
            # raise ValidationError('Project name with Address Already Exists')
        return super(ProjectConfiguration, self).create(vals)

    # def write_to_building(self, buildid, unsold, unit_remain, sold, total_units, listprice, project, house_prefix):
    #     build_obj = self.env['building.type'].browse([buildid])
    #     build_obj.write({
    #                     'count_unsold': int(unit_remain) if unit_remain > 0 else 0,
    #                     'units': int(unit_remain) if unit_remain > 0 else 0,
    #                     'count_sold': int(sold) if sold > 0 else 0,
    #                     'list_price': listprice if listprice > 0.0 else 1.0, 
    #                     'location_project': project,
    #                     'total_units': total_units,
    #                     'prefix': house_prefix if house_prefix else 'NaN',
    #                     'state': "validate",
    #                     'last_gen_no': int(sold) if sold > 0 else 0,
                    
    #                 })
                       
    # def create_discount(self, consentfee, offerprice):
    #     discounts = 0
    #     if consentfee > 1:
    #         discounts = consentfee * 100 / offerprice 
    #     else:
    #         discounts = 0
    #     return discounts
        
    # @api.multi
    # def migration_project(self): 
    #     payment_plan_obj = self.env['account.payment.term']
    #     projects = self.env['projectsite.master'].search([])
    #     custom_payment_term = payment_plan_obj.search([('name', '=', 'custom')], limit=1)
    #     for rec in projects:
    #         project_id = self.env['project.configs'].create({
    #                                         'name': rec.name.name,
    #                                         'address': rec.address if rec.address else rec.name.name,
    #                                         'phase': 1, 
    #                                         'payment_term_id': custom_payment_term.id,
    #                                         'project_site': rec.id,
    #                                     })

    # def building_type_migration(self):
    #     buildings = self.env['buildingtype.master'].search([])
    #     build_obj = self.env['building.type']
    #     for rec in buildings:
    #         product_search = self.env['product.product'].search([('name', '=', rec.name)], limit=1)
    #         product_id = product_search.id if product_search else self.env['product.product'].create({
    #                     'name': rec.name,
    #                     'list_price': 1.0,
    #                     'taxes_id': False,
    #                     'supplier_taxes_id': False,
    #                 }).id
    #         build_id = build_obj.create({
    #             'name': rec.name,
    #             'allocation_buildingtype': rec.id,
    #             'product_id': product_id,
    #             # 'location_project': project_id,
    #             # 'prefix': house_prefix if house_prefix else 'NaN',
    #             # 'last_gen_no': int(sold) if sold > 0 else 0,
    #             # 'total_units': int(total_units) if total_units > 0 else 0,
    #             # 'count_unsold': int(unit_remain) if unit_remain > 0 else 0,
    #             # 'units': int(unit_remain) if unit_remain > 0 else 0,
    #             # 'count_sold': int(sold) if sold > 0 else 0,
    #             'list_price': 1.0, 
    #         }).id

    
    def get_lists_of_projects(self, limit=20):
        ''' Fetch the list of project
        '''
        projects = http.request.env['project.configs'].sudo().search([], limit=limit)
        if projects:
            list_proj = [projs.name for projs in projects]
            return list_proj
         
    def get_lists_of_projects_date_filter(self, project_name, datefrom, dateto, limit=20):
        ''' Fetch the list of project by date
        '''
        projects = http.request.env['building.type.model'].sudo().search([('purchase_date', '>=', datefrom ),('purchase_date', '<=', dateto)], limit=limit)
        if projects:
            list_proj = [projs.name for projs in projects]
            return list_proj

    def summary_project_report(self, project_name=None, datefrom=None, dateto=None, sale=None, summary_report=None):
        domain = []
        if not sale or sale=="All":
            if datefrom and dateto and not project_name:
                domain = [('create_date','>=', datefrom ),
                    ('create_date','<=', dateto)]
                
            elif project_name and datefrom and dateto:
                domain = [('location_project.name', '=', project_name),
                ('create_date', '>=', datefrom ),('create_date', '<=', dateto)]

            elif project_name: 
                domain = [('location_project.name', '=', project_name)]

            else:
                domain = []

        plotted_category = ['Actual Sale', 'Unsold', 'Reserved', 'Outstanding', 'No Discount Sales']
        plot_category_values = [0, 0, 0, 0, 0]
        total_amount_sold = 0
        total_amount_unsold = 0
        total_amount_reserved = 0

        sold_units = 0
        unsold_units = 0
        reserved_units = 0
        
        difference_in_sales = 0
        outstanding_amount = 0
        total_without_discount = 0
        total_with_discount = 0
        total_percentage_discount = 0
        sold_without_discount_units = 0
        sold_with_discount_units = 0
        total_amount_paid = 0
        total_sellable = 0
        total_units = 0
        total_actual_sale = 0 
        percent_disc = 0

        buildings = http.request.env['building.type'].sudo().search(domain, limit=100)
        if buildings:
            for records in buildings:
                total_units += (records.units + records.reserved_units)
                unsold_units += (records.count_unsold)
                total_sellable += ((records.units + records.reserved_units) * records.list_price)
                for build_sale_line in records:
                    sold = build_sale_line.mapped('building_sale_line').filtered(lambda sold: sold.mark_sold == True)
                    unsold = build_sale_line.mapped('building_sale_line').filtered(lambda un: un.mark_sold == False and un.reserved == False)
                    reserved = build_sale_line.mapped('building_sale_line').filtered(lambda rsv: rsv.reserved == True)
                    discount = build_sale_line.mapped('building_sale_line').filtered(lambda sold: sold.mark_sold == True and sold.discount ==True)
                    nodiscount = build_sale_line.mapped('building_sale_line').filtered(lambda sold: sold.mark_sold == True and sold.discount ==True)
                    
                    sold_units += len(sold)
                    # unsold_units += len(unsold)
                    reserved_units += len(reserved)

                    total_amount_sold += sum([so.property_sale_order_id.amount_total for so in sold])
                    total_amount_unsold += sum([un.list_price for un in unsold])
                    total_amount_reserved += sum([rsv.list_price for rsv in reserved])
                    # difference_in_sales = sum([so.list_price for so in sold]) - sum([so.property_sale_order_id.amount_total for so in sold])
                    outstanding_amount += sum([so.property_sale_order_id.outstanding for so in sold])
                    total_with_discount += sum([dis.list_price for dis in discount])
                    total_percentage_discount += sum([dis.discount for dis in discount])
                    sold_with_discount_units += len(discount)
                    sold_without_discount_units += len(nodiscount)
                    total_without_discount += sum([dis.list_price for dis in nodiscount])
                total_actual_sale += (total_sellable - total_amount_sold)
            plot_category_values = [
                total_amount_sold, total_amount_unsold, total_amount_reserved,
                outstanding_amount, total_without_discount
                ]
        return {
            'plot_category': plotted_category,
            'plot_category_values': plot_category_values,
            'total_amount_sold': total_amount_sold,
            'total_amount_unsold': total_amount_unsold,
            'total_amount_reserved': total_amount_reserved,
            'sold_units': sold_units,
            'unsold_units': unsold_units,
            'reserved_units': reserved_units,
            'total_units': total_units,# sold_units + unsold_units + reserved_units,
            'outstanding_amount': outstanding_amount,
            'total_without_discount': total_without_discount,
            'sold_without_discount_units': sold_without_discount_units,
            'total_sellable': total_sellable, # total_amount_sold + total_amount_unsold,
            'received_percentage': (total_amount_paid * 100) / total_amount_sold if total_amount_paid > 1 else 0,
            'received_paid': total_amount_sold,
            'total_percentage_discount': total_percentage_discount,
            'total_actual_sale_diff': total_actual_sale
        }

    def dynamic_projects_rendering(self, project_name=None, datefrom=None, dateto=None, sale=None, summary_report=None):
        ''' Fetch the list of project
        '''
        domain = []
        
        if not sale or sale=="All":
            if datefrom and dateto and not project_name:
                domain = [('create_date','>=', datefrom ),
                    ('create_date','<=', dateto)]
                
            elif project_name and datefrom and dateto:
                domain = [('location_project.name', '=', project_name),
                ('create_date', '>=', datefrom ),('create_date', '<=', dateto)]

            elif project_name: 
                domain = [('location_project.name', '=', project_name)]

            else:
                domain = []

        if sale=="NoDatefilter":
            if datefrom and dateto and not project_name:
                domain = [('create_date', '>=', datefrom ),('create_date', '<=', dateto)]
            elif project_name and datefrom and dateto:
                domain = [
                    ('location_project.name', '=', project_name),
                    ('create_date', '>=', datefrom ),
                    ('create_date', '<=', dateto)
                    ]
            elif project_name:  
                domain = [('location_project.name', '=', project_name)]
            else:
                domain = []

        if sale == 'Reserved':
            if datefrom and dateto and not project_name:
                domain = [
                    ('reserved', '=', True),
                    ('create_date','>=', datefrom ),
                    ('create_date','<=', dateto)
                    ]

            elif project_name and datefrom and dateto:
                domain = [
                    ('reserved', '=', True),
                    ('location_project.name', '=', project_name),
                    ('create_date','>=', datefrom ),
                    ('create_date','<=', dateto)
                    ]

            elif project_name:
                domain = [('location_project.name', '=', project_name),('reserved', '=', True)]

            else:
                domain = [('reserved', '=', True),]

        if sale == 'Sold':
            if datefrom and dateto and not project_name:
                domain = [
                    ('mark_sold', '=', True),
                    ('purchase_date', '>=', datefrom ),
                    ('purchase_date', '<=', dateto)
                    ]

            elif project_name and datefrom and dateto:
                domain = [
                    ('mark_sold', '=', True),
                    ('location_project.name', '=', project_name),
                    ('purchase_date', '>=', datefrom ),
                    ('purchase_date', '<=', dateto)
                    ]

            elif project_name:
                domain = [('location_project.name', '=', project_name),('mark_sold', '=', True),]

            
            else:
                domain = [('mark_sold', '=', True),]

        if sale == 'UnSold':
            if datefrom and dateto and not project_name:
                domain = [
                    ('reserved', '!=', True),
                    ('mark_sold', '=', False),
                    ('create_date','>=', datefrom ),
                    ('create_date','<=', dateto)
                    ]

            elif project_name and datefrom and dateto:
                 
                domain = [
                    ('reserved', '!=', True),
                    ('mark_sold', '!=', True),
                    ('location_project.name', '=', project_name),
                    ('create_date','>=', datefrom ),
                    ('create_date','<=', dateto)
                    ]

            elif project_name:
                 
                domain = [('location_project.name', '=', project_name), ('reserved', '!=', True),
                    ('mark_sold', '!=', True)]
            
            else:
                domain = []
        
        buildings = http.request.env['building.type.model'].sudo().search(domain, limit=100)
        if buildings:
            if not summary_report:
                list_buildings = [build.name for build in buildings]
                amount_unsold = [build.list_price for build in buildings]
                amount_sold = [build.property_sale_order_id.amount_total for build in buildings]

                # return list_buildings
                return {
                    'list_buildings': list_buildings,
                    'list_sold': amount_sold,
                    'list_unsold': amount_unsold
                }

            else:
                 
                total_amount_reserved = 0
                total_amount_unsold = 0
                total_amount_sold = 0
                sold_units = 0
                unsold_units = 0
                reserved_units = 0
                outstanding_amount = 0
                total_without_discount = 0
                sold_without_discount_units = 0
                total_amount_paid = 0
                for build in buildings:

                    if build.reserved == True:
                        total_amount_reserved += build.list_price
                        reserved_units += 1

                    if build.mark_sold == False and build.reserved == False:
                        total_amount_unsold += build.list_price
                        unsold_units += 1

                    if build.mark_sold == True:
                        total_amount_sold += build.property_sale_order_id.amount_total
                        outstanding_amount += build.property_sale_order_id.outstanding
                        sold_units += 1
                        total_amount_paid += build.property_sale_order_id.amount_paid

                    if build.mark_sold == True and build.discount == False:
                        total_without_discount += build.property_sale_order_id.amount_total
                        sold_without_discount_units += 1

                plotted_category = ['Actual Sale', 'Unsold', 'Reserved', 'Outstanding', 'No Discount Sales']
                plot_category_values = [
                    total_amount_sold, 
                    total_amount_unsold, 
                    total_amount_reserved, 
                    outstanding_amount, 
                    total_without_discount, 
                    ]
                return {
                    'plot_category': plotted_category,
                    'plot_category_values': plot_category_values,
                    'total_amount_reserved': total_amount_reserved,
                    'total_amount_unsold': total_amount_unsold,
                    'total_amount_sold': total_amount_sold,
                    'sold_units': sold_units,
                    'total_units': sold_units + unsold_units + reserved_units,
                    'unsold_units': unsold_units,
                    'reserved_units': reserved_units,
                    'outstanding_amount': outstanding_amount,
                    'total_without_discount': total_without_discount,
                    'sold_without_discount_units': sold_without_discount_units,
                    'total_sellable': total_amount_sold + total_amount_unsold,
                    'received_percentage': (total_amount_paid * 100) / total_amount_sold,
                    'received_paid': total_amount_paid
                }
        else:
            return {
                'list_buildings': [],
                'list_sold': [],
                'list_unsold': []
            }

    name = fields.Char(string="Name")
    phase = fields.Char(string="Phase")
    color = fields.Integer('Color')
    address = fields.Text(string="Address")
    project_site = fields.Many2one('projectsite.master', string="Migration Reference ")
    payment_term_id = fields.Many2one('account.payment.term', 
                                      string='Payment Terms',
                                      oldname='payment_term')

    unit_line = fields.Many2many('building.type', string="Buildings",)
    # related_unit_ids = fields.One2many('building.type', 'location_project_id', string="Related Buildings")
    total_unit = fields.Integer(string="Total Units",
                                compute="total_house_units")
    total_sold = fields.Integer(string="Sold Units",
                                compute="total_house_units")
    total_remain = fields.Integer(string="Remaining",
                                  compute="total_house_units")

    @api.depends('unit_line')
    def total_house_units(self):
        for rec in self:
            total_units = 0
            total_sold = 0
            total_unsold = 0
            if rec.unit_line:
                for unit in rec.unit_line:
                    total_units += unit.units
                    total_sold += unit.count_sold
                    total_unsold += unit.count_unsold
                # raise ValidationError(total_sold)
                rec.total_unit = total_units 
                rec.total_sold = total_sold
                rec.total_remain = total_unsold
            else:
                rec.total_unit = 0.0 
                rec.total_sold = 0.0
                rec.total_remain = 0.0

        # for rec in self:
        #     # total_sold_units = 0
        #     # unit_lines = rec.mapped("unit_line")
        #     rec.total_unit = len(unit_lines)
        #     for unit in unit_lines:
        #         total_sold_units += len(unit.mapped('building_sale_line').filtered(lambda s: s.mark_sold ==  True))

        #     rec.total_sold = total_sold_units
        #     if rec.total_sold > 0:
        #         rec.total_remain = rec.total_unit - rec.total_sold
        #     else:
        #         rec.total_remain = False

    def _get_action(self, action_xmlid, types=None):
        # used for kanban view display
        # action = self.env.ref(action_xmlid).read()[0]
        
        tree_view_ref = self.env.ref(action_xmlid, False)
        form_view_ref = self.env.ref('property_sale.building_model_form_view_3', False)
        domain = None
        if types == "all":
            '''Display all records of the project'''
            domain = [('id', '=', [tec.id for xec in self.mapped('unit_line') for tec in xec.mapped('building_sale_line')])]

        elif types == "sold":
            '''Display all sold records of the project'''
            domain = [('id', '=', [tec.id for xec in self.mapped('unit_line') for tec in xec.mapped('building_sale_line').filtered(lambda x: x.mark_sold == True)])]
        elif types == "remaining":
            '''Display all remaining records of the project'''
            domain = [('id', '=', [tec.id for xec in self.mapped('unit_line') for tec in xec.mapped('building_sale_line').filtered(lambda x: x.mark_sold == False and x.reserved == False)])]

        return {
            'domain': domain,
            'name': 'Invoices',
            'res_model': 'building.type.model',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_ref.id, 'tree'),(form_view_ref.id, 'form')],
            # 'search_view_id': search_view_ref and search_view_ref.id,
        } 

    def get_the_action_record(self):
        return self._get_action('property_sale.property_products_treex', "all")

    def get_the_sold_record_action(self):
        return self._get_action('property_sale.property_products_treex', "sold")

    def get_remaining_record_action(self):
        return self._get_action('property_sale.property_products_treex', "remaining")

    def get_the_sale_action_record(self):
        return self._get_action('property_sale.action_orders_property')

    def get_reference_record(self):
        reference_id = self.env['project.configs'].search([('id', '=', self.id)])
        if not reference_id:
            raise ValidationError('There is no related Pickings Created.')
        resp = {
            'type': 'ir.actions.act_window',
            'name': _('Reference'),
            'res_model': 'project.configs',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'res_id': reference_id.id
        }
        return resp

