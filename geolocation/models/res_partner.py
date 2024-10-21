from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    latitude = fields.Char(string='Latitude')
    longitude = fields.Char(string='Longitude')

    def geo(self):
        latitudes = self.env.context.get('latitude', False)
        longitudes = self.env.context.get('longitude', False)
        return self.write({
                'latitude': 'latitudes',
                'longitude': 'longitudes',
            })
        