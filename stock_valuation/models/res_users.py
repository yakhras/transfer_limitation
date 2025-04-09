from odoo import models, fields




class ResUsers(models.Model):
    _inherit = 'res.users'


    property_location_id = fields.Many2one('stock.location', string='Default Location')
    