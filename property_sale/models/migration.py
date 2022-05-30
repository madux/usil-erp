# -*- coding: utf-8 -*-

from odoo import models, fields, api
import os
import logging

_logger = logging.getLogger(__name__)

class data_migration(models.Model):
    _name = "usl.datamigration"

    # @api.model
    # def migrate_data(self):
    #     allocation = self.env['plot.allocate'].search([])
    #     for records in allocation:
    #         if not self.env['sale.order'].search([('migrated_number', '=', records.offer_id.name)])
    #             project_obj = self.env['project.configs']
    #             payment_plan_obj = self.env['account.payment.term']
    #             build_obj = self.env['building.type.model']
    #             try:
    #                 project = project_obj.search([('name', '=',  records.name.name)], limit=1)
    #                 payment = payment_plan_obj.search([('name', '=', records.payment_plan.payment_term.name)], limit=1)
    #                 building = build_obj.search([('name', '=',  records.build_type)], limit=1)

    #                 project_id = None
    #                 payment_plan_id = None
    #                 build_id = None

    #                 if not payment:
    #                     plans = records.payment_plan.payment_term
    #                     # for lin in records.payment_plan.payment_term.line_ids:
    #                     # line_val = {
    #                     #     'value': lin.value,
    #                     #     'days': lin.days,
    #                     #     'option': lin.option,
    #                     # }
    #                     payment_plan_id = payment_plan_obj.create({
    #                         'name': records.payment_plan.payment_term.name,
    #                         'note': records.payment_plan.payment_term.name,
    #                         'line_ids': [(6, 0, plans.mapped('line_ids'))]
    #                     })
    #                 payment_plan_id = payment

    #                 if not project:
    #                     project_id = project_obj.create({
    #                         'name': records.name.name,
    #                         'address': records.name.address if records.name.address else records.name.name,
    #                         'phase': records.phase.name, 
    #                         'payment_term_id': payment_plan_id.id,
                            
    #                     })
    #                 project_id = project

    #                 if not building:
    #                     build_id = build_obj.create({
    #                         'name': records.build_type,
    #                         'location_project': project_id.id,
    #                         'purchase_id': records.partner_id.id,
    #                         # 'mark_sold': True if records.state != 'draft',
    #                         'purchase_date': records.offer_dt,
    #                         'list_price': records.payment_plan.amount,
    #                         'discount': records.payment_plan.consent_fee,
    #                         'building_type': self.env['product.category'].search([('id', '=', 1)]).id
                            
    #                     })
    #                     build_id.validate_building()

    #                 build_id = building

    #                 project_id.write({'unit_line': [(6,0, [build_id.id])]})

    #                 states = None
    #                 if records.state == 'draft':
    #                     states = 'Draft'
    #                 elif records.state in ["first", "reserved"]:
    #                     states = 'Sold'
    #                 elif records.state == "alloation":
    #                     states = 'Allocation'

    #                 elif records.state == "deallocation":
    #                     states = 'Cancel'
                    
    #                 values = {
    #                     'product_id': build_id.product_id.id,
    #                     'name': build_id.product_id.name,
    #                     'product_uom_qty': records.units,
    #                     'price_unit': build_id.list_price,
    #                     'discount': build_id.discount,

    #                     }
    #                 vals= {
    #                         'partner_id': records.partner_id.id,
    #                         'date_order': records.offer_dt, #datetime.datetime.strptime(records.offer_dt, "%Y-%M-%d"),
    #                         # 'name': records.offer_id.name,
    #                         'location_project': project_id.id, 
    #                         'payment_term_id': payment_plan_id.id,
    #                         'sale_status': states,
    #                         'migrated_number': records.offer_id.name,
    #                         'amount_paid': records.amount_dt,
    #                         'order_line': [(0,0, values)]
    #                 }
    #                 create_sobj = self.env['sale.order'].create(vals)
    #                 create_sobj.confirm_offer(datetime= records.offer_dt)
    #             except Exception as e:
    #                 _logger.info(e)
 