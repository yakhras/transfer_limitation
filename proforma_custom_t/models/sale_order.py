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
        <strong style="border-bottom: 1px solid #000;">Temel Koşullar</strong>
        <ol style="font-size: 12px; line-height: 1.6; color: #333; margin-top: 10px;">
            <li>Fiyatlarımıza %20 KDV Dahil değildir.</li>
            <li>Ürün fiyatlarını direkt veya dolaylı olarak etkileyen vergiler veya vergi oran değişiklikleri lehte veya aleyhte fiyatlarımıza yansıtılacaktır.</li>
            <li>Fiyatlarımız USD bazında olup, %100 tesliminde ödenecektir. Ödemeler, ödeme tarihindeki TCMB efektif satış kuru üzerinden yapılacaktır.</li>
            <li>Bu proforma müşteri tarafından teyit edildikten sonra sözleşme niteliği taşır.</li>
            <li>Vadesinde ödenmeyen faturalara aylık TL bazında %8, USD bazında %3 vade farkı ilave edilecektir.</li>
        </ol>
        """
    )


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
    



class ResCompany(models.Model):
    _inherit = 'res.company'

    company_bank_journal_ids = fields.Many2many(
        'account.journal',
        'company_bank_journal_rel',  # Relation table name
        'company_id',  # Column for res.company
        'journal_id',  # Column for account.journal
        string="Company Bank Journals",
        domain="[('type', '=', 'bank'), ('company_id', '=', id)]"
    )



class ResUsers(models.Model):
    _inherit = 'res.users'

    

    default_picking_type_ids = fields.Many2many(
        'stock.picking.type', 'stock_picking_type_users_rel',
        'user_id', 'picking_type_id', string='Default Warehouse Operations', store=False)
    
    stock_location_ids = fields.Many2many(
        'stock.location',
        'location_security_stock_location_users',
        'user_id',
        'location_id',
        'Stock Locations', store=False,)






class CrmLead(models.Model):
  _inherit = 'crm.lead'

  @api.model
  def write(self, vals):
    if 'stage_id' in vals:
      old_stages = {lead.id: lead.stage_id for lead in self}
      res = super().write(vals)
      for lead in self:
        if lead.stage_id and lead.id in old_stages and lead.stage_id != old_stages[lead.id]:
          message = "HI"
          self.env['bus.bus']._sendone(
            self.env.user.partner_id.id,
            'notification',
            {'type': 'info',
             'title': 'stage',
             'message': message,
             'sticky': True,
            }
          )
          return res
        return super().write(vals)
          
