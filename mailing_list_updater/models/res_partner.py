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





class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    
    def get_contacts_with_email(self, domain, mailing_list_id):
        """Update mobile field with count"""
        if domain is None:
            domain = []
        
        email_domain = [('email_from', '!=', False)] + domain
        partners_with_email = self.search(email_domain)
        
        specific_partner = self.browse(2781)
        if specific_partner.exists():
            specific_partner.write({'phone': len(partners_with_email)})


        # Add contacts to mailing list if ID provided
        if mailing_list_id:
            mailing_list = self.env['mailing.list'].browse(mailing_list_id)
            if mailing_list.exists():
                for partner in partners_with_email:
                    # Check if contact already exists
                    existing = self.env['mailing.contact'].sudo().search([
                        ('email', '=', partner.email_from),
                        ('list_ids', '=', mailing_list_id)
                    ], limit=1)
                    
                    if not existing:
                        # Create new mailing contact
                        self.env['mailing.contact'].sudo().create({
                            'name': partner.name,
                            'email': partner.email_from,
                            'list_ids': [(4, mailing_list_id)],  # Link to mailing list
                        })





# Even better solution: Create a single method that handles all sources at once

class MailingList(models.Model):
    _inherit = 'mailing.list'
    
 
    def add_contacts_from_sources(self, mailing_list_id, sources_data):
        """
        Add contacts from multiple sources, automatically handling duplicates
        sources_data: [{'model': 'res.partner', 'domain': [...]}, ...]
        """
        mailing_list = self.browse(mailing_list_id)
        if not mailing_list.exists():
            return {'error': 'Mailing list not found'}
        
        # Collect all emails first to check for duplicates across sources
        all_contacts = []
        
        for source in sources_data:
            model_name = source.get('model')
            domain = source.get('domain', [])
            
            if model_name == 'res.partner':
                email_domain = [('email', '!=', False)] + domain
                records = self.env[model_name].search(email_domain)
                for record in records:
                    all_contacts.append({
                        'name': record.name,
                        'email': record.email,
                    })
                    
            elif model_name == 'crm.lead':
                email_domain = [('email_from', '!=', False)] + domain
                records = self.env[model_name].search(email_domain)
                for record in records:
                    all_contacts.append({
                        'name': record.name,
                        'email': record.email_from,
                    })
        
        # Remove duplicates by email
        unique_contacts = {}
        for contact in all_contacts:
            if contact['email']:
                unique_contacts[contact['email'].lower()] = contact
        
        # Check existing and add new contacts
        added_count = 0
        for email, contact_data in unique_contacts.items():
            existing = self.env['mailing.contact'].sudo().search([
                ('email', '=', contact_data['email']),
                ('list_ids', '=', mailing_list_id)
            ], limit=1)
            
            if not existing:
                self.env['mailing.contact'].sudo().create({
                    'name': contact_data['name'],
                    'email': contact_data['email'],
                    'list_ids': [(4, mailing_list_id)],
                })
                added_count += 1
        
        return {
            'success': True,
            'added': added_count,
            'total_found': len(unique_contacts)
        }