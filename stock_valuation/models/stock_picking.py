# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, _



class Picking(models.Model):
    _inherit = "stock.picking"



    def _action_generate_immediate_wizard(self, show_transfers=False):
        view = self.env.ref('stock.view_immediate_transfer')
        return {
            'name': _('Immediate Transfer?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.immediate.transfer',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, 
                            default_show_transfers=show_transfers, 
                            default_pick_ids=[(4, p.id) for p in self], 
                            location_dest_id=self.location_dest_id.id, 
                            location_id=self.location_id.id),
        }
    