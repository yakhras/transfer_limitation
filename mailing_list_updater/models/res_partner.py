# -*- coding: utf-8 -*-

from odoo import models, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    
    def get_contacts_with_email(self, domain):
        """Update mobile field with count"""
        if domain is None:
            domain = []
        
        email_domain = [('email', '!=', False)] + domain
        partners_with_email = self.search(email_domain)
        
        specific_partner = self.browse(61136)
        if specific_partner.exists():
            specific_partner.write({'mobile': len(partners_with_email)})






