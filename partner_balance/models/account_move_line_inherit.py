# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

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
            _logger.info("Updating partner balances for partner_ids: %s", partner_ids)

            # Recalculate balances for affected partner balances
            partner_balances = self.env['partner.balance'].search([
                ('partner_id', 'in', partner_ids)
            ])
            for partner_balance in partner_balances:
                _logger.info("Recalculating balance for partner: %s", partner_balance.partner_id.name)
                partner_balance._compute_balance()  # Call the method to recalculate balance

        return res
    
    @api.model
    def create(self, vals):
        # Create the account.move.line record
        move_line = super(AccountMoveLine, self).create(vals)

        # Check if the relevant fields are in the created values
        if any(field in vals for field in ['debit', 'credit', 'full_reconcile_id']):
            partner_id = move_line.partner_id.id
            
            # Log the partner being updated
            _logger.info("Creating account.move.line and updating balance for partner_id: %s", partner_id)
            
            # Recalculate balances for the affected partner balance
            partner_balance = self.env['partner.balance'].search([('partner_id', '=', partner_id)], limit=1)
            if partner_balance:
                _logger.info("Recalculating balance for partner: %s", partner_balance.partner_id.name)
                partner_balance.get_balance_value()  # Call the method to recalculate balance

        return move_line