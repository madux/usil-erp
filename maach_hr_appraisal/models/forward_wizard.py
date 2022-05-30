from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo import http


class Forward_Appraisal_Wizard(models.TransientModel):
    _name = "memo.appraisal.foward.wizard"

    resp = fields.Many2one(
        'res.users',
        string='Current Sender'
        )
    memo_record = fields.Many2one(
        'usl.employee.appraisal',
        string='Appraisal Reference'
        )
    description_two = fields.Text('Comment')
    date = fields.Datetime(
        'Date', 
        default=lambda self: fields.datetime.now()
        )
    directed_user_id = fields.Many2one('res.users', 'Direct To')
    users_followers = fields.Many2many('hr.employee', string='Add followers')
    type = fields.Selection([
        ('return', 'Return'),
        ('forward', 'Forward'),
        ], string="Type", default='forward')

    def _get_supervisor_manager_users(self):
        supervior_group, managers_group = self.env.ref('maach_hr_appraisal.group_supervisor'), \
        self.env.ref('maach_hr_appraisal.group_appraisal_manager_id')
        officers_group = self.env.ref('maach_hr_appraisal.group_appraisal_officer_id')
        supervisor_grps = self.env['res.groups'].browse([supervior_group.id]).mapped('users')
        manager_grps = self.env['res.groups'].browse([managers_group.id]).mapped('users')
        officers_grp_users = self.env['res.groups'].browse([officers_group.id]).mapped('users')
        supervisor_users = [
            rex.id for rex in supervisor_grps.filtered(lambda x: x.id != self.memo_record.employee_id.user_id)]
        manager_users = [rex.id for rex in manager_grps.filtered(lambda x: x.id != self.memo_record.employee_id.user_id.id)]
        officers_users = [rex.id for rex in officers_grp_users.filtered(lambda x: x.id != self.memo_record.employee_id.user_id.id)]
        user_ids = supervisor_users + manager_users + officers_users
        domain = [('id', 'in', user_ids)]
        return domain

    def confirm_action(self):
        msg = "No Comment"
        if self.description_two:
            msg = self.description_two

        if self.directed_user_id:
            body = "<br/><b>{}:</b> {}<br/>".format(
                self.env.user.name,
                self.description_two if self.description_two else "-"
                )
            record = self.env['usl.employee.appraisal'].search([('id', '=', self.memo_record.id)])
            record.comments = body
            curr_emp_user = self.env['hr.employee'].search(
                [('user_id', '=', self.directed_user_id.id)], 
                limit=1
                )
            if not curr_emp_user:
                raise ValidationError('No employee record found for the directed user !!!')
            record.set_approvers(curr_emp_user)
            email_to = record.directed_user_id.login
            subject = "Appraisal Notification"
            email_cc = [rec.work_email for rec in record.approver_ids]
            msg = "Dear {}, <br/>I wish to notify you that an appraisal with description, {} \
            by {} has been {}ed to you for action. Comments below: {}  \n <br/> <br/>Kindly {} to review <br/>\
            Yours Faithfully <br/>{}".format(record.directed_user_id.name,
                                                record.sequence, record.employee_id.name,
                                                self.type, record.comments, self.get_url(record.id, record._name),
                                                self.env.user.name)
            record.action_notify(subject, msg, email_to, email_cc)

        else:
            raise ValidationError('Please select an Employee to Direct To')

    def get_url(self, id, name):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
        return "<a href={}> </b>Click<a/>. ".format(base_url)

