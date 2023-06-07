from datetime import datetime
from dateutil.parser import parse
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class res_users(models.Model):
    _inherit = 'res.users'

    # memo_flag = fields.Boolean("Memo Flag", default=False)
    user_signature = fields.Binary("Upload User Signature")
