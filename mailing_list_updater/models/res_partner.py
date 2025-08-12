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
        self.mobile = len(partners_with_email)