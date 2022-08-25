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
import logging
_logger = logging.getLogger(__name__)
 

class PropertyReport(models.Model):
    _name = "property.report"
    _rec_name = "number"

    report_type = fields.Selection([('all', 'All Project'),('single', 'Single Project')], string="Type")
    number = fields.Integer('Number', default=0)
    report_by = fields.Selection([('sales', 'Sales'),('gen', 'General report')], string="View BI by") 
    datefrom = fields.Datetime('Date From:')
    dateto = fields.Datetime('Date To:')
    color = fields.Integer('Color')

    project_ids = fields.Many2many('project.configs', string="Projects", required=True)
    buildingtype = fields.Many2many('building.type.model',compute="compute_projects", string="Buildings/Unit(s)")

    total_unit_sold = fields.Float('Total Units Sold', compute="compute_projects",readonly=True, store=True)
    total_unit_unsold = fields.Float('Total Units UnSold',compute="compute_projects", readonly=True, store=True)
    total_unit_reserved = fields.Float('Total Units Reserved', compute="compute_projects", readonly=True, store=True)
    total_amount_sold = fields.Float('Total Units Sold', compute="compute_projects", readonly=True, store=True)
    total_amount_unsold = fields.Float('Total Amount UnSold',compute="compute_projects", readonly=True, store=True)
    total_amount_reserved = fields.Float('Total Amount Reserved',compute="compute_projects", readonly=True, store=True)
    total_amount_projects = fields.Float('All Project Amount', compute="compute_projects", readonly=True, store=True)

    name = fields.Char(string="Name")
    phase = fields.Char(string="Phase")
    color = fields.Integer('Color')
    address = fields.Text(string="Address")
    payment_term_id = fields.Many2one('account.payment.term', 
                                      string='Payment Terms',
                                      oldname='payment_term')

    unit_line = fields.Many2many('building.type.model', string="Units",)
    total_unit = fields.Integer(string="Total Units",
                                compute="total_house_units")
    total_sold = fields.Integer(string="Sold Units",
                                compute="total_house_units")
    total_remain = fields.Integer(string="Remaining", compute="total_house_units")

    def open_bireport(self):
        name = 'bireport' if self.report_by == "gen" else "bi-summary"
        url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url += '/%s' % (name)
        res = {
            'name': 'Go to website',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url
               }
        return res
 
    def button_action_report_view(self, domains): 
        
        search_view_ref = self.env.ref(
            'property_sale.view_building_type_search_filter', False)
        form_view_ref = self.env.ref('property_sale.building_model_form_view_3', False)
        tree_view_ref = self.env.ref('property_sale.property_products_treex', False)
        return {
            'domain': [('id', 'in', domains)],
            'name': 'Buildings',
            'res_model': 'building.type.model',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

    @api.model
    def create(self, vals):
        preferences_count = self.env['property.report'].search_count([])
        if preferences_count > 0:
            raise ValidationError("You cannot create another report, kindly modify the existing one.")
        if 'number' in vals:
            vals['number'] = vals.get('number') + 1
        return super(PropertyReport, self).create(vals)

    def button_action_total_sold_view(self):
        domains = [rec.id for rec in self.mapped('buildingtype').filtered(lambda self: self.mark_sold == True)]
        return self.button_action_report_view(domains)

    def button_action_total_reserved_view(self):
        domains = [rec.id for rec in self.mapped('buildingtype').filtered(lambda self: self.reserved == True)]
        return self.button_action_report_view(domains)

    def button_action_total_unsold_view(self):
        domains = [self.mapped('buildingtype').filtered(lambda self: self.mark_sold == False).ids]
        return self.button_action_report_view(domains)

    @api.onchange('report_type')
    def get_all_projects(self):
        line_ids = []
        if self.report_type and self.report_type == "all":
            projects = self.env['project.configs'].search([])
            for proj in projects:
                line_ids.append(proj.id)
            self.project_ids = [(6, 0, line_ids)]
        else:
            self.project_ids = [(6, 0, line_ids)]

    @api.depends('project_ids', 'datefrom', 'dateto')
    def compute_projects(self):
        if self.project_ids:
            total_unit_sold = 0
            total_unit_unsold = 0
            total_unit_reserved = 0
            total_amount_sold= 0
            total_amount_unsold = 0
            total_amount_reserved = 0
    
            building = []
            for rec in self.project_ids:  
                sold = rec.mapped('unit_line').filtered(lambda s: s.mark_sold == True and self.datefrom <= s.purchase_date and self.dateto >= s.purchase_date if self.datefrom and self.dateto else s.mark_sold == True)
                unsold = rec.mapped('unit_line').filtered(lambda s: s.mark_sold == False) # and self.datefrom <= s.purchase_date and self.dateto >= s.purchase_date if self.datefrom and self.dateto else s.mark_sold == False)
                reserved = rec.mapped('unit_line').filtered(lambda s: s.reserved == True)# and self.datefrom <= s.purchase_date and self.dateto >= s.purchase_date if self.datefrom and self.dateto else s.reserved == True)
                building = [rex.id for rex in sold] + [rex.id for rex in unsold] + [rex.id for rex in reserved]
                total_unit_sold += len(sold.ids)
                total_unit_unsold += len(unsold.ids)
                total_unit_reserved += len(reserved.ids)
                total_amount_sold += sum([solds.list_price for solds in sold])
                total_amount_unsold += sum([unsolds.list_price for unsolds in unsold])
                total_amount_reserved += sum([reserveds.list_price for reserveds in reserved])

            self.buildingtype = [(6, 0, building)]
            self.total_unit_sold = total_unit_sold
            self.total_unit_unsold = total_unit_unsold
            self.total_unit_reserved = total_unit_reserved
            self.total_amount_sold = total_amount_sold
            self.total_amount_unsold = total_amount_unsold
            self.total_amount_reserved=total_amount_reserved
            self.total_amount_projects = sum([total_amount_sold, total_amount_unsold, total_amount_reserved])
        
    def open_action(self):
        pass

    