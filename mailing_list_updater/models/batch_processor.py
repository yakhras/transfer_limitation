# -*- coding: utf-8 -*-

import logging
import time
import json
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MailingBatchProcessor(models.TransientModel):
    """
    Batch processor for handling large-scale mailing list operations.
    
    This transient model provides optimized batch processing capabilities
    for handling large volumes of contacts with performance monitoring,
    progress tracking, and error recovery.
    """
    
    _name = 'mailing.batch.processor'
    _description = 'Mailing Batch Processor'
    
    # Configuration Fields
    batch_size = fields.Integer(
        string='Batch Size',
        default=1000,
        help='Number of records to process per batch'
    )
    
    max_execution_time = fields.Integer(
        string='Max Execution Time (seconds)',
        default=300,
        help='Maximum time allowed for batch processing'
    )
    
    enable_progress_tracking = fields.Boolean(
        string='Enable Progress Tracking',
        default=True,
        help='Track and report progress during processing'
    )
    
    # Processing Methods
    
    @api.model
    def process_contact_batch(self, batch_record, contacts_data, config=None):
        """
        Process a batch of contacts with optimized performance.
        
        Args:
            batch_record (recordset): mailing.list.update.batch record
            contacts_data (list): List of contact data to process
            config (dict, optional): Processing configuration
            
        Returns:
            dict: Processing results
        """
        if not contacts_data:
            return {
                'success': True,
                'contacts_processed': 0,
                'contacts_created': 0,
                'execution_time': 0.0,
                'batches_processed': 0,
            }
        
        config = config or {}
        batch_size = config.get('batch_size', self.batch_size or 1000)
        max_time = config.get('max_execution_time', self.max_execution_time or 300)
        
        start_time = time.time()
        total_contacts = len(contacts_data)
        contacts_processed = 0
        contacts_created = 0
        batches_processed = 0
        errors = []
        
        _logger.info(
            "Starting batch processing for %d contacts (batch_size=%d, max_time=%ds)",
            total_contacts, batch_size, max_time
        )
        
        try:
            # Process contacts in batches
            for i in range(0, total_contacts, batch_size):
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Check time limit
                if elapsed_time > max_time:
                    _logger.warning(
                        "Batch processing stopped due to time limit (%ds elapsed)",
                        elapsed_time
                    )
                    break
                
                # Get current batch slice
                batch_slice = contacts_data[i:i + batch_size]
                batch_start_time = time.time()
                
                # Process current batch
                try:
                    batch_results = self._process_contact_batch_slice(
                        batch_record, batch_slice, config
                    )
                    
                    contacts_processed += batch_results['contacts_processed']
                    contacts_created += batch_results['contacts_created']
                    batches_processed += 1
                    
                    # Update progress
                    if config.get('enable_progress_tracking', True):
                        self._update_batch_progress(
                            batch_record, contacts_processed, total_contacts
                        )
                    
                    batch_time = time.time() - batch_start_time
                    _logger.debug(
                        "Processed batch %d/%d: %d contacts in %.2fs",
                        batches_processed, 
                        (total_contacts + batch_size - 1) // batch_size,
                        len(batch_slice), batch_time
                    )
                    
                except Exception as e:
                    error_msg = str(e)
                    errors.append({
                        'batch_index': batches_processed,
                        'start_index': i,
                        'end_index': min(i + batch_size, total_contacts),
                        'error': error_msg,
                    })
                    
                    _logger.error(
                        "Error processing batch %d (contacts %d-%d): %s",
                        batches_processed, i, min(i + batch_size, total_contacts), error_msg
                    )
                    
                    # Decide whether to continue or stop
                    if not config.get('continue_on_error', True):
                        raise UserError(_("Batch processing failed: %s") % error_msg)
                
                # Commit batch to avoid long-running transactions
                if config.get('commit_batches', True):
                    self.env.cr.commit()
        
        except Exception as e:
            _logger.error("Critical error in batch processing: %s", str(e))
            raise
        
        finally:
            total_time = time.time() - start_time
            
            # Log final results
            _logger.info(
                "Batch processing completed: %d/%d contacts processed, %d created in %.2fs",
                contacts_processed, total_contacts, contacts_created, total_time
            )
            
            # Update final batch status
            batch_record.write({
                'contacts_found': total_contacts,
                'contacts_added': contacts_created,
            })
        
        return {
            'success': len(errors) == 0,
            'contacts_processed': contacts_processed,
            'contacts_created': contacts_created,
            'total_contacts': total_contacts,
            'execution_time': time.time() - start_time,
            'batches_processed': batches_processed,
            'errors': errors,
            'performance': {
                'avg_batch_time': (time.time() - start_time) / max(batches_processed, 1),
                'contacts_per_second': contacts_processed / max(time.time() - start_time, 1),
            }
        }
    
    def _process_contact_batch_slice(self, batch_record, contacts_slice, config):
        """
        Process a single slice of contacts.
        
        Args:
            batch_record (recordset): Batch record
            contacts_slice (list): Slice of contacts to process
            config (dict): Processing configuration
            
        Returns:
            dict: Slice processing results
        """
        contacts_processed = 0
        contacts_created = 0
        
        # Create mailing contacts in bulk
        contact_vals_list = []
        tracking_vals_list = []
        
        for contact_data in contacts_slice:
            if not contact_data.get('email'):
                continue
            
            # Prepare mailing contact values
            contact_vals = {
                'email': contact_data['email'],
                'name': contact_data.get('name', contact_data['email']),
                'list_ids': [(4, batch_record.mailing_list_id.id)],
                'source_model': contact_data.get('source_model'),
                'source_record_id': contact_data.get('source_record_id'),
                'last_batch_id': batch_record.batch_id,
                'is_auto_added': True,
                'company_id': batch_record.company_id.id,
            }
            
            contact_vals_list.append(contact_vals)
            contacts_processed += 1
        
        # Bulk create mailing contacts
        if contact_vals_list:
            created_contacts = self.env['mailing.contact'].create(contact_vals_list)
            contacts_created = len(created_contacts)
            
            # Create tracking records
            for i, contact in enumerate(created_contacts):
                contact_data = contacts_slice[i]
                tracking_vals_list.append({
                    'batch_id': batch_record.batch_id,
                    'mailing_contact_id': contact.id,
                    'source_model': contact_data.get('source_model'),
                    'source_record_id': contact_data.get('source_record_id'),
                    'original_email': contact_data.get('email'),
                    'original_name': contact_data.get('name'),
                    'original_phone': contact_data.get('phone'),
                    'company_id': batch_record.company_id.id,
                })
            
            # Bulk create tracking records
            if tracking_vals_list:
                self.env['mailing.contact.tracking'].create(tracking_vals_list)
        
        return {
            'contacts_processed': contacts_processed,
            'contacts_created': contacts_created,
        }
    
    def _update_batch_progress(self, batch_record, processed, total):
        """
        Update batch processing progress.
        
        Args:
            batch_record (recordset): Batch record
            processed (int): Number of contacts processed
            total (int): Total number of contacts
        """
        if total > 0:
            progress_percentage = (processed / total) * 100
            
            # Update batch record with progress info
            # Note: This would typically integrate with a progress tracking system
            _logger.debug(
                "Batch %s progress: %d/%d (%.1f%%)",
                batch_record.batch_id, processed, total, progress_percentage
            )
    
    # Performance Analysis Methods
    
    @api.model
    def analyze_batch_performance(self, batch_ids=None, date_from=None, date_to=None):
        """
        Analyze performance of batch operations.
        
        Args:
            batch_ids (list, optional): Specific batch IDs to analyze
            date_from (datetime, optional): Start date filter
            date_to (datetime, optional): End date filter
            
        Returns:
            dict: Performance analysis results
        """
        domain = [('company_id', '=', self.env.company.id)]
        
        if batch_ids:
            domain.append(('batch_id', 'in', batch_ids))
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        
        batches = self.env['mailing.list.update.batch'].search(domain)
        
        if not batches:
            return {
                'total_batches': 0,
                'analysis': 'No batches found for the specified criteria'
            }
        
        # Collect performance metrics
        total_batches = len(batches)
        total_contacts_processed = sum(batch.contacts_found for batch in batches)
        total_contacts_added = sum(batch.contacts_added for batch in batches)
        total_execution_time = sum(batch.execution_time for batch in batches)
        
        successful_batches = batches.filtered(lambda b: b.state == 'completed')
        failed_batches = batches.filtered(lambda b: b.state == 'failed')
        
        # Calculate averages and rates
        avg_execution_time = total_execution_time / max(total_batches, 1)
        avg_contacts_per_batch = total_contacts_processed / max(total_batches, 1)
        success_rate = len(successful_batches) / max(total_batches, 1)
        
        # Performance categories
        fast_batches = batches.filtered(lambda b: b.execution_time < 30)
        medium_batches = batches.filtered(lambda b: 30 <= b.execution_time < 120)
        slow_batches = batches.filtered(lambda b: b.execution_time >= 120)
        
        # Size categories
        small_batches = batches.filtered(lambda b: b.contacts_found < 100)
        medium_size_batches = batches.filtered(lambda b: 100 <= b.contacts_found < 1000)
        large_batches = batches.filtered(lambda b: b.contacts_found >= 1000)
        
        return {
            'analysis_period': {
                'date_from': date_from,
                'date_to': date_to,
                'batch_ids': batch_ids,
            },
            'summary': {
                'total_batches': total_batches,
                'successful_batches': len(successful_batches),
                'failed_batches': len(failed_batches),
                'success_rate': success_rate,
                'total_contacts_processed': total_contacts_processed,
                'total_contacts_added': total_contacts_added,
                'total_execution_time': total_execution_time,
            },
            'averages': {
                'avg_execution_time': avg_execution_time,
                'avg_contacts_per_batch': avg_contacts_per_batch,
                'avg_contacts_per_second': (
                    total_contacts_processed / max(total_execution_time, 1)
                ),
            },
            'performance_distribution': {
                'fast_batches': len(fast_batches),  # < 30s
                'medium_batches': len(medium_batches),  # 30-120s
                'slow_batches': len(slow_batches),  # > 120s
            },
            'size_distribution': {
                'small_batches': len(small_batches),  # < 100 contacts
                'medium_size_batches': len(medium_size_batches),  # 100-1000 contacts
                'large_batches': len(large_batches),  # > 1000 contacts
            },
            'top_performers': [
                {
                    'batch_id': batch.batch_id,
                    'contacts_processed': batch.contacts_found,
                    'execution_time': batch.execution_time,
                    'contacts_per_second': (
                        batch.contacts_found / max(batch.execution_time, 1)
                    ),
                    'user': batch.user_id.name,
                    'create_date': batch.create_date,
                }
                for batch in successful_batches.sorted(
                    lambda b: b.contacts_found / max(b.execution_time, 1), 
                    reverse=True
                )[:10]
            ],
        }
    
    @api.model
    def optimize_batch_size(self, sample_size=100, target_time=60):
        """
        Recommend optimal batch size based on system performance.
        
        Args:
            sample_size (int): Number of contacts to use for testing
            target_time (int): Target execution time in seconds
            
        Returns:
            dict: Batch size recommendations
        """
        # This would run performance tests with different batch sizes
        # For now, return theoretical recommendations based on system analysis
        
        # Get recent batch performance data
        recent_batches = self.env['mailing.list.update.batch'].search([
            ('state', '=', 'completed'),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=30)),
            ('company_id', '=', self.env.company.id),
        ], limit=50)
        
        if not recent_batches:
            return {
                'recommendation': 1000,
                'confidence': 'low',
                'note': 'No recent batch data available, using default recommendation'
            }
        
        # Analyze performance patterns
        performance_data = []
        for batch in recent_batches:
            if batch.execution_time > 0 and batch.contacts_found > 0:
                contacts_per_second = batch.contacts_found / batch.execution_time
                performance_data.append({
                    'contacts': batch.contacts_found,
                    'time': batch.execution_time,
                    'rate': contacts_per_second,
                })
        
        if not performance_data:
            return {
                'recommendation': 1000,
                'confidence': 'low',
                'note': 'Insufficient performance data'
            }
        
        # Calculate average processing rate
        avg_rate = sum(d['rate'] for d in performance_data) / len(performance_data)
        
        # Calculate recommended batch size for target time
        recommended_size = int(avg_rate * target_time)
        
        # Apply practical bounds
        recommended_size = max(100, min(recommended_size, 5000))
        
        # Determine confidence based on data consistency
        rates = [d['rate'] for d in performance_data]
        rate_variance = sum((r - avg_rate) ** 2 for r in rates) / len(rates)
        confidence = 'high' if rate_variance < (avg_rate * 0.5) else 'medium'
        
        return {
            'recommendation': recommended_size,
            'confidence': confidence,
            'analysis': {
                'avg_processing_rate': avg_rate,
                'target_time': target_time,
                'sample_batches': len(performance_data),
                'rate_variance': rate_variance,
            },
            'alternatives': {
                'conservative': max(100, int(recommended_size * 0.7)),
                'aggressive': min(5000, int(recommended_size * 1.3)),
            }
        }
    
    # Error Recovery Methods
    
    @api.model
    def recover_failed_batch(self, batch_id, retry_config=None):
        """
        Attempt to recover a failed batch operation.
        
        Args:
            batch_id (str): Batch ID to recover
            retry_config (dict, optional): Recovery configuration
            
        Returns:
            dict: Recovery results
        """
        batch_record = self.env['mailing.list.update.batch'].search([
            ('batch_id', '=', batch_id)
        ], limit=1)
        
        if not batch_record:
            return {'success': False, 'error': 'Batch not found'}
        
        if batch_record.state != 'failed':
            return {'success': False, 'error': 'Batch is not in failed state'}
        
        retry_config = retry_config or {}
        
        try:
            _logger.info("Attempting to recover failed batch %s", batch_id)
            
            # Reset batch state
            batch_record.write({
                'state': 'draft',
                'error_message': False,
                'end_time': False,
            })
            
            # Get original configuration
            try:
                source_models = json.loads(batch_record.source_models or '[]')
                filter_criteria = json.loads(batch_record.filter_criteria or '{}')
            except (ValueError, TypeError):
                return {'success': False, 'error': 'Invalid batch configuration'}
            
            # Retry execution with recovery configuration
            recovery_config = {
                'batch_size': retry_config.get('batch_size', 500),  # Smaller batches
                'continue_on_error': True,  # Continue despite errors
                'commit_batches': True,  # Commit more frequently
            }
            
            result = batch_record.execute_update(
                source_models, filter_criteria, preview_only=False
            )
            
            if result.get('success'):
                _logger.info("Successfully recovered batch %s", batch_id)
                return {
                    'success': True,
                    'batch_id': batch_id,
                    'contacts_added': result.get('contacts_added', 0),
                    'recovery_method': 'retry_execution',
                }
            else:
                return {'success': False, 'error': 'Recovery execution failed'}
        
        except Exception as e:
            error_msg = str(e)
            _logger.error("Failed to recover batch %s: %s", batch_id, error_msg)
            
            # Restore failed state
            batch_record.write({
                'state': 'failed',
                'error_message': f"Recovery failed: {error_msg}",
            })
            
            return {'success': False, 'error': error_msg}
    
    @api.model
    def cleanup_processing_resources(self, hours_old=24):
        """
        Clean up old processing resources and temporary data.
        
        Args:
            hours_old (int): Age threshold in hours
            
        Returns:
            dict: Cleanup results
        """
        cutoff_time = fields.Datetime.now() - timedelta(hours=hours_old)
        
        # Find stale processing batches
        stale_batches = self.env['mailing.list.update.batch'].search([
            ('state', '=', 'processing'),
            ('start_time', '<=', cutoff_time),
        ])
        
        cleanup_results = {
            'stale_batches_found': len(stale_batches),
            'stale_batches_cleaned': 0,
        }
        
        # Mark stale batches as failed
        for batch in stale_batches:
            try:
                batch.write({
                    'state': 'failed',
                    'end_time': fields.Datetime.now(),
                    'error_message': 'Batch processing timed out and was automatically failed',
                })
                cleanup_results['stale_batches_cleaned'] += 1
                
                _logger.warning(
                    "Marked stale batch %s as failed (started %s)",
                    batch.batch_id, batch.start_time
                )
            
            except Exception as e:
                _logger.error(
                    "Error cleaning up stale batch %s: %s",
                    batch.batch_id, str(e)
                )
        
        return cleanup_results