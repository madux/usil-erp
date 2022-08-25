from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http

class Send_Memo_back(models.Model):
    _name = "memo.back"

    resp = fields.Many2one('res.users', 'Responsible')
    memo_record = fields.Many2one('memo.model','Memo ID',)
    reason = fields.Char('Reason') 
    date = fields.Datetime('Date')
    direct_employee_id = fields.Many2one('hr.employee', 'Direct To')
     
    def get_url(self, id, name):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
        return "<a href={}> </b>Click<a/>. ".format(base_url)

    def post_refuse(self):
        get_state = self.env['memo.model'].search([('id','=', self.memo_record.id)])
        reasons = "<b><h4>Refusal Message From: %s </b></br> Please refer to the reasons below:</h4></br>* %s." %(self.env.user.name,self.reason)
        get_state.write({'reason_back': reasons})
        if self.reason:
            msg_body = "Dear Sir/Madam, </br>We wish to notify you that a Memo request from {} has been refused / returned. </br>\
             </br>Kindly {} to Review</br> </br>Thanks".format(self.memo_record.employee_id.name, self.get_url(self.id, self._name))
            get_state.write({'state':'refuse', 'users_followers': [(4, self.direct_employee_id.id)]})
            for rec in get_state.res_users:
                if get_state.user_ids.id == rec.id:
                    get_state.res_users = [(3, rec.id)]
            
            self.mail_sending_reject(msg_body)
        else:
            raise ValidationError('Please Add the Reasons for refusal') 
        return{'type': 'ir.actions.act_window_close'}

    def mail_sending_reject(self, msg_body):
        subject = "Memo Rejection Notification"
        email_from = self.env.user.email
        mail_to = self.direct_employee_id.work_email
        initiator = self.memo_record.employee_id.work_email
        # emails = (','.join(str(item2.work_email) for item2 in self.users_followers))
        mail_data = {
                'email_from': email_from,
                'subject': subject,
                'email_to': mail_to,
                'reply_to': email_from,
                'email_cc': initiator,  # emails if self.users_followers else [],
                'body_html': msg_body
            }
        mail_id = self.env['mail.mail'].create(mail_data)
        self.env['mail.mail'].send(mail_id)
        