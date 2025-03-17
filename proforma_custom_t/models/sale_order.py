from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError
import re



class SaleOrder(models.Model):
    _inherit = 'sale.order'   # Inherit the model

    has_note = fields.Boolean(string="Has Note", compute="_compute_has_note")
    expiration_days = fields.Char(
        string="Expiration Days",
        compute="_compute_expiration_days",
        store=False  # No need to store this, as it's dynamic and only used in the report
    )
    note = fields.Html(
        default=lambda self: """
        <strong style="text-decoration: underline;">Temel Koşullar</strong>
        <p style="font-size: 13px; line-height: 1.6; color: #333; margin-top: 10px;">
            1. Fiyatlarımıza %20 KDV Dahil değildir.<br/>
            2. Ürün fiyatlarını direkt veya dolaylı olarak etkileyen vergiler veya vergi oran değişiklikleri lehte veya aleyhte fiyatlarımıza yansıtılacaktır.<br/>
            3. Fiyatlarımız USD bazında olup, %100 tesliminde ödenecektir. Ödemeler, ödeme tarihindeki TCMB efektif satış kuru üzerinden yapılacaktır.<br/>
            4. Bu proforma müşteri tarafından teyit edildikten sonra sözleşme niteliği taşır.<br/>
            5. Vadesinde ödenmeyen faturalara aylık TL bazında %8, USD bazında %3 vade farkı ilave edilecektir.
        </p>
        """
    )

    @api.onchange('note')
    def _auto_number_note(self):
        """Automatically number each new line in the note field."""
        for record in self:
            if record.note:
                # Extract existing lines from the HTML content
                lines = re.split(r'<br\s*/?>', record.note.strip())

                # Remove existing numbers and re-number
                numbered_lines = [f"{i + 1}. {re.sub(r'^\d+\.\s*', '', line.strip())}" for i, line in enumerate(lines)]

                # Convert back to HTML with <br> for line breaks
                record.note = '<br/>'.join(numbered_lines)

    def _compute_has_note(self):
        for record in self:
            if record.note:
                # Remove HTML tags and check for meaningful text
                stripped_note = re.sub('<[^<]+?>', '', record.note)  # Remove HTML tags
                record.has_note = bool(stripped_note.strip())  # Check if non-whitespace content exists
            else:
                record.has_note = False


    def _compute_expiration_days(self):
        for order in self:
            if order.validity_date and order.date_order:
                # Convert date_order to a date if it's a datetime field
                date_order = order.date_order.date() if hasattr(order.date_order, 'date') else order.date_order
                delta = order.validity_date - date_order
                order.expiration_days = f"{delta.days} Days"
            else:
                order.expiration_days = "N/A"


    def get_partner_name_title_case(self):
        return self.partner_id.name.title() if self.partner_id.name else ''
    
