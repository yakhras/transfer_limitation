from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'



    def geo(self, long):
        return self.write({'barcode': '321'})
        