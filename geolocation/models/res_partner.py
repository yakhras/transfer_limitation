from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    latitude = fields.Float(string='Latitude', digits=(16, 5))
    longitude = fields.Float(string='Longitude', digits=(16, 5))
        