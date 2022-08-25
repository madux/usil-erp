import time
from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import logging

class ReportAccountStatement(models.AbstractModel):
    _name = "report.allocation.report_accountstatement"
    
    def get_payment(self, docs):
        return self.env['account.payment'].search([('reference', '=', docs.name), ('state', '=', ['posted', 'sent','reconciled'])])

	@api.model
	def render_html(self, docids, data=None):
		_logger = logging.getLogger(__name__)
		if not docids:
			raise ValidationError(_("Form content is missing, this report cannot be printed."))
		
		model = 'sale.order'
		docs = self.env[model].browse(docids[0])
		
		#get payments
		payments = self.get_payment(docs)
		docargs = {
			'doc_ids': self.ids,
			'doc_model': model,
			'data': data,
			'docs': docs,
			'time': time,
			'date': str(datetime.today()),
			'payments': payments,
		}
		
		return self.env['report'].render('property_sale.report_accountstatement', docargs)
	