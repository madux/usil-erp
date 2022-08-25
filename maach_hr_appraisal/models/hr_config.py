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


class HrAppraisalConfig(models.Model):
    _name = "usl.appraisal.config"
    _description= "Appraisal Setup: Main appraisal setup model"
    _order = "id desc"
    _inherit = ['mail.thread']

    """Simply select the category, add the template, add the KPI question lines"""

    sequence = fields.Char(string="# ID")
    name = fields.Char(string="Description")
    date_from = fields.Date(string="Date From", required=True)
    date_end = fields.Date(string="Date End", required=True)
    deadline = fields.Date(string="Deadline Date")
    hr_category_id = fields.Many2one(
        'usl.hr.category', 
        string="HR Category", 
        required=True,
        )
    employee_appraisal_ids = fields.Many2many(
        'usl.employee.appraisal', 
        string="Employee Appraisals", 
        readonly=True
        )
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('In progress', 'In progress'),
        ('Done', 'Done'),
        ('Cancel', 'Cancel'),
        ], string="Status", default = "Draft", readonly=True)

    # TODO DELETE The below fields
    template_ids = fields.Many2many(
        'usl.appraisal.template', 
        string="Template", 
        required=False
        )
    kpi_question_lines = fields.Many2many(
        'usl.kpi.questions', 
        'usl_kpi_questions_id', 
        'usl_appraisal_config_id',
        string="KPI Questions", store=True
        )

    @api.onchange('date_end')
    def _onchange_end_date(self):
        if self.date_from and self.date_end:
            if self.date_end < self.date_from:
                self.date_end = False 
                raise ValidationError('End date cannot be lesser than start date')

    def action_cancel_appraisal(self):
        for rec in self.employee_appraisal_ids:
            rec.state = "Cancel"
        self.state = "Cancel"

    def action_close_appraisal(self):
        for rec in self.employee_appraisal_ids:
            rec.state = "Done"
        self.state = "Done"

    def action_reopen_appraisal(self):
        for rec in self.employee_appraisal_ids:
            rec.state = "In progress"
        self.state = "In progress"

    def action_confirm(self):
        """
        Get list of all employees that falls in the select hr category job roles
        and create an employee appraisal record for them

        """
        appraisal = self.env['usl.employee.appraisal']
        already_existing_appr_records = appraisal.search([('appraisal_config_id', '=', self.id)], limit=1)
        if already_existing_appr_records and self.state in ["Draft"]:
            raise ValidationError("You cannot send an already existing appraisal")
        job_titles = [rec.id for rec in self.hr_category_id.mapped('job_roles')]
        employees = self.env['hr.employee'].search([('job_id', 'in', job_titles)])
        apr_lines = []
        if employees:
            for employee in employees:
                val = {
                    'name': self.name,
                    'appraisal_config_id': self.id,
                    # 'template_id': self.template_id.id,
                    'employee_id': employee.id,
                    'department_id': employee.department_id.id,
                    'job_title': employee.job_id.id,
                    'date_from': self.date_from,
                    'date_end': self.date_end,
                    'deadline': self.deadline,
                    'kpi_assessment_lines': [(6, 0, self._prepare_assessment_line(employee))],
                    # 'kpi_attitude_assessment_lines': ';',
                    'state': 'Draft',
                    'sequence': self.sequence,
                }
                emp_appraisal = appraisal.create(val)

                subject = "Appraisal Notification"
                email_to = employee.work_email
                email_cc = [employee.work_email]
                msg = """Dear {}, </br>I wish to notify you that your appraisal starts Now.
                </br> </br>Kindly {} to review </br>\
                Yours Faithfully</br>{}""".format(
                    employee.name,
                    emp_appraisal.get_url(emp_appraisal.id, emp_appraisal._name),
                    self.env.user.name)
                emp_appraisal.action_notify(subject, msg, email_to, email_cc)
                apr_lines.append(emp_appraisal.id)
                employee.appraisal_ids = [(6, 0, [emp_appraisal.id])]
            self.employee_appraisal_ids = [(6, 0, apr_lines)]
            self.state = "In progress"
        else:
            raise ValidationError('No Employee found under the Selected category - {} and job roles such as {}'.format(self.hr_category_id.name, [rec.name for rec in self.hr_category_id.job_roles]))

    def _prepare_assessment_line(self, employee):
        assessment_list = []
        if self.hr_category_id:
            category_lines = self.hr_category_id.mapped('category_template_ids')
            for cat_lines in category_lines:
                topic_lines = cat_lines.mapped('hr_topic_ids')
                for topc in topic_lines:
                    vals = {
                        'employee_id': employee.id,
                        'kpi_topic_id': topc.id,
                        }

                    assessment = self.env['usl.kpi.assessment'].create(vals)
                    assessment_list.append(assessment.id)

                    question_lines = topc.mapped('kpi_question_lines')

                    """Check which is default question and set it as default"""
                    for ques in question_lines:
                        if ques.is_default:
                            line_val = {
                                    'name': ques.name,
                                    'is_default': ques.is_default,
                                    'is_checkbox': ques.is_checkbox,
                                    'is_text': ques.is_text,
                                    'answer_text': ques.answer_text,
                                    'kpi_topic_id': topc.id,
                                    'template_id': topc.template_id.id,
                                    'employee_free_text': topc.employee_free_text,
                                    'kpi_answers_assessment_id': assessment.id
                                }
                            self.env['usl.kpi.answers'].create(line_val)
            return assessment_list

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('usl.appraisal.config')
        vals['sequence'] = sequence or '/'
        return super(HrAppraisalConfig, self).create(vals)


