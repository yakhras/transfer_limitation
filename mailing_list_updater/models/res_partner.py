# -*- coding: utf-8 -*-

from odoo import models, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    def get_contacts_with_email(self, domain, mailing_list_id):
        """Update mobile field with count and return results"""
        if domain is None:
            domain = []
        
        email_domain = [('email', '!=', False)] + domain
        partners_with_email = self.search(email_domain)
        
        specific_partner = self.browse(61136)
        if specific_partner.exists():
            specific_partner.write({'mobile': len(partners_with_email)})

        added_count = 0
        skipped_count = 0
        
        # Add contacts to mailing list if ID provided
        if mailing_list_id:
            mailing_list = self.env['mailing.list'].browse(mailing_list_id)
            if mailing_list.exists():
                for partner in partners_with_email:
                    # Check if contact already exists
                    existing = self.env['mailing.contact'].sudo().search([
                        ('email', '=', partner.email),
                        ('list_ids', '=', mailing_list_id)  # Fixed domain
                    ], limit=1)
                    
                    if not existing:
                        # Create new mailing contact
                        self.env['mailing.contact'].sudo().create({
                            'name': partner.name,
                            'email': partner.email,
                            'list_ids': [(4, mailing_list_id)],
                        })
                        added_count += 1
                    else:
                        skipped_count += 1
        
        # RETURN results
        return {
            'success': True,
            'model': 'res.partner',
            'total_found': len(partners_with_email),
            'added': added_count,
            'skipped': skipped_count
        }


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    def get_contacts_with_email(self, domain, mailing_list_id):
        """Update mobile field with count and return results"""
        if domain is None:
            domain = []
        
        email_domain = [('email_from', '!=', False)] + domain
        leads_with_email = self.search(email_domain)
        
        specific_lead = self.browse(2781)
        if specific_lead.exists():
            specific_lead.write({'phone': len(leads_with_email)})

        added_count = 0
        skipped_count = 0
        
        # Add contacts to mailing list if ID provided
        if mailing_list_id:
            mailing_list = self.env['mailing.list'].browse(mailing_list_id)
            if mailing_list.exists():
                for lead in leads_with_email:
                    # Check if contact already exists
                    existing = self.env['mailing.contact'].sudo().search([
                        ('email', '=', lead.email_from),
                        ('list_ids', '=', mailing_list_id)  # Fixed domain
                    ], limit=1)
                    
                    if not existing:
                        # Create new mailing contact
                        self.env['mailing.contact'].sudo().create({
                            'name': lead.name,
                            'email': lead.email_from,
                            'list_ids': [(4, mailing_list_id)],
                        })
                        added_count += 1
                    else:
                        skipped_count += 1
        
        # RETURN results
        return {
            'success': True,
            'model': 'crm.lead',
            'total_found': len(leads_with_email),
            'added': added_count,
            'skipped': skipped_count
        }