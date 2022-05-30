import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http

class USILBranch(models.Model):
    _name = "usl.branch"

    name = fields.Char('Name', required=True)


class ResUsers(models.Model):
    _inherit = "res.users"

    branch_id = fields.Many2one('usl.branch',string="Branch")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    branch_id = fields.Many2one('usl.branch',string="Branch",default=lambda self:self.env.user.branch_id.id)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    branch_id = fields.Many2one('usl.branch',string="Branch",default=lambda self:self.env.user.branch_id.id)


class AccountMove(models.Model):
    _inherit = "account.move"

    branch_id = fields.Many2one('usl.branch',string="Branch",default=lambda self:self.env.user.branch_id.id)
    
     