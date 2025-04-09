from odoo import models, fields




class ResUsers(models.Model):
    _inherit = 'res.users'


    property_location_id = fields.One2many('stock.location','name', string='Default Location')