class UslKPIAssessment(models.Model):
    _name = "usl.kpi.assessment"
    _description= "Appraisal Assessment"
    _order = "id desc"

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    kpi_topic_id = fields.Many2one('usl.kpi.topic', string="BSC Perspective")
    template_name = fields.Char(string="Template", related="kpi_topic_id.template_id.name")
    employee_free_text = fields.Boolean(
        string="Is Employee Free Text", 
        related="kpi_topic_id.employee_free_text"
        )
    kpi_answers_ids = fields.One2many(
        'usl.kpi.answers', 
        'kpi_answers_assessment_id', 
        string="Answers"
        )
    total_supervisor_score = fields.Integer(
        string="Total Supervior Score", 
        compute="_compute_kpi_question",
        store=True
        )
    no_of_task = fields.Integer(
        string="No. of Task", 
        compute="_compute_kpi_question", 
        store=True
        )
    input_percentage_of_task = fields.Integer(
        string="Input % of Task", 
        compute="_compute_input_percentage_of_task", 
        store=True)
    percentage_of_task = fields.Integer(
        string="% of Task",
        compute="_compute_percentage_of_task", 
        default=1, 
        help="No. of Task * Input % of Task ",
        store=True)
    total_percentage = fields.Float(
        string="Total Percentage", 
        compute="_compute_total_percentage", 
        store=True, 
        help="(Total Supervior Score / % of Task) * Weight of topic",
        digits = (12,2)
        )
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('In progress', 'In progress'),
        ('Done', 'Done'),
        ('Cancel', 'Cancel'),
        ], string="Status", default = "Draft", readonly=True)

    @api.constrains('kpi_answers_ids')
    def _check_validation(self):
        if self.kpi_topic_id.employee_free_text and self.kpi_topic_id.max_line_number > 0.00:
            if len(self.mapped('kpi_answers_ids')) > self.kpi_topic_id.max_line_number:
                raise ValidationError('Maximum number of lines must not be greater than {}'.format(self.kpi_topic_id.max_line_number))

    @api.depends('percentage_of_task', 'total_supervisor_score')
    def _compute_total_percentage(self):
        for rec in self:
            total_amt = 0.00
            if rec.percentage_of_task > 0:
                total_amt = float(rec.total_supervisor_score) / float(rec.percentage_of_task)
                total_amt = float(rec.kpi_topic_id.weight) * total_amt
            rec.total_percentage = total_amt

    @api.depends('kpi_answers_ids')
    def _compute_kpi_question(self):
        for rec in self:
            tasks = rec.mapped('kpi_answers_ids')
            rec.no_of_task = len(tasks)
            kpi_score = sum([it.supervisor_score for it in tasks])
            rec.total_supervisor_score = kpi_score

    @api.depends('no_of_task','input_percentage_of_task')
    def _compute_percentage_of_task(self):
        for rec in self:
            rec.percentage_of_task = rec.no_of_task * rec.input_percentage_of_task

    @api.depends('kpi_topic_id')
    def _compute_input_percentage_of_task(self):
        for rec in self:
            rec.input_percentage_of_task = rec.kpi_topic_id.input_percentage_of_task


class UslResultConfig(models.Model):
    _name = "usl.appraisal.result.config"
    _rec_name = "performance_band"
    _description = "Holds the table for configuration of results"

    description = fields.Text(string="Performance description", readonly=False)
    min_range = fields.Integer(string="Min Range", required=True)
    max_range = fields.Integer(string="Max Range", required=True)
    performance_band = fields.Char(string="Performance Band", required=True)
    result = fields.Selection([
        ('None', 'None'),
        ('A+', 'EXCEPTIONAL PERFORMANCE'),
        ('A', 'EXCEEDS EXPECTATION'),
        ('B', 'MEETS EXPECTATION'),
        ('C', 'ABOVE AVERAGE'),
        ('D', 'NEEDS IMPROVEMENT'),
        ('E', 'UNACCEPTABLE POOR PERFORMANCE'),
    ], string="Result", default="None", required=True)

