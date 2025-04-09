from odoo import models, fields




class ResUsers(models.Model):
    _inherit = 'res.users'


    location_ids= fields.Many2one('stock.location', string='Default Location')
