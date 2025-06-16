# # -*- coding: utf-8 -*-

from odoo import models, api, _, fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    cumulated_balance_amount_currency = fields.Monetary(string='Cumulated Amount Balance', store=False,
        currency_field='company_currency_id',
        compute='_compute_cumulated_amount_currency',
        help="Cumulated amount currency balance depending on the domain and the order chosen in the view.")

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
                partner_balance._compute_balance()  # Call the method to recalculate balance

        return move_line
    
    @api.model
    def unlink(self):
        partner_ids = self.mapped('partner_id').ids
        res = super(AccountMoveLine, self).unlink()

        # Recalculate balances for affected partner balances
        partner_balances = self.env['partner.balance'].search([
            ('partner_id', 'in', partner_ids)
        ])
        for partner_balance in partner_balances:
            partner_balance._compute_balance()  # Call the method to recalculate balance

        return res
    

    @api.depends_context('order_cumulated_balance', 'domain_cumulated_balance')
    def _compute_cumulated_amount_currency(self):
        if not self.env.context.get('order_cumulated_balance'):
            # We do not come from search_read, so we are not in a list view, so it doesn't make any sense to compute the cumulated balance
            self.cumulated_balance = 0
            return

        # get the where clause
        query = self._where_calc(list(self.env.context.get('domain_cumulated_balance') or []))
        order_string = ", ".join(self._generate_order_by_inner(self._table, self.env.context.get('order_cumulated_balance'), query, reverse_direction=True))
        from_clause, where_clause, where_clause_params = query.get_sql()
        sql = """
            SELECT account_move_line.id, SUM(account_move_line.amount_currency) OVER (
                ORDER BY %(order_by)s
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
            FROM %(from)s
            WHERE %(where)s
        """ % {'from': from_clause, 'where': where_clause or 'TRUE', 'order_by': order_string}
        self.env.cr.execute(sql, where_clause_params)
        result = {r[0]: r[1] for r in self.env.cr.fetchall()}
        for record in self:
            record.cumulated_balance = result[record.id]
