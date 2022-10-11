from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http
import random
from lxml import etree

import logging

_logger = logging.getLogger(__name__)

class Memo_Model(models.Model):
    _name = "memo.model"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"
    _order = "id desc"
    
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('memo.model')
        vals['code'] = str(sequence)
        return super(Memo_Model, self).create(vals)

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].sudo().read_group([
            ('res_model', '=', 'memo.model'), 
            ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for rec in self:
            rec.attachment_number = attachment.get(rec.id, 0)

    def action_get_attachment_view(self):
        self.ensure_one()
        # res = self.env['ir.actions.act_window'].xml_id('base', 'action_attachment')
        res = self.sudo().env.ref('base.action_attachment')
        res['domain'] = [('res_model', '=', 'memo.model'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'memo.model', 'default_res_id': self.id}
        return res
    
    # default to current employee using the system 
    def _default_employee(self):
        return self.env.context.get('default_employee_id') or \
        self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def _default_user(self):
        return self.env.context.get('default_user_id') or \
         self.env['res.users'].search([('id', '=', self.env.uid)], limit=1)

    memo_type = fields.Selection(
        [
        ("Payment", "Payment"), 
        ("loan", "Loan"), 
        ("Internal", "Internal Memo")
        ], string="Memo Type",default="Internal", required=True)

    name = fields.Char('Subject', size=400)
    code = fields.Char('Code', readonly=True)
    employee_id = fields.Many2one('hr.employee', string = 'Employee', default =_default_employee) 
    direct_employee_id = fields.Many2one('hr.employee', string = 'Employee') 
    set_staff = fields.Many2one('hr.employee', string = 'Employee')
    demo_staff = fields.Integer(string='User', compute="get_user_staff",
                                default=lambda self: self.env['res.users'].search([('id', '=', self.env.uid)], limit=1).id)
        
    user_ids = fields.Many2one('res.users', string = 'Beneficiary', default =_default_user)
    dept_ids = fields.Many2one('hr.department', string ='Department', 
    compute="employee_department", readonly = True, store =True)
    description = fields.Char('Note')
    project_id = fields.Many2one('account.analytic.account', 'Project')
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    amountfig = fields.Float('Budget Amount', store=True, default=1.0)
    description_two = fields.Text('Reasons')
    reason_back = fields.Char('Return Reason')
    file_upload = fields.Binary('File Upload')
    file_namex = fields.Char("FileName")
    state = fields.Selection([('submit', 'Draft'),
                                ('Sent', 'Sent'),
                                ('Approve', 'Waiting For Payment / Confirmation'),
                                ('Approve2', 'Memo Approved'),
                                ('Done', 'Done'),
                                ('refuse', 'Refused'),
                              ], string='Status', index=True, readonly=True,
                             copy=False, default='submit',
                             required=True,
                             help='Request Report state')
    date = fields.Datetime('Request Date', default=fields.Datetime.now())
    invoice_id = fields.Many2one(
        'account.move', 
        string='Invoice', 
        store=True,
        domain="[('move_type', '=', 'in_invoice'), ('state', '!=', 'cancel')]"
        )
    status_progress = fields.Float(string="Progress(%)", compute='_progress_state')
    users_followers = fields.Many2many('hr.employee', string='Add followers') #, default=_default_employee)
    res_users = fields.Many2many('res.users', string='Approvers') #, default=_default_employee)
    comments = fields.Text('Comments', default="-")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='No. Attachments')
    partner_id = fields.Many2many('res.partner', string='Related Partners')

    # Loan fields
    loan_type = fields.Selection(
        [
            # ("fixed-annuity", "Fixed Annuity"),
            # ("fixed-annuity-begin", "Fixed Annuity Begin"),
            ("fixed-principal", "Fixed Principal"),
            ("interest", "Only interest"),
        ],
        required=False,
        help="Method of computation of the period annuity",
        readonly=True,
        states={"submit": [("readonly", False)]},
        default="interest",
    )

    loan_amount = fields.Monetary(
        currency_field="currency_id",
        required=False,
        readonly=True,
        states={"submit": [("readonly", False)]},
    )

    currency_id = fields.Many2one(
        "res.currency", default= lambda self: self.env.user.company_id.currency_id.id, readonly=True,
    )

    periods = fields.Integer(
        required=False,
        readonly=True,
        states={"submit": [("readonly", False)]},
        help="Number of periods that the loan will last",
        default=12,
    )
    method_period = fields.Integer(
        string="Period Length (years)",
        default=1,
        help="State here the time between 2 depreciations, in months",
        required=False,
        readonly=True,
        states={"submit": [("readonly", False)]},
    )
    start_date = fields.Date(
        help="Start of the moves",
        readonly=True,
        states={"submit": [("readonly", False)]},
        copy=False,
    )
    loan_reference = fields.Integer(string="Loan Ref")
    active = fields.Boolean('Active', default=True)
    
    @api.model
    def fields_view_get(self, view_id='company_memo.memo_model_form_view_3', view_type='form', toolbar=False, submenu=False):
        res = super(Memo_Model, self).fields_view_get(view_id=view_id,
                                                      view_type=view_type,
                                                      toolbar=toolbar,
                                                      submenu = submenu)
        doc = etree.XML(res['arch']) 
        # users = self.env['memo.model'].search([('user_id', 'in', self.users_followers.user_id.id)])
        for rec in self.res_users:
            if rec.id == self.env.uid:
                for node in doc.xpath("//field[@name='users_followers']"):
                    node.set('modifiers', '{"readonly": true}') 
                    
                for node in doc.xpath("//button[@name='return_memo']"):
                    node.set('modifiers', '{"invisible": true}')
        res['arch'] = etree.tostring(doc)
        return res

    @api.onchange('invoice_id')
    def get_amount(self):
        if self.invoice_id and self.invoice_id.state in ['posted', 'cancel']:
            self.invoice_id = False 
            return {
                'warning': {
                    'title': "Validation",
                    'message': "You selected an invoice that is either cancelled or posted already",
                }
            }
        self.amountfig = self.invoice_id.amount_total
         
    @api.depends('set_staff')
    def get_user_staff(self):
        if self.set_staff:
            self.demo_staff = self.set_staff.user_id.id
        else:
            self.demo_staff = False
        
    # @api.one
    # def write(self, vals):
    #     res = super(Memo_Model, self).write(vals)
    #     if self.state != "submit":
    #         for rec in self.res_users:
    #             if rec.id == self.env.uid:
    #                 raise ValidationError('You are not allowed to Edit this document')
    #         return res

    def print_memo(self):
        report = self.env["ir.actions.report"].search(
            [('report_name', '=', 'company_memo.memomodel_print_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env.ref('company_memo.print_memo_model_report').report_action(self)
     
    def set_draft(self):
        for rec in self:
            rec.write({'state': "submit", 'direct_employee_id': False})
     
    def user_done_memo(self):
        for rec in self:
            rec.write({'state': "Done"})
     
    def Cancel(self):
        if self.employee_id.user_id.id != self.env.uid:
            raise ValidationError('Sorry!!! you are not allowed to cancel a memo not initiated by you.') 
        
        if self.state not in ['refuse', 'Sent']:
            raise ValidationError('You cannot cancel a memo that is currently undergoing management approval')
        for rec in self:
            rec.write({
                'state': "submit", 
                'direct_employee_id': False, 
                'partner_id':False, 
                'users_followers': False,
                'set_staff': False,
                })

    def get_url(self, id, name):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
        return "<a href={}> </b>Click<a/>. ".format(base_url)
    
    # get the employee's department
    @api.depends('employee_id')
    def employee_department(self):
        if self.employee_id:
            self.dept_ids = self.employee_id.department_id.id
        else:
            self.dept_ids = False

               
    """line 4 - 7 checks if the current user is the initiator of the memo, if true, raises warning error
    else: it opens the wizard"""

    def validator(self, msg):
        if self.employee_id.user_id.id == self.env.user.id:
            raise ValidationError("Sorry you are not allowed to reject /  return you own initiated memo") 
        # users = self.env['res.users'].browse([self.env.uid])
         
        # usr = self.mapped('res_users').filtered(lambda x: x.id == self.env.user.id)
        # if usr:
        #     raise ValidationError(msg)

    def forward_memo(self): 
        if self.state == "submit":
            if not self.env.user.id == self.employee_id.user_id.id:#  or self.env.uid != self.create_uid:
                raise ValidationError('You cannot forward a memo at draft state because you are not the initiator')
        users = self.env['res.users'].browse([self.env.uid])
        manager = users.has_group("company_memo.mainmemo_manager")
        admin = users.has_group("base.group_system")
        dummy, view_id = self.env['ir.model.data'].get_object_reference('company_memo', 'memo_model_forward_wizard')
        #usr = self.mapped('res_users').filtered(lambda x: x.id == self.env.user.id)
        #if usr:
         #   raise ValidationError('You have initially forwarded this document. Kindly reject, cancel or Wait for aproval')
        #else:
        return {
                'name': 'Forward Memo',
                'view_type': 'form',
                'view_id': view_id,
                "view_mode": 'form',
                'res_model': 'memo.foward',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_memo_record': self.id,
                    # 'default_date': self.date, 
                    'default_resp': self.env.uid,  
                },
            }
    """The wizard action passes the employee whom the memo was director to this function."""

    def forward_memos(self, employee, comments): # Always available,  
        user_id = self.env['res.users'].search([('id','=',self.env.user.id)])
        lists2 = [y.partner_id.id for x in self.users_followers for y in x.user_id]
        # self.write({'partner_id': [(4, lists2)]}) 
        type = "loan request" if self.memo_type == "loan" else "memo"
        Beneficiary = self.employee_id.name or self.user_ids.name
        body_msg = f"""Dear {self.direct_employee_id.name}, \n \
        </br>I wish to notify you that a {type} with description, {self.name},</br>  
        from {Beneficiary} (Department: {self.employee_id.department_id.name or "-"}) \
        was sent to you for review / approval. </br> </br>Kindly {self.get_url(self.id, self._name)} \
        </br> Yours Faithfully</br>{self.env.user.name}""" 
        self.mail_sending_direct(body_msg)
        self.direct_employee_id = False 
        body = "%s for %s initiated by %s, moved by- ; %s and sent to %s" %(type, self.name, Beneficiary, self.env.user.name, employee)
        body_main = body + "\n with the comments: %s" %(comments)
        self.follower_messages(body_main)
          
    def mail_sending_direct(self, body_msg): 
        subject = "Memo Notification"
        email_from = self.env.user.email
        mail_to = self.direct_employee_id.work_email
        emails = (','.join(str(item2.work_email) for item2 in self.users_followers))
        mail_data = {
                'email_from': email_from,
                'subject': subject,
                'email_to': mail_to,
                'reply_to': email_from,
                'email_cc': emails if self.users_followers else [],
                'body_html': body_msg
            }
        mail_id = self.env['mail.mail'].create(mail_data)
        self.env['mail.mail'].send(mail_id)
    
    def _get_group_users(self):
        followers = []
        account_id = self.env.ref('company_memo.mainmemo_account')
        acc_group = self.env['res.groups'].search([('id', '=', account_id.id)], limit=1)
        for users in acc_group.users:
            employee = self.env['hr.employee'].search([('user_id', '=', users.id)])
            for rex in employee:
                followers.append(rex.id)
        return self.write({'users_followers': [(4, follow) for follow in followers]})

    def approve_memo(self): # Always available to Some specific groups
        users = self.env['res.users'].browse([self.env.uid])
        manager = users.has_group("company_memo.mainmemo_manager")
        if not manager:
            if self.env.uid == self.employee_id.user_id.id:
                raise ValidationError('You are not Permitted to approve a Payment Memo.\
                Forward it to the authorized Person')
         
        body = "MEMO APPROVE NOTIFICATION: -Approved By ;\n %s on %s" %(self.env.user.name,fields.Date.today())
        type = "loan request" if self.memo_type == "loan" else "memo"
        body_msg = f"""Dear {self.employee_id.name}, </br>I wish to notify you that a {type} with description, '{self.name}',\
                from {self.employee_id.department_id.name or self.user_ids.name} department have been approved by {self.env.user.name}.</br>\
                Accountant's/ Respective authority should take note. \
                </br>Kindly {self.get_url(self.id, self._name)} </br>\
                Yours Faithfully</br>{self.env.user.name}"""

        users = self.env['res.users'].browse([self.env.uid])
        if self.state == "Approve":
            raise ValidationError("Sorry!!! this record have already been approved.")
        
        if self.memo_type in ["Payment", 'loan']:
            self.state = "Approve"
            self.write({'res_users': [(4, users.id)]})
        elif self.memo_type == "Internal":
            self.state = "Done"
            self.write({'res_users': [(4, users.id)]})
        self.mail_sending_direct(body_msg)
        self.follower_messages(body)
    
    def user_approve_memo(self): # Always available to Some specific groups
        if self.memo_type == "Internal":
            type = "loan request" if self.memo_type == "loan" else "memo"
            body = "%s APPROVAL NOTIFICATION: -Approved By ;\n %s on %s" %(type.capitalize(), self.env.user.name, fields.Date.today())
            bodyx = "Dear {}, </br>I wish to notify you that a {} with description, '{}',\n \
                    from {} department have been approved by {}. Kindly review. </br> </br>Kindly {} </br>\
                    Yours Faithfully</br>{}".format(self.employee_id.name, type,
                                                self.name, self.employee_id.department_id.name, self.env.user.name,
                                                self.get_url(self.id, self._name), self.env.user.name)
            
            users = self.env['res.users'].browse([self.env.uid])
            user = users.has_group("company_memo.mainmemo_officer")
            manager = users.has_group("company_memo.mainmemo_manager")
            acc = users.has_group("company_memo.mainmemo_account")
            msg = """You are not Permitted to approve a Payment Memo.\n Kindly Forward it to the authorized Person"""
            if not manager:
                raise ValidationError(msg)
            else:
                self.approve_memo()
        else:
            raise ValidationError('To use this feature, ensure the Memo Type is not a payment memo')
        
    def follower_messages(self, body):
        # body= "RETURN NOTIFICATION;\n %s" %(self.reason_back)
        body = body
        records = self._get_followers()
        followers = records
        self.message_post(body=body)
        # self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)

    def Register_Payment(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('account', 'view_account_payment_form')
        # if not self.vendor_id:
        #     raise ValidationError("Please select a Vendor")
        if (self.memo_type != "Payment") or (self.amountfig < 1):
            raise ValidationError("(1) Memo type must be 'Payment'\n (2) Amount must be greater than one to proceed with payment")
        #self.state = "Done"
        ret = {
                'name':'Register Memo Payment',
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'domain': [],
                'context': {
                        'default_amount': self.amountfig,
                        'default_payment_type': 'outbound',
                        'default_partner_id':self.vendor_id.id or self.employee_id.user_id.partner_id.id, 
                        'default_memo_reference': self.id,
                        'default_communication': self.name,
                },
                'target': 'current'
                }
        return ret

    def generate_loan_entries(self):
        if self.loan_reference:
            raise ValidationError("You have generated a loan already for this record")
        # view_id = self.env['ir.model.data'].get_object_reference('account_loan', 'account_loan_form')
        view_id = self.env.ref('account_loan.account_loan_form')
        if (self.memo_type != "loan") or (self.loan_amount < 1):
            raise ValidationError("Check validation: \n (1) Memo type must be 'loan request'\n (2) Loan Amount must be greater than one to proceed with loan request")
        # try:
        ret = {
            'name':'Generate loan request',
            'view_mode': 'form',
            'view_id': view_id.id,
            'view_type': 'form',
            'res_model': 'account.loan',
            'type': 'ir.actions.act_window',
            'domain': [],
            'context': {
                    'default_loan_type': self.loan_type,
                    'default_loan_amount': self.loan_amount,
                    'default_periods':self.periods or 12,  
                    'default_partner_id':self.employee_id.user_id.partner_id.id,  
                    'default_method_period':self.method_period,  
                    'default_rate': 15, 
                    'default_start_date':self.start_date, 
                    'default_name': self.code,
            },
            'target': 'current'
            }
        return ret
        # except Exception as e:
        #     _logger.info(f"Issue with Account loan ==> {e}") 

    def migrate_records(self):
        account_ref = self.env['account.payment'].search([])
        for rec in account_ref:
            memo_rec = self.env['memo.model'].search([('code', '=', rec.communication)])
            if memo_rec:
                memo_rec.state = "Done"
        
    def return_memo(self):
        msg = "You have initially forwarded this memo. Kindly use the cancel button or wait for approval"
        self.validator(msg)
        default_sender = self.mapped('res_users')
        last_sender = self.env['hr.employee'].search([('user_id', '=', default_sender[-1].id)]).id if default_sender else False
        # raise ValidationError([rec.name for rec in default_sender])
        return {
              'name': 'Reason for Return',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'memo.back',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_memo_record': self.id,
                  'default_date': self.date,
                  'default_direct_employee_id': last_sender,
                  'default_resp':self.env.uid,
              },
        }
    
    @api.depends('state')
    # Depending on any field change (ORM or Form), the function is triggered.
    def _progress_state(self):
        for order in self:
            if order.state in ["submit", "refuse"]:
                order.status_progress = random.randint(0, 5)

            elif order.state == "Sent":
                order.status_progress = random.randint(20, 60)

            elif order.state == "Approve":
                order.status_progress = random.randint(71, 95)
                
            elif order.state == "Approve2":
                order.status_progress = random.randint(71, 98)
                
            elif order.state == "Done":
                order.status_progress = random.randint(98, 100)
            else:
                order.status_progress = random.randint(99, 100) # 100 / len(order.state)

    def unlink(self):
        for delete in self.filtered(lambda delete: delete.state in ['Sent','Approve2', 'Approve']):
            raise ValidationError(_('You cannot delete a Memo which is in %s state.') % (delete.state,))
        return super(Memo_Model, self).unlink()

    
