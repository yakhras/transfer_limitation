# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class StockValuationLayerRevaluation(models.TransientModel):
    _inherit = 'stock.valuation.layer.revaluation'


    # location_id = fields.Many2one('stock.location', "Related Location", required=True)


    def action_validate_revaluation(self):
        self.reason = self.current_quantity_svl
        super(StockValuationLayerRevaluation, self).action_validate_revaluation()
