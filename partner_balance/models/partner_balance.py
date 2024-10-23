# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PartnerBalance(models.Model):
    _name = 'partner.balance'
    _description = 'Partner Balance'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade'
    )
    # Dynamically filtered One2many field to display related move lines
    move_line_ids = fields.One2many(
        'account.move.line', 
        compute='_compute_move_lines',
        string="Related Move Lines",
        readonly=True
    )
    balance = fields.Monetary(
        string='Balance',
        required=True,
        default=0.0,
        currency_field='currency_id',
        compute='_compute_balance',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        # required=True,
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
    @api.depends('move_line_ids.debit', 'move_line_ids.credit')
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
    
    def _compute_move_line_count(self):
        for rec in self:
            rec.move_line_count = self.env['account.move.line'].search_count(self._get_move_line_domain())

    def _get_move_line_domain(self):
        """
        Returns the domain to filter account.move.line records used in the balance computation.
        """
        return [
            ('partner_id', '=', self.partner_id.id),
            ('full_reconcile_id', '=', False),
            ('balance', '!=', 0),
            ('account_id.reconcile', '=', True)
        ]
    
    def action_view_move_lines(self):
        """
        Returns an action that opens a tree view displaying the filtered move lines.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Move Lines',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': self._get_move_line_domain(),
            'context': dict(self.env.context),
        }
    

    def _compute_move_lines(self):
        """
        Compute the move lines used for balance calculation and set them to the One2many field.
        """
        for rec in self:
            move_lines = self.env['account.move.line'].search(self._get_move_line_domain())
            rec.move_line_ids = move_lines

    # Compute balance for the current records only
    @api.depends('move_line_ids.debit', 'move_line_ids.credit')
    def _compute_balance(self):
        for rec in self:
            debit = sum(line.debit for line in rec.move_line_ids if not line.full_reconcile_id)
            credit = sum(line.credit for line in rec.move_line_ids if not line.full_reconcile_id)
            rec.balance = debit - credit
