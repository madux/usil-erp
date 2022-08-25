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


class HrKPIAnswers(models.Model):
    _name = "usl.kpi.answers"
    _description= "KPI Answers: This holds the table or lines that employers can provide there own answers"
    _order = "id desc"

    name = fields.Char(string="Name")
    is_checkbox = fields.Boolean(string="Is Checkbox", default=False)
    answer_checkbox = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="Answer", default=False)
    is_text = fields.Boolean(string="Is Text", default=False)
    answer_text = fields.Text(string="Describe", size=25)
    is_default = fields.Boolean(string="Is Default", default=False)
    kpi_topic_id = fields.Many2one('usl.kpi.topic', string="BSC Perspective")
    template_id = fields.Many2one('usl.appraisal.template', string="Related Template")
    kpi_answers_assessment_id = fields.Many2one('usl.kpi.assessment', string="Assessment ID")
    supervisor_comments = fields.Char(string="Supervisor Comment")
    supervisor_score = fields.Float(string="Supervisor Score", default=0.0)
    assessment_date = fields.Date(string="Assessment Date")
    employee_free_text = fields.Boolean(string="Is Employee Free Text", default=False)
    is_own_assessment = fields.Boolean(string="My own details", default=False, compute="compute_own_appraisal")
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('In progress', 'In progress'),
        ('Done', 'Done'),
        ('Cancel', 'Cancel'),
        ], string="Status", default = "Draft", readonly=True)

    @api.depends('kpi_answers_assessment_id')
    def compute_own_appraisal(self):
        for rec in self:
            if rec.kpi_answers_assessment_id:
                if self.env.uid == rec.kpi_answers_assessment_id.employee_id.user_id.id:
                    rec.is_own_assessment = True
                else:
                    rec.is_own_assessment = False
            else:
                rec.is_own_assessment = False

    @api.onchange('supervisor_score')
    def update_assessment_date(self):
        if self.supervisor_score:
            supervisor_score = int(self.supervisor_score)
            if supervisor_score not in range(0, 6):
                self.supervisor_score = False
                return {
                        'warning': {
                            'title': "Validation Error!",
                            'message': "Supervisors score should be in range of 1 - 5"
                        }
                        }
            self.assessment_date = fields.Date.today()
        else:
            self.assessment_date =  False 

    @api.constrains('supervisor_score')
    def _check_validation(self):
        for rec in self:
            supervisor_score = int(rec.supervisor_score)
            if supervisor_score not in range(0, 6):
                raise ValidationError('Supervisors score should be in range of 1.0 - 5.0')


class HrKPIQuestions(models.Model):
    _name = "usl.kpi.questions"
    _description= "KPI Questions: this holds table for questions"
    _order = "id desc"

    name = fields.Char(string="Question", required=True)
    is_checkbox = fields.Boolean(string="Is Checkbox", default=False)
    answer_checkbox = fields.Selection([('Yes', 'Yes'), ('No', 'No')], 
    string="Answer", default=False, help="Visible if is is checkbox is enabled")
    is_text = fields.Boolean(string="Is Text", default=False, help="If the question is a text field")
    answer_text = fields.Text(string="Describe", size=25, help="Visible if is text is enabled")
    is_default = fields.Boolean(
        string="Is Default", default=False, 
        help="If set, the question will appear by default on appraisal")
    kpi_topic_id = fields.Many2one('usl.kpi.topic', string="BSC Perspective")
    template_id = fields.Many2one('usl.appraisal.template', string="Related Template")
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('In progress', 'In progress'),
        ('Done', 'Done'),
        ('Cancel', 'Cancel'),
        ], string="Status", default = "Draft", readonly=True)

    @api.onchange('is_checkbox', 'is_text')
    def toggle_fields(self):
        if self.is_checkbox:
            self.is_text = False
            self.answer_text = False
        elif self.is_text:
            self.is_checkbox = False
            self.answer_checkbox = False


class HrKPITopic(models.Model):
    _name = "usl.kpi.topic"
    _description= "KPI Topic: Appraisal topics"
    _order = "id desc"

    name = fields.Char(string="Name", required=False)
    kpi_question_lines = fields.One2many(
        'usl.kpi.questions', 
        'kpi_topic_id', 
        string="KPI Questions"
        )
    weight = fields.Float(string="Weight", required=False)
    employee_free_text = fields.Boolean(string="Is Employee Free Text", default=False)
    max_line_number = fields.Float(string="Maximum Number of Input")
    template_id = fields.Many2one('usl.appraisal.template', string="Related Template")
    hr_category_id = fields.Many2one('usl.hr.category', string="Related HR Category ID")  # Use to filter only category records

    input_percentage_of_task = fields.Integer(string="Input % of Task", default=1)
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('In progress', 'In progress'),
        ('Done', 'Done'),
        ('Cancel', 'Cancel'),
        ], string="Status", default = "Draft", readonly=True)

    @api.constrains('kpi_question_lines', 'weight')
    def _check_lines(self):
        if not self.employee_free_text and not self.mapped('kpi_question_lines'):
            raise ValidationError('You must provide at least one KPI Question for these topic')
        if self.weight < 1:
            raise ValidationError('Weight must be greater than 0')


class UslHrCategoryTemplate(models.Model):
    _name = "usl.hr.category"
    _description= "HR Appraisal Category: The category of appraisals based on job roles"

    name = fields.Char(string="Name", placeholder="OFFICER - MGR", required=True)
    job_roles = fields.Many2many('hr.job', string="Job role")
    category_template_ids = fields.One2many(
        'usl.category.template.line', 
        'hr_category_id', 
        string="Template"
        )

    @api.constrains('job_roles', 'category_template_ids')
    def _check_lines(self):
        if not self.mapped('job_roles'):
            raise ValidationError('You must assign at least one job role')

        if not self.mapped('category_template_ids'):
            raise ValidationError('You must select a template')


class HrCategoryTemplate(models.Model):
    _name = "usl.category.template.line"

    hr_template_id = fields.Many2one(
        'usl.appraisal.template', 
        string="Template", 
        required=True
        )
    hr_topic_ids = fields.Many2many(
        'usl.kpi.topic', 
        'category_template_topic_rel', 
        'category_template_topic_id', 
        string="Topics", 
        required=True
        )
    hr_category_id = fields.Many2one(
        'usl.hr.category', 
        string="Related HR Category ID"
        )


class HrAppraisalTemplate(models.Model):
    _name = "usl.appraisal.template"
    _description= "Appraisal template"
    _inherit = ['mail.thread']
    _order = "id desc"

    name = fields.Char(string="Name", required=True) # e.g financial perspective
    # Once selected, system checks if the topic is_attitude_appraisal
    is_attitude_appraisal = fields.Boolean(string="Is Attitude Appraisal", default=False)

    # TODO To be removed
    hr_category_ids = fields.Many2many('usl.hr.category', string="HR Category")
    total_weight = fields.Float(string="Total Weight") #
    kpi_topic_lines = fields.Many2many(
        'usl.kpi.topic', 
        'usl_appraisal_kpi_topic_id', 
        'usl_appraisal_template_id',
        string="KPI Settings", 
        required=False
        )
    hr_category_id = fields.Many2one(
        'usl.hr.category', 
        string="Related HR Category ID"
        )
