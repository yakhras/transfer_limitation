from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class SaleOrder(models.Model):
    _inherit = 'sale.order'   # Inherit the model

    has_note = fields.Boolean(string="Has Note", compute="_compute_has_note")

    def _compute_has_note(self):
        for record in self:
            # Check if `note` has meaningful content (ignoring whitespace and empty HTML tags)
            record.has_note = bool(record.note and record.note.strip())