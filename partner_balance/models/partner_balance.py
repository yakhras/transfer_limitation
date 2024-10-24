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


    # Returns the domain to filter account.move.line records used in the balance computation.
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

    
    #Compute balance value
    @api.depends('move_line_ids.debit', 'move_line_ids.credit')
    def _compute_balance(self):
        for rec in self:
            # Get the domain using the _get_move_line_domain method
            domain = rec._get_move_line_domain()

            # Use the domain to search for matching account.move.line records
            move_lines = self.env['account.move.line'].search(domain)

            # Calculate total debit and credit from the filtered lines
            debit = sum(line.debit for line in move_lines)
            credit = sum(line.credit for line in move_lines)

            # Compute balance as debit - credit
            rec.balance = debit - credit


    #Override the create Method for recompute balance
    @api.model
    def create(self, vals):
        record = super(PartnerBalance, self).create(vals)
        record._compute_balance()  # Compute balance after creation
        return record
    
    
    # to display the partner’s name instead of the default object name
    def name_get(self):
        result = []
        for record in self:
            name = record.partner_id.name  # Get the partner name
            result.append((record.id, name))  # Return a tuple of (record_id, name)
        return result
    

    def _compute_move_lines(self):
        """
        Compute the move lines used for balance calculation and set them to the One2many field.
        """
        for rec in self:
            move_lines = self.env['account.move.line'].search(self._get_move_line_domain())
            rec.move_line_ids = move_lines