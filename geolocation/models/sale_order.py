from odoo import _, api, fields, models
import datetime


class ResPartner(models.Model):
    _inherit = 'res.partner'



    def geo(self, geo):
        # return self.write({'barcode': geo.get('long')})
        return self.barcode = geo.get(data)
