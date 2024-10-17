from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'


    @api.model
    def geo(self,long):
        return self.write({'barcode': 'long'})
        