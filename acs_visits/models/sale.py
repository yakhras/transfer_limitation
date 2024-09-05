# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _visit_count(self):
        for rec in self: 
            rec.visit_count = self.env['visit.visit'].sudo().search_count([('sale_id', '=', rec.id)])

    visit_count = fields.Integer(compute="_visit_count", readonly=True, string="Visits")

    def sale_visit_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_visits.visit_visit_action")
        action['domain'] = [('sale_id','=', self.id)]
        action['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_sale_id': self.id
        }
        return action
