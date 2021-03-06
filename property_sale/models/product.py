import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http

class ProductProduct(models.Model):
    _inherit = "product.product"
    
    @api.model
    def create(self, vals):
        vals['default_code'] = self.env['ir.sequence'].next_by_code('product.product')
        return super(ProductProduct, self).create(vals)