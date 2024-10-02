from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'   # Inherit the model

    email = fields.Boolean(string='email reciept')

    @api.onchange('email')
    def _onchange_email(self):
        if (self.email):
            contact = self.contact_list_ids.contact_ids
            for con in contact:
                self.copyvalue = con.name
        else:
            self.copyvalue = 0.0