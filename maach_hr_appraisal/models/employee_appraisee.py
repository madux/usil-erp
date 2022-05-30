from datetime import datetime, timedelta
import time
import base64
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo import http
import logging
from lxml import etree

_logger = logging.getLogger(__name__)


class HrEmployeeAppraisal(models.Model):
    _name = "usl.employee.appraisal"
    _description= "Employee Appraisal"
    _order = "id desc"
    _inherit = ['mail.thread']

    name = fields.Char(string="Description", readonly=True)
    sequence = fields.Char(string="# ID", readonly=True)
    appraisal_config_id = fields.Many2one('usl.appraisal.config', 
    string="Appraisal Config ID", required=True, readonly=True)
    template_id = fields.Many2one('usl.appraisal.template', string="Template")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=False, readonly=True)
    line_manager_id = fields.Many2one('hr.employee', string="Line Manager")
    approver_ids = fields.Many2many('hr.employee', string="Approvers",readonly=True)
    department_id = fields.Many2one('hr.department', string="Department",readonly=True)
    unit_id = fields.Char(string="Unit", readonly=True)
    directed_user_id = fields.Many2one('res.users', string="Appraisal with ?", readonly=True)
    job_title = fields.Many2one('hr.job', string="Job title", readonly=True )
    date_from = fields.Date(string="Date From", readonly=True, store=True)
    date_end = fields.Date(string="Date End", readonly=True)
    deadline = fields.Date(string="Deadline Date", compute="get_appraisal_deadline")
    key_strength = fields.Text(string="Key Strengths to Continue")
    key_development = fields.Text(string="Key Development Opportunites")
    training_needs = fields.Text(string="Appraisee's training needs")
    first_level_summary = fields.Text(string="First Level Summary of assessment")
    second_level_summary = fields.Text(string="Second Level Summary of assessment")
    kpr_assessment_comment = fields.Text(string="KPR Assessment Comment")
    appraisee_comment = fields.Text(string="Appraisee's Comment")
    confirm_submission = fields.Boolean(string="Confirm Submission", default=False)
    kpi_assessment_lines = fields.Many2many(
        'usl.kpi.assessment', 
        'usl_employee_appraisal_rel_1', 
        'kpi_attitude_assessment_1_id', 
        string="KPI Questions"
        )
    kpi_attitude_assessment_lines = fields.Many2many(
        'usl.kpi.assessment', 
        'usl_employee_appraisal_rel', 
        'kpi_attitude_assessment_id', 
        string="Attitude KPI Questions"
        )
    balance_score = fields.Float(
        string="Balance Score", 
        compute="_compute_assessment_score", 
        help="Sum of balance score Total percentage in line"
        )
    attitude_appraisal_score = fields.Float(
        string="Attitude Appraisal Score",
        compute="_compute_assessment_score", 
        help="Sum of attitude appraisal Total percentage in line"
        )
    overall_total = fields.Float(
        string="Overall Total", 
        compute="_compute_overall_total"
        )
    days_remaining = fields.Integer(
        string="Days remaining", 
        compute="_compute_days_remaining"
        )
    total_score = fields.Float(
        string="Total Score", 
        help="This is the overall total - the number of queries * 5 and number of warnings * 3"
        )
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('In progress', 'In progress'),
        ('Done', 'Done'),
        ('Locked', 'Locked'),
        ('Cancel', 'Cancel'),
        ], string="Status", readonly=True)

    acceptance_status = fields.Selection([
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ], string="Acceptance Status", readonly=True)
        
    result = fields.Selection([
        ('None', 'None'),
        ('A+', 'EXCEPTIONAL PERFORMANCE'),
        ('A', 'EXCEEDS EXPECTATION'),
        ('B', 'MEETS EXPECTATION'),
        ('C', 'ABOVE AVERAGE'),
        ('D', 'NEEDS IMPROVEMENT'),
        ('E', 'UNACCEPTABLE POOR PERFORMANCE'),
    ], string="Result", default="None", readonly=True)
    result_description = fields.Char(string="Performance description", readonly=False)
    performance_band = fields.Char(string="Performance Band", readonly=True)
    ho_comment = fields.Text(string="HOU's / HOD's Comment")
    comments = fields.Text(string="General Comments")
    commendation = fields.Boolean(string="Satisfactory", default=False)
    queried = fields.Boolean(string="Queried", default=False)
    warned = fields.Boolean(string="Warning to Improve", default=False)
    dismissal = fields.Boolean(string="Dismissal", default=False)
    confirm = fields.Boolean(string="Confirm", default=False)
    absent = fields.Integer(string="Total Absent", default=0)
    edit_mode = fields.Boolean(string="Edit mode", default=False)
    appraisal_with_hr_manager = fields.Boolean(
        string="With HR manager", 
        default=False, store=True, 
        compute="compute_appraisal_with_manager")
    appraisal_with_hr_supervisor = fields.Boolean(
        string="With Supervisor", default=False, 
        store=True, compute="compute_appraisal_with_manager"
        )
    extend_probation = fields.Boolean(string="Extend probation", default=False)
    need_improvement = fields.Boolean(string="Needs Attitude Improvement", default=False)
    number_queries = fields.Integer(string="Queries")
    number_commendation = fields.Integer(string="Commendation")
    number_warning = fields.Integer(string="Warning")
    number_absent = fields.Integer(string="Absent")
    number_appraisal = fields.Integer(string="Appraisal")
    appraisal_year = fields.Char(string="Appraisal year", compute="compute_appraisal_year") 

    @api.depends('date_from')
    def compute_appraisal_year(self):
        for rec in self:
            if rec.date_from:
                rec.appraisal_year = datetime.strptime(rec.date_from.strftime('%Y-%m-%d'), '%Y-%m-%d').year
            else:
                rec.appraisal_year = False 

    @api.depends('directed_user_id')
    def compute_appraisal_with_manager(self):
        if self.directed_user_id:
            current_user = self.env['res.users'].browse([self.directed_user_id.id])
            supervisor = current_user.has_group("maach_hr_appraisal.group_supervisor")
            manager = current_user.has_group("maach_hr_appraisal.group_appraisal_manager_id")
            if supervisor:
                self.appraisal_with_hr_supervisor = True

            if manager:
                self.appraisal_with_hr_manager = True
        else:
            self.appraisal_with_hr_manager = False
            self.appraisal_with_hr_supervisor = False

    def action_rejected(self):
        if not self.employee_id.user_id.id == self.env.uid:
            raise ValidationError('Sorry!!! you are only allowed to reject your own approved Appraisal')
        self.acceptance_status = 'Rejected'

    def action_accepted(self):
        if not self.employee_id.user_id.id == self.env.uid:
            raise ValidationError('Sorry!!! you are only allowed to accepted your own approved Appraisal')
        self.acceptance_status = 'Accepted'

    def _check_validation(self):
        if self.deadline:
            if fields.Date.today() > self.appraisal_config_id.deadline:
                raise ValidationError("You are not allowed to submit because the deadline has exceeded !!!")

    def _message_post(self, template):
        """Wrapper method for message_post_with_template
        Args:
            template (str): email template
        """
        if template:
            ir_model_data = self.env['ir.model.data']
            template_id = ir_model_data.get_object_reference('maach_hr_appraisal', template)[1]
            self.message_post_with_template(
                template_id, composition_mode='comment',
                model='{}'.format(self._name), res_id=self.id,
                email_layout_xmlid='mail.mail_notification_light',
            )

    @api.depends('deadline')
    def _compute_days_remaining(self):
        for rec in self:
            if rec.deadline:
                now = datetime.now()
                deadline = datetime.strptime(
                    rec.deadline, '%Y-%m-%d')
                difference = deadline - now
                rec.days_remaining = difference.days

            else:
                rec.days_remaining = False 

    @api.depends('appraisal_config_id')
    def get_appraisal_deadline(self):
        for rec in self:
            if rec.appraisal_config_id:
                rec.deadline = rec.appraisal_config_id.deadline
            else:
                rec.deadline = False

    @api.depends('kpi_assessment_lines')
    def _compute_assessment_score(self):
        for rec in self:
            balance_tasks = rec.mapped('kpi_assessment_lines').filtered(lambda x: x.kpi_topic_id.template_id.is_attitude_appraisal == False)
            balance_total = sum([it.total_percentage for it in balance_tasks])
            rec.balance_score = balance_total * 0.6

            attitude_tasks = rec.mapped('kpi_assessment_lines').filtered(lambda x: x.kpi_topic_id.template_id.is_attitude_appraisal == True)
            attitude_total = sum([it.total_percentage for it in attitude_tasks])
            rec.attitude_appraisal_score = (attitude_total / 100) * 40

    @api.onchange('balance_score', 'attitude_appraisal_score')
    def _compute_overall_total(self):
        for rec in self:
            tasks = rec.mapped('kpi_assessment_lines')
            total = sum([it.total_percentage for it in tasks])
            scores = rec.balance_score + rec.attitude_appraisal_score
            total = scores
            rec.overall_total = total # if not rec.attitude_appraisal_score else total

    # @api.depends('overall_total')
    def _compute_result(self):
        for rec in self:
            number_queries_warning = (rec.number_queries * 5) + (rec.number_warning * 3)
            total = rec.overall_total - number_queries_warning
            self.total_score = total
            result_domain = [('min_range', '<=', total), ('max_range', '>=', total)]
            result_config = self.env['usl.appraisal.result.config'].search(result_domain, limit=1)
            if result_config:
                rec.result_description = result_config.description
                rec.result = result_config.result
                rec.performance_band = result_config.performance_band

    def action_set_progress(self):
        self.state = "In Progress"

    def action_cancel(self):
        self.state = "Cancel"

    def action_set_draft(self):
        self.state = "Draft"

    def get_url(self, id, name):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
        return "<a href={}> </b>Click<a/>. ".format(base_url)

    def action_confirm(self):
        if self.employee_id.user_id.id == self.env.uid:
            raise ValidationError('Sorry!!! you are not allow to approve your Appraisal')
        curr_emp_user = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.set_approvers(curr_emp_user)
        subject = "Appraisal Notification"
        email_to = self.employee_id.work_email
        email_cc = [rec.work_email for rec in self.approver_ids]
        msg = "Dear {}, </br>I wish to notify you that an appraisal with description, {} \
        by {} has been approved.</br> </br>Kindly {} to review </br>\
        Yours Faithfully</br>{}".format(
            self.employee_id.name,
            self.sequence, self.employee_id.name,
            self.get_url(self.id, self._name),
            self.env.user.name)
        self.action_notify(subject, msg, email_to, email_cc)
        self.state = "Done"
        self._compute_result()

    def set_approvers(self, empID=False):
        if self.env.uid != self.employee_id.user_id.id:
            curr_emp_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            if not empID:
                raise ValidationError('No employee to direct to')
            self.approver_ids = [(6, 0, [empID.id, curr_emp_user.id])]
        dir_userid = self.env['hr.employee'].search([('id', '=', empID.id)], limit=1)
        self.directed_user_id = dir_userid.user_id.id
        self.state = "In progress"

    def action_notify(self, subject, msg, email_to, email_cc):
        subject = subject
        email_from = self.env.user.email
        email_ccs = list(filter(bool, email_cc))
        reciepients = (','.join(items for items in email_ccs)) if email_ccs else False
        mail_data = {
                'email_from': email_from,
                'subject': subject,
                'email_to': email_to,
                'reply_to': email_from,
                'email_cc': reciepients,
                'body_html': msg
            }
        mail_id = self.env['mail.mail'].create(mail_data)
        self.env['mail.mail'].send(mail_id)
        self.message_post(body=msg)

    def stat_button_query(self):
        pass

    def stat_button_number_commendation(self):
        pass

    def stat_button_warning(self):
        pass

    def stat_button_absent(self):
        pass

    def stat_button_total_appraisal(self):
        pass

    def withdraw_appraisal_action(self):
        self.directed_user_id = False # self.env.user.id

    def forward_action(self):
        self._check_validation()
        dummy, view_id = self.env['ir.model.data'].get_object_reference('maach_hr_appraisal', 'memo_hr_appraisal_model_forward_wizard')
        return {
                'name': 'Forward',
                'view_type': 'form',
                'view_id': view_id,
                "view_mode": 'form',
                'res_model': 'memo.appraisal.foward.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_memo_record': self.id,
                    'default_resp': self.env.uid,
                    'default_type': "forward",
                },
            }

    def return_action(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('maach_hr_appraisal', 'memo_hr_appraisal_model_forward_wizard')
        return {
                'name': 'Return',
                'view_type': 'form',
                'view_id': view_id,
                "view_mode": 'form',
                'res_model': 'memo.appraisal.foward.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_memo_record': self.id,
                    'default_type': "return",
                    'default_resp': self.env.uid,
                },
            }

    def add_queries(self):
        '''This increment number of queries by 1 and also deducts 5 from the overall total which
        affects the perfomance bond / result
        '''
        self.number_queries = self.number_queries + 1

    def remove_queries(self):
        '''This decrement number of queries by 1
        '''
        if self.number_queries > 0:
            self.number_queries = self.number_queries - 1

    def add_warning(self):
        '''This increment number of warnings by 1 and also deducts 3 from the overall total which
        affects the perfomance bond / result
        '''
        self.number_warning = self.number_warning + 1

    def remove_warning(self):
        if self.number_warning > 0:
            self.number_warning = self.number_warning - 1

    @api.model
    def fields_view_get(self, view_id='maach_hr_appraisal.usl_employee_appraisal_form_view', view_type='form', toolbar=False, submenu=False):
        res = super(HrEmployeeAppraisal, self).fields_view_get(view_id=view_id,
                                                      view_type=view_type,
                                                      toolbar=toolbar,
                                                      submenu = submenu)
        doc = etree.XML(res['arch'])
        for rec in self: #.approver_ids:
            if rec.directed_user_id.id == self.env.uid:
                for node in doc.xpath("//button[@name='forward_action']"):
                    node.set('modifiers', '{"invisible": false}')

            if rec.employee_id.user_id.id == self.env.uid:
                for node in doc.xpath("//button[@name='return_action']"):
                    node.set('modifiers', '{"invisible": true}')

                for node in doc.xpath("//button[@name='withdraw_appraisal_action']"):
                    node.set('modifiers', '{"invisible": true}')

        res['arch'] = etree.tostring(doc)
        return res

    def unlink(self):
        for record in self.filtered(lambda record: record.state not in ['Draft','Cancel']):
            raise ValidationError(_('In order to delete an Appraisal, you must cancel it first...'))
        return super(HrEmployeeAppraisal, self).unlink()
 
    def write(self, vals):
        """
        Any time an approver changes this options, 
        the system adds 1 if True else deducts 1
        This is used to count the number of queries, 
        warning by any approver
        """
        # for rec in self:
        # self.validate_user_edit()
        res = super(HrEmployeeAppraisal, self).write(vals)
        if 'queried' in vals and vals.get('queried') == True:
            self.update({'number_queries': self.number_queries + 1})
        if 'warned' in vals and vals.get('warned') == True:
            self.update({'number_warning': self.number_warning + 1})
        if 'commendation' in vals and vals.get('commendation') == True:
            self.update({'number_commendation': self.number_commendation + 1})
        if 'absent' in vals and vals.get('absent') == True:
            self.update({'number_absent': self.number_absent + 1})
        return res

