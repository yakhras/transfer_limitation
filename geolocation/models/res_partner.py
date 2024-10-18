from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def geo(self,long):
        record = self.write({
            'barcode': long  # Storing the 'data' in the 'name' field
        })
        return {'success': True, 'message': f"Data '{long}' stored successfully with ID {self.id}"}
        