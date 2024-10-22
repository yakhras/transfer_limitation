# -*- coding: utf-8 -*-

from odoo import models, fields

class PartnerBalance(models.Model):
    _name = 'partner.balance'
    _description = 'Partner Balance'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade'
    )
    move_line_id = fields.Many2one(
        'account.move.line',
        string='Move Line',
        required=True,
        ondelete='cascade'
    )
    balance = fields.Monetary(
        string='Balance',
        required=True,
        default=0.0,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        related='partner_id.currency_id',
        store=True
    )
    date_updated = fields.Datetime(
        string='Last Updated',
        default=fields.Datetime.now
    )

    _sql_constraints = [
        ('unique_partner_move_line', 'UNIQUE(partner_id, move_line_id)',
         'Each partner can only have one balance record per move line!')
    ]

    # Get Balance Value For Record
    def get_balance_value(self):
        for rec in self:
            rec.balance = rec.compute_balance()

    # Compute Balance Value For Record
    def compute_balance(self):
        for rec in self:
            total_credits = rec.get_total_credits()
            total_debits = rec.get_total_debits()
            balance = round(total_debits - total_credits, 2)
            return balance

    # Get Total Debit Values For Record
    def get_total_debits(self):
        domain = [
            ('full_reconcile_id', '=', False),
            ('balance', '!=', 0),
            ('account_id.reconcile', '=', True),
            ('partner_id', '=', self.partner_id.id)  # Ensure it filters by partner
        ]
        total_debit = sum(self.env['account.move.line'].search(domain).mapped('debit'))
        return round(total_debit, 2)

    # Get Total Credit Values For Record
    def get_total_credits(self):
        domain = [
            ('full_reconcile_id', '=', False),
            ('balance', '!=', 0),
            ('account_id.reconcile', '=', True),
            ('partner_id', '=', self.partner_id.id)  # Ensure it filters by partner
        ]
        total_credit = sum(self.env['account.move.line'].search(domain).mapped('credit'))
        return round(total_credit, 2)
