# -*- coding: utf-8 -*-

from odoo import models, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def get_contacts_with_email(self, domain=None):
        """
        Search partners with given domain and filter those with email
        
        Args:
            domain: list - Odoo domain filter
            
        Returns:
            dict: Window action to display filtered records
        """
        if domain is None:
            domain = []
        
        # Add email filter to domain
        email_domain = [('email', '!=', False)] + domain
        
        # Search records with email
        partners_with_email = self.search(email_domain)
        
        # Return tree view action
        return {
            'name': _('Contacts with Email'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('id', 'in', partners_with_email.ids)],
            'context': {
                'search_default_filter_email': 1,
                'create': False,  # Optional: disable create button
            },
            'target': 'current',
            'help': _(f'Found {len(partners_with_email)} contacts with email addresses')
        }