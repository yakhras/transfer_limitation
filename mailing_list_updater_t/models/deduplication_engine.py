# -*- coding: utf-8 -*-

import logging
import hashlib
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MailingDeduplicationEngine(models.TransientModel):
    """
    Multi-phase deduplication engine for mailing contacts.
    
    This transient model provides sophisticated deduplication algorithms
    to ensure no duplicate contacts are added to mailing lists, even when
    importing from multiple sources.
    
    Deduplication Phases:
    1. Internal Phase: Remove duplicates within the import batch
    2. External Phase: Remove contacts that already exist in the target mailing list
    3. Cross-source Phase: Handle contacts that exist in multiple source systems
    """
    
    _name = 'mailing.deduplication.engine'
    _description = 'Mailing Contact Deduplication Engine'
    
    # Configuration Fields (for UI configuration if needed)
    strict_email_matching = fields.Boolean(
        string='Strict Email Matching',
        default=True,
        help='Use exact email matching (recommended)'
    )
    
    normalize_emails = fields.Boolean(
        string='Normalize Emails',
        default=True,
        help='Normalize email addresses before comparison'
    )
    
    cross_source_priority = fields.Selection([
        ('newest', 'Prefer Newest Record'),
        ('oldest', 'Prefer Oldest Record'),
        ('partner', 'Prefer res.partner'),
        ('crm', 'Prefer crm.lead'),
        ('manual', 'Manual Resolution'),
    ], string='Cross-Source Priority', default='partner',
       help='How to resolve conflicts when the same contact exists in multiple sources')
    
    # Core Deduplication Methods
    
    @api.model
    def deduplicate_contacts(self, contacts_data, mailing_list, config=None):
        """
        Main deduplication method that coordinates all phases.
        
        Args:
            contacts_data (list): List of contact dictionaries
            mailing_list (recordset): Target mailing list
            config (dict, optional): Deduplication configuration
            
        Returns:
            tuple: (deduplicated_contacts, statistics)
        """
        if not contacts_data:
            return [], {'total_input': 0, 'total_output': 0, 'phases': {}}
        
        config = config or {}
        stats = {
            'total_input': len(contacts_data),
            'phases': {},
            'duplicates_found': 0,
            'removed_count': 0,
        }
        
        _logger.info(
            "Starting deduplication for %d contacts targeting list '%s'",
            len(contacts_data), mailing_list.name
        )
        
        # Phase 1: Internal deduplication (within the batch)
        contacts_after_phase1, phase1_stats = self._phase1_internal_deduplication(
            contacts_data, config
        )
        stats['phases']['phase1_internal'] = phase1_stats
        
        # Phase 2: External deduplication (against existing mailing list)
        contacts_after_phase2, phase2_stats = self._phase2_external_deduplication(
            contacts_after_phase1, mailing_list, config
        )
        stats['phases']['phase2_external'] = phase2_stats
        
        # Phase 3: Cross-source resolution
        final_contacts, phase3_stats = self._phase3_cross_source_resolution(
            contacts_after_phase2, config
        )
        stats['phases']['phase3_cross_source'] = phase3_stats
        
        # Calculate final statistics
        stats['total_output'] = len(final_contacts)
        stats['duplicates_found'] = (
            phase1_stats.get('duplicates_removed', 0) +
            phase2_stats.get('duplicates_removed', 0) +
            phase3_stats.get('duplicates_removed', 0)
        )
        stats['removed_count'] = stats['total_input'] - stats['total_output']
        stats['deduplication_rate'] = stats['removed_count'] / max(stats['total_input'], 1)
        
        _logger.info(
            "Deduplication completed: %d → %d contacts (%.1f%% reduction)",
            stats['total_input'], stats['total_output'], 
            stats['deduplication_rate'] * 100
        )
        
        return final_contacts, stats
    
    def _phase1_internal_deduplication(self, contacts_data, config):
        """
        Phase 1: Remove duplicates within the import batch.
        
        Args:
            contacts_data (list): Input contact data
            config (dict): Configuration options
            
        Returns:
            tuple: (deduplicated_contacts, phase_stats)
        """
        if not contacts_data:
            return [], {'input_count': 0, 'output_count': 0, 'duplicates_removed': 0}
        
        _logger.debug("Phase 1: Internal deduplication starting with %d contacts", len(contacts_data))
        
        normalize_emails = config.get('normalize_emails', True)
        email_to_contact = {}
        duplicates_removed = 0
        
        for contact in contacts_data:
            email = contact.get('email', '').strip()
            if not email:
                continue
            
            # Normalize email if configured
            if normalize_emails:
                email = self._normalize_email(email)
            
            # Check for duplicates
            if email in email_to_contact:
                # We have a duplicate - decide which one to keep
                existing_contact = email_to_contact[email]
                winner = self._resolve_internal_duplicate(existing_contact, contact, config)
                
                if winner != existing_contact:
                    email_to_contact[email] = winner
                
                duplicates_removed += 1
                
                _logger.debug(
                    "Phase 1: Found internal duplicate for %s, kept %s",
                    email, winner.get('source_model', 'unknown')
                )
            else:
                email_to_contact[email] = contact
        
        deduplicated_contacts = list(email_to_contact.values())
        
        phase_stats = {
            'input_count': len(contacts_data),
            'output_count': len(deduplicated_contacts),
            'duplicates_removed': duplicates_removed,
            'unique_emails': len(email_to_contact),
        }
        
        _logger.debug("Phase 1: Completed - %d duplicates removed", duplicates_removed)
        return deduplicated_contacts, phase_stats
    
    def _phase2_external_deduplication(self, contacts_data, mailing_list, config):
        """
        Phase 2: Remove contacts that already exist in the target mailing list.
        
        Args:
            contacts_data (list): Contacts from Phase 1
            mailing_list (recordset): Target mailing list
            config (dict): Configuration options
            
        Returns:
            tuple: (filtered_contacts, phase_stats)
        """
        if not contacts_data:
            return [], {'input_count': 0, 'output_count': 0, 'duplicates_removed': 0}
        
        _logger.debug("Phase 2: External deduplication against list '%s'", mailing_list.name)
        
        normalize_emails = config.get('normalize_emails', True)
        
        # Get existing emails in the mailing list
        existing_contacts = self.env['mailing.contact'].search([
            ('list_ids', 'in', mailing_list.id),
            ('email', '!=', False),
        ])
        
        existing_emails = set()
        for contact in existing_contacts:
            email = contact.email.strip() if contact.email else ''
            if email:
                if normalize_emails:
                    email = self._normalize_email(email)
                existing_emails.add(email)
        
        # Filter out contacts that already exist
        filtered_contacts = []
        duplicates_removed = 0
        
        for contact in contacts_data:
            email = contact.get('email', '').strip()
            if not email:
                continue
            
            if normalize_emails:
                normalized_email = self._normalize_email(email)
            else:
                normalized_email = email
            
            if normalized_email in existing_emails:
                duplicates_removed += 1
                _logger.debug(
                    "Phase 2: Contact %s already exists in mailing list",
                    email
                )
            else:
                filtered_contacts.append(contact)
        
        phase_stats = {
            'input_count': len(contacts_data),
            'output_count': len(filtered_contacts),
            'duplicates_removed': duplicates_removed,
            'existing_contacts_in_list': len(existing_emails),
        }
        
        _logger.debug("Phase 2: Completed - %d existing contacts filtered out", duplicates_removed)
        return filtered_contacts, phase_stats
    
    def _phase3_cross_source_resolution(self, contacts_data, config):
        """
        Phase 3: Resolve conflicts when contacts exist in multiple sources.
        
        Args:
            contacts_data (list): Contacts from Phase 2
            config (dict): Configuration options
            
        Returns:
            tuple: (resolved_contacts, phase_stats)
        """
        if not contacts_data:
            return [], {'input_count': 0, 'output_count': 0, 'duplicates_removed': 0}
        
        _logger.debug("Phase 3: Cross-source resolution starting")
        
        # Group contacts by normalized email
        normalize_emails = config.get('normalize_emails', True)
        email_groups = defaultdict(list)
        
        for contact in contacts_data:
            email = contact.get('email', '').strip()
            if not email:
                continue
            
            if normalize_emails:
                key = self._normalize_email(email)
            else:
                key = email
            
            email_groups[key].append(contact)
        
        # Resolve conflicts in each group
        resolved_contacts = []
        duplicates_removed = 0
        conflicts_resolved = 0
        
        for email_key, contacts_group in email_groups.items():
            if len(contacts_group) == 1:
                # No conflict, keep the single contact
                resolved_contacts.append(contacts_group[0])
            else:
                # Conflict exists, resolve it
                winner = self._resolve_cross_source_conflict(contacts_group, config)
                resolved_contacts.append(winner)
                duplicates_removed += len(contacts_group) - 1
                conflicts_resolved += 1
                
                _logger.debug(
                    "Phase 3: Resolved conflict for %s, kept %s from %d candidates",
                    email_key, winner.get('source_model', 'unknown'), len(contacts_group)
                )
        
        phase_stats = {
            'input_count': len(contacts_data),
            'output_count': len(resolved_contacts),
            'duplicates_removed': duplicates_removed,
            'conflicts_resolved': conflicts_resolved,
            'unique_email_groups': len(email_groups),
        }
        
        _logger.debug("Phase 3: Completed - %d conflicts resolved", conflicts_resolved)
        return resolved_contacts, phase_stats
    
    # Helper Methods
    
    def _normalize_email(self, email):
        """
        Normalize email address for comparison.
        
        Args:
            email (str): Raw email address
            
        Returns:
            str: Normalized email address
        """
        if not email:
            return ''
        
        # Convert to lowercase and strip whitespace
        normalized = email.lower().strip()
        
        # Handle Gmail-style aliases (ignore dots and plus suffixes)
        if '@gmail.com' in normalized or '@googlemail.com' in normalized:
            local, domain = normalized.split('@', 1)
            
            # Remove dots from local part
            local = local.replace('.', '')
            
            # Remove plus suffixes
            if '+' in local:
                local = local.split('+')[0]
            
            normalized = f"{local}@{domain}"
        
        return normalized
    
    def _resolve_internal_duplicate(self, contact1, contact2, config):
        """
        Resolve duplicate within the same batch.
        
        Args:
            contact1 (dict): First contact
            contact2 (dict): Second contact
            config (dict): Configuration options
            
        Returns:
            dict: Winning contact
        """
        priority = config.get('cross_source_priority', 'partner')
        
        # Priority by source model
        model_priority = {
            'res.partner': 3,
            'crm.lead': 2,
            'hr.employee': 1,
            'event.registration': 1,
        }
        
        model1 = contact1.get('source_model', '')
        model2 = contact2.get('source_model', '')
        
        priority1 = model_priority.get(model1, 0)
        priority2 = model_priority.get(model2, 0)
        
        if priority1 != priority2:
            return contact1 if priority1 > priority2 else contact2
        
        # If same priority, prefer the one with more complete data
        score1 = self._calculate_contact_completeness_score(contact1)
        score2 = self._calculate_contact_completeness_score(contact2)
        
        return contact1 if score1 >= score2 else contact2
    
    def _resolve_cross_source_conflict(self, contacts_group, config):
        """
        Resolve conflict when same contact exists in multiple sources.
        
        Args:
            contacts_group (list): List of conflicting contacts
            config (dict): Configuration options
            
        Returns:
            dict: Winning contact
        """
        if len(contacts_group) == 1:
            return contacts_group[0]
        
        priority_strategy = config.get('cross_source_priority', 'partner')
        
        if priority_strategy == 'newest':
            # Prefer newest record (if we have creation date info)
            return max(contacts_group, key=lambda c: c.get('create_date', ''))
        
        elif priority_strategy == 'oldest':
            # Prefer oldest record
            return min(contacts_group, key=lambda c: c.get('create_date', ''))
        
        elif priority_strategy in ['partner', 'crm']:
            # Prefer specific source model
            preferred_model = 'res.partner' if priority_strategy == 'partner' else 'crm.lead'
            
            # First, try to find preferred model
            for contact in contacts_group:
                if contact.get('source_model') == preferred_model:
                    return contact
            
            # If preferred model not found, fall back to completeness scoring
            return max(contacts_group, key=self._calculate_contact_completeness_score)
        
        else:
            # Default: use completeness scoring
            return max(contacts_group, key=self._calculate_contact_completeness_score)
    
    def _calculate_contact_completeness_score(self, contact):
        """
        Calculate a completeness score for a contact.
        
        Args:
            contact (dict): Contact data
            
        Returns:
            int: Completeness score (higher is better)
        """
        score = 0
        
        # Required fields
        if contact.get('email'):
            score += 10
        if contact.get('name'):
            score += 5
        
        # Optional fields
        if contact.get('phone'):
            score += 3
        
        # Source quality bonus
        source_model = contact.get('source_model', '')
        if source_model == 'res.partner':
            score += 3  # Partners usually have more complete data
        elif source_model == 'crm.lead':
            score += 2  # Leads have moderate data completeness
        
        # Data quality indicators
        email = contact.get('email', '')
        name = contact.get('name', '')
        
        if email and '@' in email and '.' in email:
            score += 2  # Valid email format
        
        if name and len(name) > 3:
            score += 2  # Reasonable name length
        
        if name and ' ' in name.strip():
            score += 1  # Full name (first + last)
        
        return score
    
    # Analysis and Reporting Methods
    
    @api.model
    def analyze_potential_duplicates(self, mailing_list_id, similarity_threshold=0.8):
        """
        Analyze existing mailing list for potential duplicates.
        
        Args:
            mailing_list_id (int): Mailing list to analyze
            similarity_threshold (float): Similarity threshold for flagging
            
        Returns:
            dict: Analysis results
        """
        mailing_list = self.env['mailing.list'].browse(mailing_list_id)
        if not mailing_list.exists():
            return {'error': 'Mailing list not found'}
        
        contacts = self.env['mailing.contact'].search([
            ('list_ids', 'in', mailing_list.id),
            ('email', '!=', False),
        ])
        
        # Group by normalized email
        email_groups = defaultdict(list)
        for contact in contacts:
            normalized_email = self._normalize_email(contact.email)
            email_groups[normalized_email].append(contact)
        
        # Find potential duplicates
        potential_duplicates = []
        total_duplicates = 0
        
        for email, contact_group in email_groups.items():
            if len(contact_group) > 1:
                potential_duplicates.append({
                    'normalized_email': email,
                    'contacts': [{
                        'id': c.id,
                        'email': c.email,
                        'name': c.name,
                        'source_model': c.source_model,
                        'create_date': c.create_date,
                    } for c in contact_group],
                    'count': len(contact_group),
                })
                total_duplicates += len(contact_group) - 1  # -1 because one is kept
        
        return {
            'mailing_list': mailing_list.name,
            'total_contacts': len(contacts),
            'unique_emails': len(email_groups),
            'duplicate_groups': len(potential_duplicates),
            'total_duplicates': total_duplicates,
            'duplicate_rate': total_duplicates / max(len(contacts), 1),
            'potential_duplicates': potential_duplicates[:50],  # Limit for UI
        }
    
    @api.model
    def get_deduplication_report(self, batch_ids=None, date_from=None, date_to=None):
        """
        Generate deduplication performance report.
        
        Args:
            batch_ids (list, optional): Specific batch IDs to analyze
            date_from (datetime, optional): Start date filter
            date_to (datetime, optional): End date filter
            
        Returns:
            dict: Deduplication report
        """
        # Get audit records for deduplication operations
        domain = [
            ('operation_type', '=', 'deduplication_performed'),
            ('company_id', '=', self.env.company.id),
        ]
        
        if batch_ids:
            domain.append(('batch_id', 'in', batch_ids))
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        
        audit_records = self.env['mailing.operation.audit'].search(domain)
        
        total_operations = len(audit_records)
        total_contacts_processed = 0
        total_duplicates_removed = 0
        total_execution_time = 0.0
        
        phase_stats = {
            'phase1_internal': {'duplicates_removed': 0, 'operations': 0},
            'phase2_external': {'duplicates_removed': 0, 'operations': 0},
            'phase3_cross_source': {'duplicates_removed': 0, 'operations': 0},
        }
        
        for record in audit_records:
            total_execution_time += record.execution_time or 0.0
            
            # Parse details for phase information
            try:
                import json
                details = json.loads(record.details or '{}')
                
                total_contacts_processed += details.get('total_input', 0)
                total_duplicates_removed += details.get('removed_count', 0)
                
                # Analyze phase statistics
                phases = details.get('phases', {})
                for phase_name, phase_data in phases.items():
                    if phase_name in phase_stats:
                        phase_stats[phase_name]['duplicates_removed'] += phase_data.get('duplicates_removed', 0)
                        phase_stats[phase_name]['operations'] += 1
                        
            except (ValueError, TypeError):
                continue
        
        return {
            'period': {
                'date_from': date_from,
                'date_to': date_to,
                'batch_ids': batch_ids,
            },
            'summary': {
                'total_operations': total_operations,
                'total_contacts_processed': total_contacts_processed,
                'total_duplicates_removed': total_duplicates_removed,
                'average_duplicate_rate': (
                    total_duplicates_removed / max(total_contacts_processed, 1)
                ),
                'total_execution_time': total_execution_time,
                'average_execution_time': (
                    total_execution_time / max(total_operations, 1)
                ),
            },
            'phase_breakdown': phase_stats,
        }