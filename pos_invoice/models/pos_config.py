from odoo import _, api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"


    invoice_type = fields.Boolean("Select Invoice Type", help="Allow to Select Invoice type: Formal, Informal", default=False)