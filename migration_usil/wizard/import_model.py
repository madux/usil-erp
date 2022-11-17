
from odoo import fields, models ,api, _
from tempfile import TemporaryFile
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import base64
import copy
import io
import re
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd
import xlrd
from xlrd import open_workbook
import csv
import base64
import sys
_logger = logging.getLogger(__name__)


class ImportRecords(models.TransientModel):
    _name = 'import_record.wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)
    import_type = fields.Selection([
            ('employee', 'Employee'),
            ('customer', 'Customer'),
            ('vendor', 'Vendor'),
            ('warehouse', 'Warehouse'),
            ('product', 'Products'),
            ('asset', 'Asset'),
            ('property', 'Property'),
        ],
        string='Import Type', required=True, index=True,
        copy=True, default='all',
        track_visibility='onchange'
    )
    location_project = fields.Many2one('project.configs', string="Project")
    buildingtype_id = fields.Many2one('building.type', string='ID', ondelete='cascade')
    building_name = fields.Char("Building Name")

    @api.onchange('location_project')
    def onchange_location_project(self):
        domain =[('id', '=', None)]
        if self.location_project:
            self.buildingtype_id = False
            buildingtypes = self.env['building.type'].search([('location_project', '=', self.location_project.id)])
            domain = [('id', 'in', [rec.id for rec in buildingtypes])]
        return {
            'domain': {
            'buildingtype_id': domain
        }}

    def excel_reader(self, index=0):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet = workbook.sheet_by_index(index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
            return file_data
        else:
            raise ValidationError('Please select file and type of file')


    def create_uom(self, name):
        product_uom_obj = self.env['uom.uom']
        uom_ref = product_uom_obj.search([('name', '=ilike', name)], limit=1)
        uom_id = uom_ref.id if uom_ref else product_uom_obj.create({
            'name': name, 'category_id': self.env['uom.category'].search([('name', '=', 'Unit')], limit=1).id, 
            'uom_type': 'bigger'
        }).id
        return uom_id
    
    def create_lot_id(self, name, productid, best_before, expiry_date, removal_date, alert_date):
        lot_obj = self.env['stock.production.lot']
        lot_ref = lot_obj.search([('name', '=', name)], limit=1)
        if not lot_ref:
            lot_id = lot_obj.create({
                'name': name, 'product_id': productid,  'company_id': self.env.user.company_id.id,
                'use_date': best_before, 'expiration_date': expiry_date,'removal_date': removal_date,'alert_date': alert_date,
            })
            return lot_id.id
        else:
            return lot_ref.id
    
    def create_stock_quant(self, product_id, qty, lot_id, location_id):
        stockObj = self.env['stock.quant'].sudo()
        stock_ref = stockObj.search([('product_id.default_code', '=', product_id.default_code)], limit=1)
        if not stock_ref:
            if product_id.type == "product": # Stock quants are only created for storable products 
                stockObj.create({
                    'tracking': product_id.tracking, 
                    'product_id': product_id.id,
                    'lot_id': lot_id, 
                    'quantity': qty,
                    'product_uom_id': product_id.uom_id.id,
                    'location_id': location_id
                })
        else:
            stock_ref.update({
                'quantity': stock_ref.quantity + qty
            })
            
    def create_warehouse(self, name, code, partner_id=False):
        partner_obj = self.env['res.partner']                  
        partner = self.env.user.company_id.partner_id.id if not partner_id else partner_id
        warehouseObj = self.env['stock.warehouse']
        warehouse_ref =  warehouseObj.search(['|', ('name', '=', name), ('code', '=', code)], limit=1)
        if not warehouse_ref:
            warehouse = warehouseObj.create({
                'name': name,
                'code': code,
                'partner_id': partner
            })
             
        else:
            warehouse = warehouse_ref
        return warehouse

    #FIXED ASSET
    def generate_fixed_assets(self, file_data):
        currencyObj = self.env['res.currency']
        accountAsset = self.env['account.asset']
        accountJounral = self.env['account.journal']
        accountObj = self.env['account.account']
        unsuccess_records = []           
        errors = ['The Following messages occurred']

        fixedJournal = accountJounral.search([('code', '=', 'FXA')], limit=1)
        if not fixedJournal:
            raise ValidationError('Please ensure you maunaly create a fixed journal record with code FXA')
        fixed_asset_records = []
        for row in file_data:
            currency = currencyObj.search([('name', '=', row[6])], limit=1)
            accountassetid = accountObj.search([('code', '=', row[9])], limit=1)
            accountdepreciationid = accountObj.search([('code', '=', row[10])], limit=1)
            accountexpdepreciationid = accountObj.search([('code', '=', row[11])], limit=1)
            if not all([accountassetid, accountdepreciationid, accountexpdepreciationid]):
                raise ValidationError('Please ensure the following accounts => {}, {}, {}'.format(row[9], row[10], row[11]))
        
            name = row[0]
            original_value = row[1]
            book_value = row[2]
            value_residual = row[3]
            acquisition_date = datetime.strptime(row[4], '%d/%m/%Y')
            first_depreciation_date_import = datetime.strptime(row[5], '%d/%m/%Y')
            currency_id = currency.id if currency else currencyObj.search([('name', '=', 'NGN')], limit=1).id
            method = 'linear' if row[7] == "Straight Line" else 'linear'
            method_number = row[8]
            method_period = "12" # use 12 for years and 1 for months
            account_asset_id = accountassetid.id 
            account_depreciation_id = accountdepreciationid.id 
            account_depreciation_expense_id = accountexpdepreciationid.id
            journal_id = fixedJournal.id
            vals = {
                'name': name,
                'original_value': original_value,
                'book_value': book_value,
                'value_residual':value_residual,
                'acquisition_date': acquisition_date,
                'first_depreciation_date_import': first_depreciation_date_import,
                'currency_id': currency_id or 124,
                'method': method,
                'method_number':method_number,
                'method_period': method_period,
                'account_asset_id': account_asset_id,
                'account_depreciation_id': account_depreciation_id,
                'account_depreciation_expense_id': account_depreciation_expense_id,
                'journal_id': journal_id,
                'asset_type':'purchase'
            }
            asset_id =accountAsset.create(vals)
            accountAsset.browse([asset_id.id]).validate()
        return fixed_asset_records
        
    # PRODUCT AND WAREHOUSE STARTS
    def generate_warehouse(self, file_data):
        state_obj = self.env['res.country.state']
        partner_obj = self.env['res.partner']
        unsuccess_records = []           
        errors = ['The Following messages occurred']

        for row in file_data:
            # try:
            warehouse_name = row[0]
            warehouse_short_name = row[1]
            address = row[2]
            address2 = row[3]
            city = row[4]
            state = row[5]
            phone = row[6]
            mobile = row[7]
            email = row[8]
            firstname = row[9] or " "
            middlename = row[10] or " "
            lastname = row[11] or " "
            fullname = ' '.join([firstname, middlename, lastname])
            search_state_ref = state_obj.search([('name', 'ilike', state)], limit=1)
            state_id = search_state_ref.id if search_state_ref else False
            partner_id = partner_obj.create({
                        'name': fullname, 'phone': phone, 'email': email, 'mobile': mobile,
                        'company_type': 'person', 'state_id': state_id, 'country_id': 163,
                        'street': address, 'street2': address2, 'city': city, 'customer_rank': 1,
                        'supplier_rank': 1, 'type': 'other', 
                    }).id
            parent_partner = self.env.user.company_id.partner_id
            parent_partner.write({'child_ids': [(4, partner_id)]})
            self.create_warehouse(warehouse_name, warehouse_short_name, partner_id)
            # except Exception as error:
            #     unsuccess_records.append(warehouse_name)
        # return unsuccess_records
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)

            
    def generate_product(self, file_data):
        product_obj = self.env['product.product']
        product_categ_obj = self.env['product.category']
        unsuccess_records = []
        errors = ['The Following messages occurred']
        for row in file_data:
            # try:
            prod_name = row[0]
            barcode = False # row[1]
            default_code = row[2]
            product_type = "consu" if row[3] == "Consumable" else "service" if row[3] == "Service" else "product" if row[3] == "Storable Product" else False
            prod_categ_name = row[4]
            fifo = self.env.ref('stock.removal_fifo').id
            lifo = self.env.ref('stock.removal_lifo').id
            fefo = self.env.ref('product_expiry.removal_fefo').id
            removal_strategy = fifo if row[5] == 'FIFO' else lifo if row[5] == 'LIFO' else fefo if row[5] == 'FEFO' else False
            standard_price = row[8] if row[8] else False # cost price
            quantity = 0 # row[9]
            sale_uom = row[10]
            po_uom = row[11]
            batch_lot = row[12]
            best_before = datetime.strptime(row[13], '%m/%d/%Y %H:%M:%S') if row[13] else False
            expiry_date = datetime.strptime(row[14], '%m/%d/%Y %H:%M:%S') if row[14] else False
            removal_date = datetime.strptime(row[15], '%m/%d/%Y %H:%M:%S') if row[15] else False
            alert_date = datetime.strptime(row[16], '%m/%d/%Y %H:%M:%S') if row[16] else False
            purchase_ok = True
            sale_ok = True
            warehouse_name = row[19]
            product_desc = row[20]
            categ_ref = product_categ_obj.search([('name', '=', prod_categ_name)], limit=1)
            categ_id = categ_ref.id if categ_ref else product_categ_obj.create({'name' : prod_categ_name, 
            'property_valuation': 'real_time', # 'real_time' if row[6] == "automatic" else 'manual_periodic', 
            'removal_strategy_id': removal_strategy,
            'property_cost_method': 'average' if row[7] == "Average Cost" else 'fifo' if row[7] == 'First In First Out' else 'standard' }).id
            uom_id = self.create_uom(sale_uom)
            uom_po_id = self.create_uom(po_uom)
            tracking = "lot"
            product_ref = product_obj.search([('default_code', '=', default_code)], limit=1)
            product_id = None 
            if not product_ref:
                product_id = product_obj.create({
                    'name': prod_name, 'barcode': barcode, 'default_code': default_code, 'type': product_type,
                    'categ_id': categ_id, 'standard_price': standard_price, 'uom_id': uom_id, 'uom_po_id': uom_po_id,
                    'tracking': tracking, 'purchase_ok': purchase_ok, 'sale_ok': sale_ok,'description_sale': product_desc,
                })
                warehouse = self.create_warehouse(warehouse_name, warehouse_name, False)

                if batch_lot:
                    batch_lot_id = self.create_lot_id(batch_lot, product_id.id, best_before, expiry_date, removal_date, alert_date)
                else:
                    batch_lot_id = False
                stock_quant_id = self.create_stock_quant(product_id, quantity, batch_lot_id, warehouse.lot_stock_id.id)
        #     except Exception as error:
        #         unsuccess_records.append(prod_name)
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)

    # PRODUCT AND WAREHOUSE ENDS

    def create_department(self, name):
        department_obj = self.env['hr.department']
        depart_rec = department_obj.search([('name', '=', name)], limit = 1)
        department_id = department_obj.create({
                    "name": name
                }).id if not depart_rec else depart_rec.id
        return department_id

    def create_employee_category(self, name):
        employee_category_obj = self.env['hr.employee.category']
        category_rec = employee_category_obj.search([('name', '=ilike', name)], limit = 1)
        emp_category = employee_category_obj.create({
                    "name": name
                }).id if not category_rec else category_rec.id
        return emp_category

    def check_existing_emp_record(self, fullname_or_code=False, emp_code=False):
        employee_obj = self.env['hr.employee']
        employee_rec = employee_obj.search([('barcode', '=', emp_code)], limit = 1)
        if employee_rec:
            employee_id = employee_rec.id
            user_id = employee_rec.user_id.id
            return employee_id, user_id
        else:
            return False

    def create_contact_person_record(self, fname, mname, lname, contact_person_phone=False, contact_person_email=False):
        first_name, middle_name, second_name = fname.capitalize() if fname and type(fname) in [str] else fname, mname if mname else "", lname if lname else ""
        fullname = ' '.join([str(first_name), str(middle_name), str(second_name)])
        partner_obj = self.env['res.partner']
        partner_rec = partner_obj.search([('name', '=', fullname),
                ('email', '=', contact_person_email), ('phone', '=', contact_person_phone)], limit=1)
        if partner_rec:
            return partner_rec.id
            
        contact_person_id = partner_obj.create({'name': fullname, 'phone': contact_person_phone, 'email': contact_person_email,
        'lastname': mname,  'lastname2': lname, 'firstname': fname,})
        return contact_person_id.id

    def create_partner_record(self, customer_id, company_type, customer_rank, supplier_rank, name, phone =False, second_phone=False, \
        whatsapp_no= False, email=False, second_email=False, website=False, tin_no = False, street1=False, street2=False, city=False, lga=False, \
            zone=False, title=False, cfname=False, cmname=False, clname=False, cphone=False, cemail=False, sale_person_arg=False, contact_type=False):
        partner_obj = self.env['res.partner']
        lga_obj = self.env['res.country.lga']
        zone_obj = self.env['res.country.zone']
        if name:
            partner_id = partner_obj.search([('customer_id', '=', customer_id)], limit=1)
            if partner_id:
                return partner_id.id
            else:
                lga_ref = lga_obj.search([('name', '=', lga)], limit=1) if lga else False
                zone_id = zone_obj.search([('name', '=', zone)], limit=1) if zone else False
                if lga or zone:
                    if not lga_ref:
                        # raise ValidationError("Wrong LGA name provided")
                        pass 
                    if not zone_id:
                        # raise ValidationError("Wrong zone name provided")
                        pass 
                state_id = lga_ref.state_id.id if lga_ref else False
                region_id = zone_id.region_id if zone_id else False
                country_id = region_id.country_id.id if region_id else False
                
                title_obj = self.env['res.partner.title']
                title_id = title_obj.search([('name', '=ilike', title)], limit=1) if title else False
                # if sale_person_arg:
                sale_person_id = False 
                if sale_person_arg:
                    emp_ref = self.env['hr.employee'].search([('emp_code', '=', sale_person_arg)], limit=1) if sale_person_arg else False
                    sale_person_id = emp_ref.user_id.id if emp_ref else False
                
                partner_id = partner_obj.create({
                    'name': name, 'phone': phone, 'email': email, 
                    'whatsapp_no': whatsapp_no, 'mobile': second_phone,
                    'company_type': company_type, 'lga_id': lga_ref.id if lga_ref else False, 'zone_id': zone_id.id if zone_id else False,
                    'state_id': state_id, 'country_id': country_id, 'secondary_email' :second_email,
                    'website': website, 'tin_no': tin_no, 'user_id': sale_person_id,
                    'region_id': region_id.id if region_id else False, 'street': street1, 'street2': street2, 'city': city,
                    'title': title_id.id if title_id else False, 'customer_id': customer_id if customer_id else False,
                    'supplier_rank':supplier_rank, 'customer_rank': customer_rank, 'contact_type': contact_type,
                    # 'lastname': "-",  'lastname2': "-", 'firstname': "-",
                
                    'child_ids': [(4, self.create_contact_person_record(cfname, cmname, clname, cphone, cemail))] if cfname else False
                })
                return partner_id.id

    def generate_move(self, partner_id, amount, vendor_account=False):
        partner_id = self.env['res.partner'].browse([partner_id])
        journal_id = self.env['account.journal'].search([('type', '=', 'bank')], limit=1) #TODO to be reviewed
        vals = {
            'ref': 'Opening balance Move For {}'.format(partner_id.name),
            'journal_id': journal_id.id,
            'date': fields.Date.today(),
        }
        move_id = self.env['account.move'].create(vals)
        account_receivable_id = partner_id.property_account_receivable_id.id
        account_payable_id = partner_id.property_account_payable_id.id
        amount_val = abs(amount)

        """If the opening balance is less than 0, it is assumed the contact is owning the company"""
        move_items = []  
        product_income_sales_account = self.env['account.account'].search(['|', ('code', '=', 400000), ('name', '=', "Sales category 1")], limit=1).id
        product_expense_sales_account = self.env['account.account'].search(['|', ('code', '=', 500000), ('name', '=', "Cost of sales 1")], limit=1).id
        sl_acc = account_receivable_id if not vendor_account else vendor_account
        ex_acc = product_income_sales_account if not vendor_account else product_expense_sales_account
        if amount and amount > 0:
            move_debit_id = self._prepare_move_lines(move_id.id, 0, amount_val, sl_acc)
            move_credit_id = self._prepare_move_lines(move_id.id, amount_val, 0, ex_acc)
            move_items.append(move_debit_id)
            move_items.append(move_credit_id)
        else:
            move_debit_id = self._prepare_move_lines(move_id.id, 0, amount_val, ex_acc)
            move_credit_id = self._prepare_move_lines(move_id.id, amount_val, 0, sl_acc)
            move_items.append(move_debit_id)
            move_items.append(move_credit_id)
        move_id.line_ids = [(0, 0, rec) for rec in move_items]
        return move_id

    def _prepare_move_lines(self, move_id, credit, debit, account_id):
        move = self.env['account.move'].browse([move_id])
        line_vals = {
            'move_id': move.id,
            'partner_id': move.partner_id.id,
            'debit': debit,
            'credit': credit, 
            'quantity': 1.00, 
            'account_id': account_id,
            'date': move.date, 
        }
        return line_vals

    def create_bank_account(self, account_name, account_number, partnerid, bnk_name, srt_code=False):
        # account_name: name of the holder, account_number: account number
        bank_obj = self.env['res.bank']
        partner_bank_obj = self.env['res.partner.bank']
        account_number = str(int(account_number))
        bank_ref = bank_obj.search([('name', '=', bnk_name), ('bic', '=', srt_code)], limit=1)
        bank_id = bank_ref if bank_ref else self.create_bank_record(bnk_name, srt_code)
        p_bank_ref = partner_bank_obj.search([('acc_number', '=', account_number)], limit=1)
        return p_bank_ref.id if p_bank_ref else partner_bank_obj.create({
            'partner_id': partnerid, 'bank_id': bank_id.id, 
            'bank_name': bank_id.name,
            'acc_holder_name': account_name,
            'acc_number': account_number,
            'currency_id': self.env.company.currency_id.id,
        }).id

    def create_bank_record(self, bank_name, bic_code=False):
        bank_obj = self.env['res.bank']
        bnk_id = bank_obj.create({
            'name': bank_name, 'bic': bic_code
        })
        return bnk_id

    def import_contacts(self, index, sheet_type):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_contact = workbook.sheet_by_index(index)
            data1 = [[sheet_contact.cell_value(r, c) for c in range(sheet_contact.ncols)] for r in range(sheet_contact.nrows)]
            data1.pop(0)
            file_data = data1

            # sheet_vendor = workbook.sheet_by_index(1)
            # data2 = [[sheet_vendor.cell_value(r, c) for c in range(sheet_vendor.ncols)] for r in range(sheet_vendor.nrows)]
            # data2.pop(0)
            # file_data2 = data2
        else:
            raise ValidationError('Please select file and type of file')
        success = 0
        unsucess = 0
        errors = ['The Following messages occurred']
        for row in file_data:
            # import sheet 1
            self.generate_record_sheet(row, sheet_type)

        # for row2 in file_data2:
        #     # import sheet 2
        #     self.generate_record_sheet(row2, False)

    def generate_record_sheet(self, row, sheet):
        '''
        arg sheet 1: True if you want to create customer sheet 
        Setting to false is an indication that the system with import from sheet 2(Vendor sheet)
        The customer and vendor column are not the same
        '''
        partner_obj = self.env['res.partner']
        unimport_count, count, = 0, 0
        success_records, unsuccess_records =  [], []
        # try:
        customer_id = row[0]
        company_type = row[1] if row[1] in ['contact'] else 'person'
        
        title = row[2]
        first_name, middle_name, second_name = row[3].capitalize() if row[3] else "",\
            row[4] if row[4] else "", row[5] if row[5] else ""
        primary_phn_num = row[6]
        secondary_phn_num = row[7]
        whatsapp_phn_num = row[8]
        email = row[9]
        second_email = row[10]
        website = row[11] 
        fullname = ' '.join([first_name, middle_name, second_name])
        zone = row[13] if sheet else False
        lga = row[15] if sheet else False # Municipal
        address1 = row[16] if sheet else row[13]
        address2 = row[17] if sheet else row[14]
        city = row[18] if sheet else row[15] 
        
        #contact details
        cfname = row[19] if sheet else row[20]
        cmname = row[20] if sheet else row[21]
        clname = row[21] if sheet else row[22]
        cphone = row[22] if sheet else row[23]
        cwhatsapp_phn_num = row[23] if sheet else row[24]
        cemail = row[24] if sheet else row[25]
        op_balance = row[25] if sheet else row[26]
        opening_balance = float(op_balance) if op_balance and type(op_balance) in [float, int] else False
        phone = str(primary_phn_num) if primary_phn_num else None
        partner_id = None 
        customer_rank = 1 # use count to increase the customer rank
        supplier_rank = 1 # use count to increase the suppier rank
        if sheet:
            contact_type = "customer" or "others"
            sales_id_col = row[26] if row[26] else False
            partner_id = self.create_partner_record(customer_id, company_type, customer_rank, False, fullname, phone, secondary_phn_num, \
                whatsapp_phn_num, email, \
                    second_email, website, False, address1, address2, city, lga, zone, False, cfname, cmname, \
                        clname, cphone, cemail, sales_id_col, contact_type)
            if opening_balance:
                self.generate_move(partner_id, opening_balance,False)
        else:
            partner_id = self.create_partner_record(
                customer_id, company_type, False, 
                supplier_rank, fullname, phone, 
                secondary_phn_num, whatsapp_phn_num, 
                email, second_email, website, row[12],
                address1, address2, city, False, False,
                 False, cfname, cmname, \
                    clname, cphone, cemail, False, "supplier")
            
            # generate account number for vendor if sheet (Vendor sheet creation)
            partner_browse_obj = self.env['res.partner'].browse([partner_id])
            acc_name,acc_num, bnk_name, srt_code = row[16], row[17],row[18],row[19]
            account_type_id = None
            bank_account_id = None
            if acc_num and acc_name and bnk_name:
                bank_account_id = self.create_bank_account(acc_name, acc_num, partner_id, bnk_name, srt_code)
            if row[29]: # check for account type
                account_payable = self.env['account.account'].search([('name', '=', row[29])], limit=1)
                account_type_id = account_payable.id

            # TODO: Test for bank / account/ account payabable type generation
            partner_browse_obj.write({
                'bank_ids': [(4, bank_account_id)] if bank_account_id else False,
                'property_account_payable_id': account_type_id
                })
            if opening_balance:
                vendor_account = account_type_id if account_type_id else partner_browse_obj.property_account_payable_id.id
                self.generate_move(partner_id, opening_balance, vendor_account)
        count += 1
        success_records.append(fullname)
        # except Exception as error:
        #     print('Caught error: ' + repr(error))
        #     unimport_count += 1
        #     unsuccess_records.append(fullname)
        #     raise ValidationError('There is a problem with the record at Row\n \
        #             {}.\n Check the error around Column: {}' .format(row, error))
         
    def format_date(self,date_str):
        """
        Rearranges date if the provided date and month is misplaced 
            :param date_str is date in format mm/dd/yy
            :return date string 'Y-m-d'
        """
        if not date_str or type(date_str) is not str:
            return False
        data = date_str.split('/')
        if len(data) > 2:
            try:
                mm, dd, yy = int(data[0]), int(data[1]), data[2]
                if mm > 12: 
                    dd, mm = mm, dd
                if mm > 12 or dd > 31 or len(yy) != 4:
                    return False
                else:
                    return "{}-{}-{}".format(yy, mm, dd)
            except Exception as e:
                return False
 
    def create_hr_contract(self, employee_id, date_start, date_end=False):
        if employee_id and date_start:
            srtdate=self.format_date(date_start)
            if date_end and date_end < date_start:
                return False
            else:
                employee = self.env['hr.employee'].browse([employee_id])
                contract = self.env['hr.contract'].create({
                    'state': 'open' if not date_end else "cancel",
                    'name': "Contract for {}".format(employee.name),
                    'structure_type_id': self.env.ref("hr_contract.structure_type_employee").id,
                    'employee_id': employee.id,
                    'wage': 1,
                    'department_id': employee.department_id.id,
                    'job_id': employee.job_id.id,
                    'date_start': srtdate if srtdate else fields.Datetime.today(),
                    'date_end': self.format_date(date_end),
                    'active': False if date_end else True 
                })
                employee.active = False if date_end else True 
                return contract

    def create_pfa(self, name):
        pfa_obj = self.env['hr.pfa']
        pfa_ref = pfa_obj.search([('name', '=', name)], limit=1) 
        pfa_id = pfa_ref.id if pfa_ref else pfa_obj.create({
            'name': name
            }).id
        return pfa_id
        
    def create_job_role(self, name):
        if not name:
            return False
        jobId = self.env['hr.job'].search([('name', '=', name)], limit=1)
        return jobId.id if jobId else self.env['hr.job'].create({'name': name}).id
        
    def import_records_action(self):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet = workbook.sheet_by_index(0)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
        errors = ['The Following messages occurred']
        employee_obj = self.env['hr.employee']
        userObj = self.env['res.users']
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        
        prod_errors = ['The Following messages occurred: ']
        warehouse_errors = ['The Following messages occurred: ']

        if self.import_type == "employee":
            emp_supervisor_map = []
            for row in file_data:
                # try:
                emp_code = row[0]
                first_name, middle_name, second_name = row[1].capitalize() if row[1] else "", row[2]\
                        if row[2] else "", row[3] if row[3] else ""
                phn_num = row[4]
                email = row[5]
                job_title = row[6]
                dept = row[7]
                manager_name_or_code = row[8] 
                emp_supervisor_map.append({"emp_code": emp_code, "sup_code": manager_name_or_code})
                cadre = row[9]
                emergency_contact = row[10]
                emergency_phone = row[11]
                marital_status = row[12]
                gender = row[13] 
                mobilephone = '+234'+ str(row[14])[1:] if row[14] and row[4].startswith('0') else False
                home_phone = '+234'+ str(row[15])[1:] if row[15] and row[4].startswith('0') else False 
                employment_state = row[16]
                employee_sale_type = row[17]
                addr1 = row[18]
                addr2 = row[19]
                state = row[20][:-6] if row[20] else False
                country = row[21]
                private_email = row[22]
                date_hired = row[23]
                date_terminated = row[24]
                date_rehired = row[25]
                dob = row[26]
                wrk_phone = '+234'+ str(row[4])[1:] if row[4] and row[4].startswith('0') else False 
                zone = row[27] or False
                region = row[28] or False
                bank = row[29]
                acc_number = row[30]
                pension_num = row[31]
                pfa = row[32]
                nok_relation = row[33]
                nok_email = row[34]
                passport_num = row[35]
                fullname = ' '.join([first_name, middle_name, second_name])
                phone = phn_num
                department_id = self.create_department(dept)
                category = self.create_employee_category(cadre)
                user_id = False
                state_obj = self.env['res.country.state']
                zone_obj = self.env['res.country.zone']    
                partner_obj = self.env['res.partner']                  
                state_id = False
                zone_id = False
                region_id = False
                country_id = False
                partner_id = False
                search_zone_ref = zone_obj.search([('name', 'ilike', zone)], limit=1)
                search_state_ref = state_obj.search([('name', 'ilike', state)], limit=1)
                state_id = search_state_ref.id if search_state_ref else False
                pfa_id = None 
                if pfa:
                    pfa_id = self.create_pfa(pfa)
                if search_zone_ref:
                    zone_id = search_zone_ref.id 
                    region_id = search_zone_ref.region_id.id
                    country_id = 163 or search_zone_ref.region_id.country_id.id 
                
                portal_user_group = self.env.ref('base.group_portal')
                if employee_sale_type != "Employee":
                    # if the postition is Sales Representative, create a protal user
                    # and write the region and lga to related partner field
                    if email:
                        if not userObj.search([('login', '=', email)], limit=1):
                            user_id = userObj.sudo().create({
                                                'name': fullname,
                                                'login': email,
                                                'password': "admin",
                                                'groups_id': [(6, 0, [portal_user_group.id])],
                                                }).id
                            usr = userObj.browse([user_id])
                            if usr.partner_id:
                                usr.partner_id.update({
                                    'state_id': state_id, 'country_id': country_id,
                                    'region_id': region_id, 'zone_id': zone_id, 
                                    'phone': wrk_phone or home_phone, 'email': email,
                                    'mobile': wrk_phone or mobilephone,   
                                })
                                partner_id = usr.partner_id.id
                if not partner_id:
                    partner_id = partner_obj.create({
                        'name': fullname, 'phone': wrk_phone or phone, 'email': email, 'mobile': mobilephone,
                        'company_type': 'person', 'zone_id': zone_id,
                        'state_id': state_id, 'country_id': country_id,
                        'region_id': region_id, 'street': addr1, 'street2': addr2, 'customer_rank': 1,
                    }).id
                employee_obj = self.env['hr.employee']
                employee_rec = employee_obj.search([('barcode', '=', emp_code)], limit = 1)
                employee_id = employee_rec.id if employee_rec else False # self.check_existing_emp_record(False, emp_code)[0] if self.check_existing_emp_record(False, emp_code) else False
                bank_account_id = None
                if acc_number and partner_id and bank:
                    bank_account_id = self.create_bank_account(fullname, acc_number, partner_id, bank, "")
                if not employee_id:
                    manager_id = self.check_existing_emp_record(manager_name_or_code, False)
                    parent_id = None
                    if manager_id and job_title != "Managing Director/CEO":
                        parent_id = manager_id[0]
                    employee_id = employee_obj.create({
                        'name': fullname,
                        'mobile_phone': mobilephone or home_phone,
                        'work_phone': wrk_phone,
                        'barcode': emp_code,
                        'department_id': department_id,
                        'category_ids': [(4, category)], 
                        'emergency_contact': emergency_contact,
                        'emergency_phone': emergency_phone,
                        'user_id': user_id,
                        'marital': marital_status,
                        'gender': gender, 
                        'job_id': self.create_job_role(job_title),
                        'job_title': job_title,
                        'address_home_id': partner_id,
                        'passport_id': passport_num,
                        'nok_relation': nok_relation,
                        'pfa_id':pfa_id,
                        'pfa_no': pension_num,
                        'bank_account_id': bank_account_id,
                        'private_email': private_email,
                        'phone': home_phone,
                        'birthday': self.format_date(dob),
                        'work_phone': home_phone,
                        'country_id': 163,
                        'work_email': email if email else False,
                        'parent_id': parent_id,
                    }).id 
                else:
                    """This is added if a manager is existing as an employee and similar name was found on the excel
                    perhaps during creation of the main employee and a manager name was generated
                    """
                    pass 
                    # emp = employee_obj.browse([employee_id])
                    # emp_update = emp.update({
                    #     'mobile_phone': phone,
                    #     'work_phone': phone,
                    #     'department_id': department_id,
                    #     'category_ids': [(4, category)], 
                    #     'parent_id': self.check_existing_emp_record(manager_name, False) if self.check_existing_emp_record(manager_name, False) else employee_obj.create({'name': row[7]}).id
                    # })
                srt_date=self.format_date(date_hired)
                # m/d/y str if strt date, and end and start date > end date, return m/d/y
                if not srt_date:
                    errors.append('No Contract Created for' +str(fullname))
                if not self.env['hr.contract'].search([('employee_id', '=', employee_id)], limit=1):
                    contract = self.create_hr_contract(employee_id, date_hired, date_terminated) 
                    if not contract:
                        errors.append('No Contract Created for -' +str(fullname))

                count += 1
                success_records.append(fullname)
            #update employee superviser
            for map in emp_supervisor_map:
                sup_code = map.get('sup_code')
                if sup_code:
                    supervisor = self.env['hr.employee'].sudo().search([('barcode','=', sup_code)], limit=1)
                    if supervisor:
                        emp = self.env['hr.employee'].sudo().search([('barcode','=', map.get('emp_code'))], limit=1)
                        emp.parent_id = supervisor.id
                        
            errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
            errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message) 

        elif self.import_type == "vendor":
            self.import_contacts(1, False)

        elif self.import_type == "customer":
            self.import_contacts(0, True)

        elif self.import_type == "warehouse":
            index = 1
            warehouse_file_data = self.excel_reader(index)
            ware_err = self.generate_warehouse(warehouse_file_data)
            warehouse_errors.append(ware_err)

        elif self.import_type == "products":
            index = 0
            product_file_data = self.excel_reader(index)
            prod_err = self.generate_product(product_file_data)
            prod_errors.append(prod_err)
        
        elif self.import_type == "asset":
            index = 0
            asset_file_data = self.excel_reader(index)
            self.generate_fixed_assets(asset_file_data)
        
        elif self.import_type == "property":
            index = self.index
            property_file_data = self.excel_reader(index)
            self.generate_property_data(property_file_data)
        
    def generate_property_data(self, file_data):
        '''
        for each record, create customer (res.partner)
        manually create a column to contain project name 
        check if property exists in the project -> unitline, create the unit line in the project , else use
        the unit id
        create property sales,
        register the invoice 
        generate payment
        '''
        Project = self.env['project.configs']
        Building = self.env['building.type']
        account_move = self.env['account.move']
        account_payment = self.env['account.payment']
        Partner = self.env['res.partner']
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        errors = ['The Following messages occurred']
        for row in file_data:
            _logger.info(f'PRINTING === {row[0]}')
            # try:
            # project_name = row[1]
            customer_name = row[2]
            email = row[3]
            telephone = row[4]
            form_number = row[5]
            saletype = row[6]
            phase = row[7]
            level = row[8]
            block_no = row[9]
            shop_no = row[10]
            shop_type = row[11]
            building = row[12]
            order_date = row[13]
            unit_price = row[14]
            discount = row[15]
            net_amount = row[16]
            amount_paid = row[17]
            balance = row[18] 
            discount_percentage = 0
            if discount and int(discount) > 0:
                perc_disc= discount / unit_price
                discount_percentage =  perc_disc * 100
            # create partner
            already_exiting_so = self.env['sale.order'].search([('migrated_number', '=', row[0])], limit=1)
            if not already_exiting_so:
                if customer_name and order_date:
                    _logger.info(f'CUSTOMER2 === {customer_name}')
                    partner = Partner.create({
                        'name': customer_name, 'phone': telephone, 'email': email, 
                    })
                    # project = Project.search([('name', '=', project_name)], limit=1)
                    project = self.location_project
                    if not project:
                        raise ValidationError(f"Please Select location")
                    # building is in the form of LOCKUP SHOP (A) GF
                    # if shop_type and level and block_no:
                        # building_name = f"{shop_type.upper()} SHOP ({block_no}) {level}"
                    # building_name = self.building_name
                    # building_id = project.mapped('unit_line').filtered(lambda s: s.name == building_name)
                    building = self.buildingtype_id
                    if not building:
                        raise ValidationError(f"Please configure a building type for selected project")
                        # building = Building.create({
                        #     'name': building_name, 
                        #     'location_project': project.id,
                        #     'list_price': unit_price,
                        #     'count_unsold': 1
                        # })
                        # building.validate_building()
                    project.write({'unit_line': [(6,0, [building.id])]})
                    uom_id = self.env['uom.uom'].search([('name', '=', 'Unit(s)')])
                    date = datetime(*xlrd.xldate_as_tuple(order_date, 0))
                    values = {
                            'product_id': building.product_id.id,
                            'name': building.product_id.name or building.name,
                            'product_uom_qty': uom_id.id or 1,
                            'price_unit': unit_price,
                            'house_number': int(shop_no) if shop_no else shop_no,
                            'price_subtotal': net_amount,
                            'discount': discount_percentage,
                            }
                    vals= {
                            'partner_id': partner.id,
                            'date_order': date,
                            'sale_type': 'property',
                            'shop_type': shop_type,
                            'block_no': block_no,
                            'form_number': form_number,
                            'saletype': saletype,
                            'level': level,
                            'phase': phase,
                            'shop_no': shop_no,
                            'migrated_number': row[0],
                            'location_project': project.id, 
                            # 'payment_term_id': payment_plan_id.id,
                            'sale_status': 'Allocated',
                            'amount_paid': amount_paid,
                            'discounts': discount_percentage,
                            'outstanding': balance,
                            'order_line': [(0,0, values)],
                            'percentage_paid': (amount_paid / unit_price) * 100
                        }

                    # create property sale
                    create_sobj = self.env['sale.order'].create(vals)
                    _logger.info(f'SO CREATED IS === {create_sobj.id}')
                    create_sobj.action_confirm()
                    create_sobj.confirm_offer()
                    self.generate_invoice_and_payment(create_sobj)
                    count += 1
                    # success_records.append(fullname)
                    errors.append('Successful Import(s): '+str(count)+' Record(s):')
            # except Exception as error:
            #     unsuccess_records.append(str(row[0]))
            # errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message) 
    
    def journal_id(self, acquirer=False):
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

    def generate_invoice_and_payment(self, sale_order):
        # inv = sale_order.sudo()._create_invoices()[0]
        # inv.action_post()
        sale_payment_method = self.env['account.payment.method'].sudo().search(
                [
                    ('code', '=', 'manual'), 
                    ('payment_type', '=', 'inbound')], limit=1)
        account_journal = self.env['account.journal'].sudo()
        account_payment_obj = self.env['account.payment'].sudo()
        journal_id = self.journal_id(False)
        payment_method = account_journal.browse([journal_id]).inbound_payment_method_ids[0].id if account_journal.browse(
            [journal_id]).inbound_payment_method_ids else sale_payment_method.id if sale_payment_method else 1
        
        acc_values = {
            # 'invoice_ids': [(6, 0, [inv.id])],
            'amount': sale_order.amount_paid,
            'narration_text': '[SO REF: {}]'.format(sale_order.name),
            'reference': sale_order.name,
            'payment_type': 'inbound',
            'is_property': True,
            'partner_type': 'customer',
            # 'move_id': inv.id,
            'journal_id': journal_id,
            # 'branch_id': branch_id,
            'payment_method_id': payment_method,
            'partner_id': sale_order.partner_id.id,
        }
        payment = account_payment_obj.create(acc_values)
        payment.action_post()
        
    def confirm_notification(self,popup_message):
        view = self.env.ref('migration_usil.migration_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
                'name':'Message!',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'migration.confirm.dialog',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'new',
                'context':context,
                }

class MigrationDialogModel(models.TransientModel):
    _name="migration.confirm.dialog"
    
    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)

 