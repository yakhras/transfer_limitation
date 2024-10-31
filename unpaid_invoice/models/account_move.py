from odoo import models, fields, api
from datetime import date

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_due_and_unpaid = fields.Boolean(
        compute='_compute_due_and_unpaid',
        store=True
    )

    @api.depends('invoice_date_due', 'payment_state')
    def _compute_due_and_unpaid(self):
        unpaid_invoice_model = self.env['unpaid.invoice']
        for move in self:
            # Check if due today and unpaid or partially paid
            move.is_due_and_unpaid = (
                move.invoice_date_due == date.today() and
                move.payment_state in ['not_paid', 'partial']
            )

            # Trigger creation in unpaid.invoice if condition met
            if move.is_due_and_unpaid:
                existing_unpaid_invoice = unpaid_invoice_model.search([('invoice_id', '=', move.id)], limit=1)
                if not existing_unpaid_invoice:
                    unpaid_invoice_model.create({
                        'invoice_id': move.id,
                        'amount_due': move.amount_residual,
                        'due_date': move.invoice_date_due,
                        'partner_id': move.partner_id.id,
                        'team_id': move.team_id.id,
                        'currency_id': move.currency_id.id,
                    })
