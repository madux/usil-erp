'''1. 10 UNITS of House in Project Main. 
   2. Customer indicates to buy a unit == Category-->Unit 1
   3. 1 Units deducts from the 10 units
   4. A validity is set to determine if the offer letter exceeds,
   5. If yes=> System Adds the unit back.
   6. If any payment done, system changes state to sold 
   7. if payment is over 30%. It will be allocated. '''
   
'''SETUP: 
    1. Create a configuration model and view as store: E.G 
   Product category(product=product.product, total_unit(computednum of records under the category), 
   )
   2. On sales management: Add the category, this will be displayed on the sales as required, validity_duration(default = 5)
   3. On change of category: the products in orderlines displays only the products under category configuration in 1 above. 
   4. On click of confirm button, it will enable the current date(order date) and set the validity date to what was the default'''
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
 
class SaleOrder(models.Model):
    _order = "id desc"
    _inherit = "sale.order"
    
    offer_price = fields.Float('Offer Price', store=True, compute="compute_discount_offer_price_building_type")
    discounts = fields.Float('Discount(%)',store=True,  compute="compute_discount_offer_price_building_type")
    buildingtype_id = fields.Many2one('building.type', string="Building", store=True, 
    compute="compute_discount_offer_price_building_type")
    migrated_number = fields.Char('Migration Number')
    phone_number = fields.Char('Phone No:', related="partner_id.phone")
    total_discount = fields.Float('Total Discount(%)', readonly=False, compute="discount_function")
    amount_paid = fields.Float('Total Paid', readonly=False) #    compute="compute_payments")
    prop_payment_count = fields.Integer('Counts', default=0)
    outstanding = fields.Float('Outstanding',
                               compute="get_outstanding_payments", store=True, readonly=False)
    percentage_paid = fields.Float('Percentage Paid(%)', store=True,
                               compute="get_outstanding_payments", readonly=False)
    breakdown_ids = fields.Many2many("house.payment.breakdown", 'order_id',
                                     string="Payment Breakdown")
    sale_type = fields.Selection([
        ('sale', 'Sale'),
        ('property', 'Property Sales'),
        ('rental', 'Rental')], string='Sale Type', default='sale' )
    location_project = fields.Many2one('project.configs', string="Project")
    building_unit_ref = fields.Many2many('building.type.model', string="Unit Reference") 
    sale_status = fields.Selection([
        ('Draft', 'Draft'),
        ('Sold', 'Sold'),
        ('Allocated', 'Allocated'),
        ('Cancel', 'Cancelled')], string='Sale Status', default='Draft')
    # invoice_ids = fields.Many2many('account.invoice',
    # string = "Invoices", compute="compute_payments")
    payment_idss = fields.Many2many('account.payment',
                                   string="Payment", readonly=False) 
    date_validity = fields.Datetime(string="Validity Date", 
                                    default=lambda *a: (datetime.now() + relativedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                                    help="Sets the validity date to 5 days by default")  # Add context to pick from parent

    @api.depends('order_line')
    def compute_discount_offer_price_building_type(self):
        build_obj= self.env['building.type']
        for rec in self:
            if rec.order_line:
                price_unit = rec.order_line[0].price_unit
                discount = rec.order_line[0].discount
                product_id = rec.order_line[0].product_id
                rec.buildingtype_id = build_obj.search([('product_id','=', product_id.id)], limit=1).id
                rec.offer_price = price_unit
                rec.discounts = discount 
            else:
                rec.buildingtype_id = False
                rec.offer_price = False
                rec.discounts = False            
    
    @api.depends('amount_total','amount_paid')
    def get_outstanding_payments(self):
        for rec in self:
            paid_percentage = rec.percentage_paid
            if rec.amount_total > 0:
                paid_percentage = (rec.amount_paid * 100) / rec.amount_total 
            rec.update({
                'outstanding': rec.amount_total - rec.amount_paid, 
                'percentage_paid': paid_percentage
                })

    # @api.depends('amount_paid','amount_total')
    # def get_percentage_paid(self):
    #     for rec in self:
    #         if rec.amount_total > 0:
    #             paid_percentage = (rec.amount_paid * 100) / rec.amount_total 
    #             rec.update({'percentage_paid': paid_percentage})
    #         else:
    #             rec.update({'percentage_paid': False})

    @api.depends('order_line')
    def discount_function(self):
        for rex in self:
            discount = sum([rec.discount for rec in rex.mapped('order_line')])
            rex.update({'total_discount': rex.amount_total - rex.amount_paid})

    @api.depends('partner_id')
    def compute_property_details(self):
        for rec in self:
            if rec.partner_id:
                rec.phone_number = rec.partner_id.phone
            else:
                rec.phone_number = False
    
    @api.onchange('location_project')
    def change_payment_term(self):
        if self.location_project:
            if self.sale_type == "property":
                self.payment_term_id = self.location_project.payment_term_id.id
                self.order_line = False

    def generate_house_number(self, buildingtypeid):
        buildingtype = self.env['building.type'].browse([buildingtypeid])
        lastgen = buildingtype.last_gen_no + 1
        house_number = '{} {}'.format(str(buildingtype.prefix) ,str(lastgen))
        return str(house_number)
         
    def confirm_offer(self): # visible when sale_type is property
        buildinglineObj = self.env['building.type.model']
        for rec in self:
            rec.restrict_sales()
            lists = []
            for record in rec.order_line:
                buildingtypeid = self.env['building.type'].sudo().search([('product_id', '=', record.product_id.id)], limit=1)
                if buildingtypeid:
                    buildingtype = self.env['building.type'].browse([buildingtypeid.id])
                    lastgen = buildingtype.last_gen_no + 1
                    house_number = '{} {}'.format(str(buildingtype.prefix) ,str(lastgen))
                    housenumber = record.house_number if record.house_number else house_number
                    # housenumber = record.house_number if record.house_number else self.generate_house_number(buildingtypeid.id),
                    vals = ({
                        'name': rec.name,
                        'product_id': record.product_id.id,
                        'default_code': record.product_id.default_code,
                        'mark_sold': True,
                        'list_price': record.price_unit,
                        'customer_id': rec.partner_id.id,
                        'purchase_date': datetime.now(), #datetimes if datetime else datetime.now(),
                        'reference': rec.name,
                        'property_sale_order_id': rec.id,
                        'sales_team': rec.team_id.id,
                        'discount': record.discount,
                        'location_project': rec.location_project.id,
                        'house_number': housenumber,
                    
                    })
                    buildingtypeid.sudo().write({'building_sale_line': [(0,0, vals)], 'last_gen_no': buildingtypeid.last_gen_no + 1, 'units': buildingtype.units + 1})
                    record.house_number = housenumber # record.house_number if record.house_number else self.generate_house_number(buildingtypeid.id),
                    project_id = self.env['project.configs'].sudo().search([('id', '=', rec.location_project.id)], limit=1)
                    if project_id:
                            # raise ValidationError('project is '+ project_id.name+ 'and building is '+buildingtype.id)
                            project_id.sudo().write({'unit_line':[(4,buildingtype.id)]})
                    else: 
                        raise ValidationError("One of the Units you are trying to sale is not found on the configuration")

            rec.sale_status = "Sold"
            rec.invoice_status = "to invoice"
            rec.calculate_breakdown()

    def cancel_expired_allocation(self):
        if self.sale_type == "property" and self.date_validity:
            date_validity = datetime.strptime(self.date_validity, "%Y-%m-%d %H:%M:%S")
            if (date_validity > datetime.now()) and (self.amount_paid <= 0):
                buildingsaleline = self.env['building.type.model'].search([('property_sale_order_id', '=', self.id)])
                for rex in buildingsaleline:
                    rex.mark_sold = False
                    rex.unlink()
                self.action_cancel()
                self.action_propertycancel()
                self.update_transactions()
            else:
                raise ValidationError("You cannot remove or cancel \
                        this allocation because the customer has made payment!")

    def action_propertycancel(self):
        self.sale_status = "Draft"
        self.state = "draft"

    def cron_check_expired_allocation(self):
        if self.sale_type == "property" and self.date_validity:
            if (self.date_validity > datetime.today()) and (self.amount_paid <= 0):
                buildingsaleline = self.env['building.type.model'].search([('property_sale_order_id', '=', self.id)])
                if buildingsaleline:
                    for rex in buildingsaleline:
                        rex.mark_sold = False
                        rex.unlink()
                    self.action_cancel()
                    self.update_transactions()

    def get_url(self, id, name):
        base_url = http.request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
        return "<a href={}> </b>Click<a/>.".format(base_url)

    def send_mail_officers(self):
        bodyx = "Dear Sir, <br/>An allocation with Reference: {} have been effected.\
        <br/> Kindly {} to view and followup with the necessary operations. <br/>\
        Regards".format(self.name, self.get_url(self.id, self._name))
        email_from = self.env.user.email
        group_user_id2 = self.env.ref('property_sale.director').id
        group_user_id = self.env.ref('property_sale.officer').id
        group_user_id3 = self.env.ref('property_sale.accounts_prop').id
        if self.id:
            bodyx = bodyx
            self.mail_sending_for_three(
                email_from,
                group_user_id,
                group_user_id2,
                group_user_id3,
                bodyx) 
         
    def mail_sending_for_three(self, email_from, group_user_id, group_user_id2, group_user_id3, bodyx):
        from_browse = self.env.user.name
        groups = self.env['res.groups']
        for order in self:
            group_users = groups.search([('id', '=', group_user_id)])
            group_users2 = groups.search([('id', '=', group_user_id2)])
            group_users3 = groups.search([('id', '=', group_user_id3)])
            group_emails = group_users.users
            group_emails2 = group_users2.users
            group_emails3 = group_users3.users

            append_mails = []
            append_mails_to = []
            append_mails_to3 = []
            for group_mail in group_emails:
                append_mails.append(group_mail.login)

            for group_mail2 in group_emails2:
                append_mails_to.append(group_mail2.login)

            for group_mail3 in group_emails3:
                append_mails_to3.append(group_mail3.login)

            all_mails = append_mails + append_mails_to + append_mails_to3 
            email_froms = str(from_browse) + " <" + str(email_from) + ">"
            mail_to = (', '.join(str(item) for item in all_mails))
            subject = "Property Sales Notification"
            
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_to,
                #'email_cc': mail_sender,
                'reply_to': email_from,
                'body_html': bodyx
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)
    
    #send payment reminder mail to user if trigger date have been met
    def send_reminder_mail(self):
        offer_ids = self.env['sale.order'].search([])
        for offer in offer_ids:
            date_order = offer.date_order
            if (offer.amount_paid < offer.amount_total) and (offer.state not in ["draft"]):
                if date_order:
                    today_date = datetime.today()
                    date_order = datetime.strptime(date_order, '%Y-%m-%d')
                    today = datetime.strptime(today_date, '%Y-%m-%d')
                    diff = today - date_order
                    duration = diff.days
                    # diff = r.date() - today_date.date()
                    offer.send_mail(offer.id)
                    status = "Due Date"
                    body = "%s Payment Reminder message sent to Customer" % (status)
                    offer.message_post(body=body) 

    ''' funtion to send payment reminder by mail on button click '''
    def send_mail(self, id):
        sale_order_id = self.env['sale.order'].browse([id])
        # for report in self.env['sale.order'].browse(id):
        if sale_order_id.date_order and sale_order_id.amount_paid <= 0:
            payment_terms = self.env['account.payment.term'].search([('id', '=', sale_order_id.payment_term_id.id)])
            lines = sale_order_id.payment_term_id.mapped("line_ids")
            sum_of_days = sum(day.days for day in lines)
            today_date = datetime.today()
            order_date = datetime.strptime(datetime.strftime(sale_order_id.date_order, '%Y-%m-%d'), '%Y-%m-%d')
            diff = order_date.date() - today_date.date()
            if (diff.days in range(0, 5)):
                template_id = self.env['mail.template'].search([('name', '=', 'Plot Payment Friendly Reminder')], limit=1)
                if template_id:
                    mail_message = self.env['mail.template'].browse(template_id.id).send_mail(sale_order_id.id, force_send=True, raise_exception=True)
            elif (diff.days > sum_of_days) and (diff.days in range(5, 15)):
                template_id = self.env['mail.template'].search([('name', '=', 'Plot Payment Reminder')], limit=1)
                if template_id:
                    mail_message = self.env['mail.template'].browse(template_id.id).send_mail(sale_order_id.id, force_send=True, raise_exception=True)

            elif (diff.days > sum_of_days):
                template_id = self.env['mail.template'].search([('name', '=', 'Plot Payment Late Reminder')], limit=1)
                if template_id:
                    mail_message = self.env['mail.template'].browse(template_id.id).send_mail(sale_order_id.id, force_send=True, raise_exception=True)

    def send_mail_click(self):
        self.send_mail(self.id)

    def edit_offer_letter(self):
        self.ensure_one()
        #switch offer letter type to pdf
        report = self.env['ir.actions.report'].search([('report_name', '=', 'property_sale.offer_letter')], limit=1)
        if report:
            report.write({'report_type': 'qweb-html'})
        # return self.env['report'].get_action(self.id, 'property_sale.offer_letter')
        return self.env.ref('property_sale.offer_letter_report').report_action(self)


    def print_offer_letter(self):
        self.ensure_one()
        # switch offer letter type to pdf
        report = self.env['ir.actions.report'].search([('report_name', '=', 'property_sale.offer_letter')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        body = "%s  printed an offer letter on %s" % (self.env.user.name, datetime.strftime(datetime.today(), '%d-%m-%y'))
        self.message_post(body=body)
        # return self.env['report'].get_action(self.id, 'property_sale.offer_letter')
        return self.env.ref('property_sale.offer_letter_report').report_action(self)

    def next_payment_date(self, date):
        amount, date, name = self.next_amount_operation()
        self.next_payment_date = date

    def Register_Payment(self):
        amount, date, name = self.next_amount_operation()
        breakdowns = self.breakdown_ids
        amounts = 0 
        sale = self.env['sale.order'].search([('id', '=', self.id)])
        if len(self.mapped('breakdown_ids')) > 0:
            if int(self.prop_payment_count) < int(len(self.mapped('breakdown_ids'))):
                amounts = self.breakdown_ids[self.prop_payment_count].amount_to_pay
            else:
                amounts = self.outstanding
        else:
            amounts = self.outstanding
        dummy, view_id = self.env['ir.model.data'].get_object_reference('account', 'view_account_payment_form')
        ret = {
                'name':'Register Payment',
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'domain': [],
                'context': {
                        'default_amount': amounts,
                        'default_payment_type': 'inbound',
                        'default_partner_id':self.partner_id.id, 
                        'default_communication': self.name, 
                        'default_reference': self.name,
                        'default_narration': name,
                        'default_is_property': True,
                        },
                'target': 'new',
                }
        return ret

    def view_payment_history(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('account', 'view_account_payment_tree')
        for record in self:
            return {
                    'name': _('Provision Allocation Payments'),
                    'view_mode': 'tree',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.payment',
                    'domain': [('id', 'in', [rec.id for rec in record.payment_idss])], #['&',('partner_id', '=', record.partner_id.id),('reference', '=', self.name)],
                    'target': 'new'
            }
            
    def check_payment_validation(self):
        payment_in_draft = self.mapped('payment_idss').filtered(lambda s: s.state not in ['posted', 'sent'])
        if payment_in_draft:
            raise ValidationError('All Payments are still not confirmed by accounts Please inform accounts to validate')

    def print_receipt(self):
        self.ensure_one()
        self.check_payment_validation()
        # switch offer letter type to pdf
        if self.amount_paid > 0.00:
            body = "%s Printed a Receipt" %self.env.user.name
            self.message_post(body=body)
            report = self.env["ir.actions.report"].search([('report_name', '=', 'property_sale.receipt_todate')],limit=1)
            if report:
                report.write({'report_type':'qweb-pdf'})
            # return self.env['report'].get_action(self.id, 'property_sale.receipt_todate')
            return self.env.ref('property_sale.receipt_payment_all').report_action(self)
        else:
            raise ValidationError('The allocation payment must be greater than 0%')
        
    def print_provisional_allocation_letter(self):
        self.ensure_one()
        #switch offer letter type to pdf
        if self.percentage_paid >= 30.0:
            body = "%s Printed an offer letter" %self.env.user.name
            self.message_post(body=body)
            report = self.env["ir.actions.report"].search([('report_name', '=', 'property_sale.report_final_provision_letter_prop')],limit=1)
            if report:
                report.write({'report_type':'qweb-pdf'})
            # return self.env['report'].get_action(self.id, 'property_sale.report_final_provision_letter_prop')
            return self.env.ref('property_sale.final_provision_offer_letter_prop').report_action(self)

        else:
            raise ValidationError('The payment must be equal or above 30%')

    def print_final_allocation_letter(self):
        self.ensure_one()
        #switch offer letter type to pdf
        if self.percentage_paid >= 100.0:
            body = "%s Printed an offer letter" %self.env.user.name
            self.message_post(body=body)
            report = self.env["ir.actions.report"].search([('report_name', '=', 'property_sale.report_final_provision_letter_prop')],limit=1)
            if report:
                report.write({'report_type':'qweb-pdf'})
            # return self.env['report'].get_action(self.id, 'property_sale.report_final_provision_letter_prop')
            return self.env.ref('property_sale.final_provision_offer_letter_prop').report_action(self)

        else:
            raise ValidationError('The allocation payment must be completed to 100%')

    def print_offer_payment_statement(self):
        # return self.env['report'].get_action(self.id, 'property_sale.report_accountstatement')
        return self.env.ref('property_sale.report_account_statement').report_action(self)

    def next_amount_operation(self):
        if self.breakdown_ids:
            lines = self.mapped('breakdown_ids')
            amount_to_pay, next_payment_date, name = [], [], []
            for line in lines:
                amount_to_pay.append(line.amount_to_pay)
                next_payment_date.append(line.next_payment_date)
                name.append(line.name)
            amo, dat, nam = iter(amount_to_pay), iter(next_payment_date), iter(name)
            amount, date, name = next(amo), next(dat), next(nam)
            return amount, date, name
        else:
            return self.outstanding, datetime.now(), self.name

    def create_breakdown(self, next_payment_date, amount_to_pay, name):
        lists = []
        lists.append((0, 0, {
                        'order_id': self.id, 
                        'name': name,  
                        'next_payment_date': next_payment_date,
                        'amount_to_pay': amount_to_pay,
                        }))
        self.write({'breakdown_ids': lists})

    def calculate_breakdown(self):
        current = datetime.now()
        nums = 1
        overall_duration = 0
        for payment in self.payment_term_id.line_ids[:-1]:
            amount_to_pay = 0.0
            name = str(nums) +"- Installment"
            if payment.option == "day_after_invoice_date":
                next_payment_date = datetime.now() + timedelta(days=payment.days)
                overall_duration += payment.days
                if payment.value == "percent":

                    amount_to_pay = (payment.value_amount / 100) * self.amount_total
                elif payment.value == "fixed":
                    amount_to_pay = (payment.value_amount)
                else:
                    amount_to_pay = self.amount_total
                self.create_breakdown(next_payment_date, amount_to_pay, name)

            elif payment.option == "fix_day_following_month":
                date_remain = 30 - int(current.day)
                diff = date_remain + payment.days
                overall_duration += diff
                next_payment_date = current + timedelta(days=diff)
                self.next_payment_date = next_payment_date
                if payment.value == "percent":
                    amount_to_pay = (payment.value_amount / 100) * self.amount_total
                    printer.pprint("The amount to pay is" + str(amount_to_pay))
                elif payment.value == "fixed":
                    amount_to_pay = (payment.value_amount)
                else:
                    amount_to_pay = self.amount_total
                self.create_breakdown(next_payment_date, amount_to_pay, name)

            elif payment.option == "last_day_following_month":
                # check the next date of payment
                date_remain = 30 - int(current.day)
                diff = date_remain + 30
                overall_duration += diff
                next_payment_date = current + timedelta(days=diff)
                if payment.value == "percent":
                    amount_to_pay = (payment.value_amount /100) *self.amount_total
                                     
                elif payment.value == "fixed":
                    amount_to_pay = (payment.value_amount)
                else:
                    amount_to_pay = self.amount_total
                self.create_breakdown(next_payment_date, amount_to_pay, name)

            elif payment.option == "last_day_current_month":
                # check the next date of payment
                date_remain = overall_duration + 30
                diff = date_remain
                next_payment_date = current + timedelta(days=overall_duration)
                if payment.value == "percent":
                    amount_to_pay = (payment.value_amount /100) * self.amount_total
                elif payment.value == "fixed":
                    amount_to_pay = (payment.value_amount)
                else:
                    amount_to_pay = self.amount_total
                self.create_breakdown(next_payment_date, amount_to_pay, name)
            nums += 1
    
    def get_all_related_builiding(self):
        # project = self.env['project.configs'].browse([project_id])
        project = self.env['project.configs'].search([])
        for proj in project:
            all_building = self.env['building.type'].search([('location_project', '=', proj.id)])
            if all_building:
                proj.write({'unit_line': [(6, 0, [rec.id for rec in all_building])]})

    def restrict_sales(self):
        for rec in self.order_line:
            related_building_id = self.env['building.type'].search([('product_id','=', rec.product_id.id), ('location_project','=', self.location_project.id)], limit=1)
            if related_building_id and related_building_id.count_unsold < 1:
                raise ValidationError("You have exhausted the number of Units for {}. Kindly remove the line".format(rec.product_id.name))

    def update_transactions(self):
        for rec in self.order_line:
            building = self.env['building.type'].search([('product_id', '=', rec.product_id.id)])
            if building:
                for tec in building:
                    tec.update_transactions()
            else:
                raise ValidationError('NO REFERENCE FOUND')
             

    # @api.multi
    # def migration_def(self):
    #     offer_app = self.env['offer.application'].search([('imported', '=', False)])
    #     build_obj = self.env['building.type']
    #     global_build_id = False
    #     global_total_units = False
    #     global_generated_units = False
    #     errors = []
    #     if offer_app:
    #         for records in offer_app:
    #             build_list = []

    #             project_obj = self.env['project.configs']
    #             project_prefix_obj = self.env['project.prefix']
    #             payment_plan_obj = self.env['account.payment.term']
                
    #             build_obj = self.env['building.type']
    #             payment_plan_id = False
    #             build_id = False
    #             product = False
    #             house_prefix = 0
    #             total_units = 0
    #             unit_remain=0
    #             sold = 0
    #             project_id = False
    #             build_count = 0
    #             available_unit = 0
    #             product_id = False
                
    #             payment = payment_plan_obj.search([('name', '=', records.payment_term_id.payment_term.name)], limit=1)

    #             payment_plan_id = False
    #             payment_plan = self.env['construction.payment.term'].search([('project_site_id', '=', records.project_site.id),('building_type_id', '=', records.building_type.id)], limit=1)
    #             custom_payment_term = payment_plan_obj.search([('name', '=ilike', 'custom')], limit=1)
    #             payment_plan_id = payment_plan.payment_term.id if payment_plan else custom_payment_term.id if custom_payment_term else 1


    #             # if self.env['projectsite.master'].browse([records.project_site.id)]).id == 9:
    #             #     # create a project called APO URBAN MARKET and assign the id to project variable
    #             #     project = 1
    #             #     project_id = project
    #             # else:
    #             #     project = project_obj.search([('name', '=', records.project_site.name.name)], limit=1)
                
    #             project_id = project.id if project else False
    #             project_prefix = project_prefix_obj.search([('project_site', '=', records.project_site.id), ('building_type', '=', records.building_type.id)], limit=1)
    #             if project_prefix:
    #                 house_prefix = project_prefix.prefix
    #                 total_units = int(project_prefix.units)
    #                 sold = int(project_prefix.count)
    #                 unsold = int(total_units) - int(sold)
    #                 unit_remain = int(project_prefix.unit_remain)
    #             #if not project_id:
    #             if self.env['projectsite.master'].browse([records.project_site.id]).id == 9:
    #                 # create a project called APO URBAN MARKET and assign the id to project variable
    #                 project = 1
    #                 project_id = project
    #             else:
    #                 project_id = project_obj.create({
    #                     'name': records.project_site.name.name,
    #                     'address': records.project_site.address if records.project_site.address else records.project_site.name.name,
    #                     'phase': records.phase_id.name, 
    #                     'payment_term_id': payment_plan_id,
    #                 }).id
                    
    #             # else:
    #             #     project_id = project_id
    #             #     project_idz = project_obj.browse([project_id])
    #             discounts = 0
    #             if records.consent_fee > 1:
    #                 discounts = records.consent_fee * 100 / records.offer_price
    #             else:
    #                 discounts = 0

    #             product_id = self.env['product.product'].search([('name', '=', records.building_type.name)], limit=1)
    #             if not product_id:
    #                 product = self.env['product.template'].create({
    #                     'name': records.building_type.name,
    #                     'list_price': int(payment_plan.amount) if payment_plan and payment_plan.amount > 1 else records.offer_price,
    #                     'taxes_id': False,
    #                     'supplier_taxes_id': False,
    #                 }).id
    #             else:
    #                 product = product_id.id
                
    #             construction_payment_custom_plan = self.env['construction.payment.term'].search([('payment_term.name', '=', 'custom')],limit=1)
    #             building = build_obj.search([('name', '=',  records.building_type.name), ('location_project.name', '=', records.project_site.name.name)], limit=1) # ('name', '=',  records.build_type), ('location_project', '=', )], limit=1)
    #             list_price = int(records.payment_term_id.amount) if records.payment_term_id.amount > 0 else float(construction_payment_custom_plan.amount) if construction_payment_custom_plan and construction_payment_custom_plan.amount > 0 else 1.0
    #             if not building:
    #                 build_id = build_obj.create({
    #                     'name': records.building_type.name,
    #                     'location_project': project_id,
    #                     'prefix': house_prefix if house_prefix else 'NaN',
    #                     'last_gen_no': int(sold) if sold > 0 else 0,
    #                     'total_units': int(total_units) if total_units > 0 else 0,
    #                     'count_unsold': int(unit_remain) if unit_remain > 0 else 0,
    #                     'units': int(unit_remain) if unit_remain > 0 else 0,
    #                     'count_sold': int(sold) if sold > 0 else 0,
    #                     'list_price': list_price if list_price > 0 else 1, 
    #                     'product_id': product,
    #                 }).id
    #             else:
    #                 build_id = building.id

    #             payment_plan_idz = payment_plan_obj.browse([payment_plan_id])
    #             product_idz = self.env['product.product'].browse([product])
    #             project_idz = project_obj.browse([project_id])
                

    #             if not build_id:
    #                 errors.append('Building type with name {} not found'.format(records.building_type.name))
    #             else:
    #                 buildz = build_obj.browse([build_id])
    #                 buildz.state = "validate"
    #                 buildz.units =  int(buildz.count_unsold) 
    #                 buildz.last_gen_no = int(buildz.count_sold)
    #                 build_list.append(buildz.id)
                    
    #                 project_idz.write({'unit_line': [(4, buildz.id)]})
    #                 if not project_idz:
    #                     raise ValidationError('No project id found while trying to create unit lines')
    #                 vals = ({
    #                         'name': buildz.name,
    #                         'buildingtype_id': buildz.id,
    #                         'product_id': product_idz.id,
    #                         'default_code': product_idz.default_code,
    #                         'mark_sold': True,
    #                         'list_price': records.offer_price,
    #                         'reference': str(records.id), 
    #                         'reserved': False,
    #                         'location_project': project_idz.id,
    #                         'amount_paid': records.amount_todate,
    #                         'outstanding': records.rem_balance,  # TODO allocate.balance
    #                         'purchase_date': records.offer_date, 
    #                         'customer_id': records.partner_id.id,
    #                         'house_number': records.offer_number,
    #                         'discount': discounts,  
    #                     })
    #                 self.env['building.type.model'].create(vals)
                     
                
    #                 # buildz.update_transactions()
    #                 #FIXME buildz.expected_outstandings_amount += records.rem_balance
    #                 #FIXME buildz.expected_paid_amount += records.amount_todate
            
    #             states = ''
    #             if records.offer_state == 'draft':
    #                 states = 'Draft'
    #             elif records.offer_state in ["first", "reserved"]:
    #                 states = 'Sold'
    #             elif records.offer_state == "alloation":
    #                 states = 'Allocation'

    #             elif records.offer_state == "deallocation":
    #                 states = 'Cancel'
                
    #             values = {
    #                 'product_id': product_idz.id,
    #                 'name': product_idz.name,
    #                 'product_uom_qty': records.units,
    #                 'product_uom': self.env['product.uom'].search([('name', '=', 'Unit(s)')]).id,
    #                 'price_unit': records.offer_price, # product_idz.list_price,
    #                 'discount': discounts,
    #                 # 'taxes_id': [6,0,[rex.id for rex in product_idz.taxes_id]],
    #                 }
                
    #             vals = {
    #                     'partner_id': records.partner_id.id,
    #                     'date_order': records.offer_date,
    #                     'location_project': project_idz.id, 
    #                     'payment_term_id': payment_plan_idz.id,
    #                     'sale_status': states,
    #                     'migrated_number': records.offer_number,
    #                     'amount_paid': records.amount_todate,
    #                     'branch_id': self.env.user.branch_id.id,
    #                     'order_line': [(0,0, values)]
    #                     }

    #             create_sobj = self.env['sale.order'].create(vals)
    #             account_payment = self.env['account.payment'].search(['|', ('offer_app', '=', records.id), ('plot_allocate.offer_id', '=', records.id)])
    #             if account_payment:
    #                 create_sobj.write({'payment_idss': [(4, [rec.id for rec in account_payment])]})

    #             records.imported = True
    #         build_count += 1
    #         # self.get_all_related_builiding()

            
    #     else:
    #         raise ValidationError('You have successfully migrated all records')


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    house_number = fields.Char('House Number') # required if house number is true,
    location_project = fields.Many2one('project.configs')
    date_validity = fields.Datetime(string="Validity Date")
    product_id = fields.Many2one('product.product', string='Product', change_default=True, ondelete='restrict', required=True)
   
    @api.onchange('location_project')
    def domain_product_ids(self):
        domain = {}
        sy_list = []
        if self.location_project:
            sy = self.env['project.configs'].search([('id','=', self.location_project.id)], limit=1)
            sys = sy.mapped('unit_line').filtered(lambda s: s.location_project.id == self.location_project.id and s.units > 0)
            for rec in sys:
                sy_list.append(rec.product_id.id)
            domain = {'product_id': [('id', '=', sy_list)]}
            return {'domain': domain}
        else:
            domain = {'product_id': [('sale_ok', '=', True)]}
            return {'domain': domain}

    @api.onchange('house_number')
    def check_house_number(self):
        if self.house_number:
            related_building_id = self.env['building.type'].search([('product_id','=', self.product_id.id)], limit=1)
            hnum_duplicate = related_building_id.mappped('building_sale_line').filtered(lambda s: s.house_number == self.house_number)
            if hnum_duplicate:
                raise ValidationError("The same house number has been assigned to a Unit. kindly change it")


class PaymentBreakdown(models.Model):
    _name = "house.payment.breakdown"
    
    order_id = fields.Many2one('sale.order')
    name = fields.Char(string='Name')
    next_payment_date = fields.Datetime('Due Date')
    amount_to_pay = fields.Float("Amount")
    status = fields.Boolean("Status", default=False)
 
 
