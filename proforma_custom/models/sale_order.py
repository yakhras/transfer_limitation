from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class SaleOrder(models.Model):
    _inherit = 'sale.order'   # Inherit the model

    has_note = fields.Boolean(string="Has Note", compute="_compute_has_note")
    expiration_days = fields.Char(
        string="Expiration Days",
        compute="_compute_expiration_days",
        store=False  # No need to store this, as it's dynamic and only used in the report
    )


    def _compute_has_note(self):
        for record in self:
            # Check if `note` has meaningful content (ignoring whitespace and empty HTML tags)
            record.has_note = bool(record.note)


    def _compute_expiration_days(self):
        for order in self:
            if order.validity_date and order.date_order:
                # Convert date_order to a date if it's a datetime field
                date_order = order.date_order.date() if hasattr(order.date_order, 'date') else order.date_order
                delta = order.validity_date - date_order
                order.expiration_days = f"{delta.days} Days"
            else:
                order.expiration_days = "N/A"


    partner_name_title_case = fields.Char(
        compute='_compute_partner_name_title_case', 
        string='Partner Name (Title Case)'
    )

    def _compute_partner_name_title_case(self):
        for record in self:
            record.partner_name_title_case = record.partner_id.name.title() if record.partner_id.name else ''