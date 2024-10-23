# -*- coding: utf-8 -*-

from odoo import models, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def write(self, vals):
        # Call the original write method
        res = super(AccountMoveLine, self).write(vals)

        # Check if the relevant fields are in the updated values
        if any(field in vals for field in ['debit', 'credit', 'full_reconcile_id']):
            # Get the partner_id from the move lines being updated
            partner_ids = self.mapped('partner_id').ids

            # Recalculate balances for affected partner balances
            partner_balances = self.env['partner.balance'].search([
                ('partner_id', 'in', partner_ids)
            ])
            for partner_balance in partner_balances:
                partner_balance._compute_balance()  # Call the method to recalculate balance

        return res