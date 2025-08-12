# -*- coding: utf-8 -*-

from odoo import models, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    
    def get_contacts_with_email(self, domain=None):
        """Update mobile field with count"""
        if domain is None:
            domain = []
        
        email_domain = [('email', '!=', False)] + domain
        partners_with_email = self.search(email_domain)
        
        # Write to the record (assuming self is a single record)
        self.write({'mobile': str(len(partners_with_email))})