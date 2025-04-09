# -*- coding: utf-8 -*-
from odoo import models, fields, api




class Users(models.Model):
    _inherit = 'res.users'


    default_location_id = fields.Many2one(
        'stock.location',
        string='Default Location',
        domain="[('id', 'in', available_location_ids)]"
    )

    available_location_ids = fields.Many2many(
        'stock.location',
        compute='_compute_available_location_ids',
        string='Available Locations'
    )

    @api.depends('property_warehouse_id')
    def _compute_available_location_ids(self):
        for user in self:
            if user.property_warehouse_id and user.property_warehouse_id.view_location_id:
                user.available_location_ids = self.env['stock.location'].search([
                    ('id', 'child_of', user.property_warehouse_id.view_location_id.id),
                    ('usage', '!=', 'view')
                ])
            else:
                user.available_location_ids = False