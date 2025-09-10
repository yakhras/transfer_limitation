# -*- coding: utf-8 -*-

from odoo import models, api, _
import re

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



class MailingList(models.Model):
    _inherit = 'mailing.list'



    def split_and_clean_emails(self, email_string):
        """
        Split multiple emails and clean them
        Handles: comma, semicolon, space, newline separators
        """
        if not email_string:
            return []
        
        # Convert to string if not already
        email_string = str(email_string).strip()
        
        # Split by common separators: comma, semicolon, space, newline
        # Also handles cases with or without spaces after separators
        emails = re.split(r'[,;\s\n]+', email_string)
        
        # Clean and validate each email
        valid_emails = []
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for email in emails:
            email = email.strip().lower()
            if email and re.match(email_pattern, email):
                valid_emails.append(email)
        
        return valid_emails
    


    def add_contacts_from_sources(self, mailing_list_id, sources_data):
        """
        Add contacts from multiple sources, handling multiple emails per field
        """
        mailing_list = self.browse(mailing_list_id)
        if not mailing_list.exists():
            return {'error': 'Mailing list not found'}
        
        # Collect all contacts
        all_contacts = []
        
        for source in sources_data:
            model_name = source.get('model')
            domain = source.get('domain', [])
            
            if model_name == 'res.partner':
                email_domain = [('email', '!=', False)] + domain
                records = self.env[model_name].search(email_domain)
                for record in records:
                    # Handle multiple emails in one field
                    emails = self.split_and_clean_emails(record.email)
                    for email in emails:
                        all_contacts.append({
                            'name': record.name,
                            'email': email,
                            'source': 'Partner'
                        })
                    
            elif model_name == 'crm.lead':
                email_domain = [('email_from', '!=', False)] + domain
                records = self.env[model_name].search(email_domain)
                for record in records:
                    # Handle multiple emails in one field
                    emails = self.split_and_clean_emails(record.email_from)
                    for email in emails:
                        all_contacts.append({
                            'name': record.name or email.split('@')[0],  # Use email prefix if no name
                            'email': email,
                            'source': 'Lead'
                        })
        
        # Remove duplicates by email
        unique_contacts = {}
        for contact in all_contacts:
            if contact['email']:
                # Store first occurrence (or you could merge names)
                if contact['email'] not in unique_contacts:
                    unique_contacts[contact['email'].lower()] = contact
        
        # Check existing and add new contacts
        added_count = 0
        skipped_count = 0
        errors = []
        
        for email, contact_data in unique_contacts.items():
            try:
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
                else:
                    skipped_count += 1
            except Exception as e:
                errors.append(f"Error with {email}: {str(e)}")
        
        return {
            'success': True,
            'added': added_count,
            'skipped': skipped_count,
            'total_found': len(unique_contacts),
            'errors': errors if errors else None
        }
    