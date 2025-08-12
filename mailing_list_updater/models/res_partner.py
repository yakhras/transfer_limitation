# -*- coding: utf-8 -*-

from odoo import models, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    
    def get_contacts_with_email(self, domain, mailing_list_id):
        """Update mobile field with count"""
        if domain is None:
            domain = []
        
        email_domain = [('email', '!=', False)] + domain
        partners_with_email = self.search(email_domain)
        
        specific_partner = self.browse(61136)
        if specific_partner.exists():
            specific_partner.write({'mobile': len(partners_with_email)})


        # Add contacts to mailing list if ID provided
        if mailing_list_id:
            mailing_list = self.env['mailing.list'].browse(mailing_list_id)
            if mailing_list.exists():
                for partner in partners_with_email:
                    # Check if contact already exists
                    existing = self.env['mailing.contact'].sudo().search([
                        ('email', '=', partner.email),
                        ('list_ids', 'in', mailing_list_id)
                    ], limit=1)
                    
                    if not existing:
                        # Create new mailing contact
                        self.env['mailing.contact'].sudo().create({
                            'name': partner.name,
                            'email': partner.email,
                            'list_ids': [(4, mailing_list_id)],  # Link to mailing list
                        })






