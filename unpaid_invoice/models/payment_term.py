from odoo import models, fields
from datetime import datetime

class PaymentTerm(models.Model):
    _name = 'payment.term'
    _description = 'Payment Term'

    name = fields.Char('Payment Name', required=True)
    