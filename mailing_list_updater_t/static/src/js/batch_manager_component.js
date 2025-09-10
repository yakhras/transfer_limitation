/** @odoo-module **/

const { Component, useState } = owl;

/**
 * Batch Manager Component for OWL 1.0 (Fixed for Odoo 15.0)
 * 
 * Manages batch operations including history viewing, rollback functionality,
 * and batch statistics display.
 */
class BatchManagerComponent extends Component {
    
    setup() {
        // Services (OWL 1.0 style)
        this.rpc = this.env.services.rpc;
        
        // Component state
        this.state = useState({
            // Batch data
            batches: [],
            currentBatch: null,
            statistics: {},
            
            // UI state
            selectedTab: 'history', // history, details, statistics
            isLoading: false,
            showRollbackDialog: false,
            
            // Pagination
            currentPage: 1,
            pageSize: 10,
            totalBatches: 0,
            
            // Filtering
            statusFilter: 'all', // all, completed, error, processing
            dateFilter: 'all', // all, today, week, month
            searchTerm: '',
            
            // Sorting
            sortField: 'created_date',
            sortDirection: 'desc',
            
            // Rollback state
            rollbackBatch: null,
            rollbackReason: '',
            isRollingBack: false,
            
            // Error handling
            errors: []
        });
        
        // Props from parent (if needed)
        this.mailingListId = this.props.mailingListId;
        
        // Listen for view-batch events from parent
        this.env.bus?.addEventListener('view-batch', this.onViewBatchRequest.bind(this));
    }
    
    /**
     * OWL 1.0 Lifecycle - Will Start
     * Load initial data
     */
    async willStart() {
        await Promise.all([
            this.loadBatchHistory(),
            this.loadStatistics()
        ]);
    }
    
    /**
     * OWL 1.0 Lifecycle - Mounted
     * Setup after component is mounted
     */
    mounted() {
        this.setupRefreshTimer();
    }
    
    /**
     * OWL 1.0 Lifecycle - Will Unmount
     * Component cleanup
     */
    willUnmount() {
        // Clear timers
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        // Remove event listeners
        this.env.bus?.removeEventListener('view-batch', this.onViewBatchRequest);
    }
    
    /**
     * Load batch history with current filters
     */
    async loadBatchHistory() {
        this.state.isLoading = true;
        this.state.errors = [];
        
        try {
            const params = {
                page: this.state.currentPage,
                limit: this.state.pageSize,
                sort_field: this.state.sortField,
                sort_direction: this.state.sortDirection
            };
            
            // Add filters
            if (this.state.statusFilter !== 'all') {
                params.status = this.state.statusFilter;
            }
            
            if (this.state.dateFilter !== 'all') {
                params.date_filter = this.state.dateFilter;
            }
            
            if (this.state.searchTerm) {
                params.search = this.state.searchTerm;
            }
            
            if (this.mailingListId) {
                params.mailing_list_id = this.mailingListId;
            }
            
            const response = await this.rpc({
                route: "/mailing/batch/history",
                params: params
            });
            
            if (response.success) {
                this.state.batches = response.data.batches || [];
                this.state.totalBatches = response.data.total || 0;
            } else {
                throw new Error(response.error?.message || "Failed to load batch history");
            }
            
        } catch (error) {
            this.state.errors.push(error.message);
            this.trigger('show-error', { 
                message: `Failed to load batch history: ${error.message}` 
            });
            console.error("Batch history loading error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * Load batch statistics
     */
    async loadStatistics() {
        try {
            const params = {};
            
            if (this.mailingListId) {
                params.mailing_list_id = this.mailingListId;
            }
            
            const response = await this.rpc({
                route: "/mailing/batch/statistics",
                params: params
            });
            
            if (response.success) {
                this.state.statistics = response.data || {};
            }
            
        } catch (error) {
            console.warn("Statistics loading error:", error);
        }
    }
    
    /**
     * Handle view batch request from parent
     */
    async onViewBatchRequest(event) {
        if (event.detail?.batchId) {
            await this.viewBatchDetails(event.detail.batchId);
        }
    }
    
    /**
     * Setup auto-refresh timer for active batches
     */
    setupRefreshTimer() {
        this.refreshTimer = setInterval(() => {
            // Only refresh if there are processing batches
            const hasProcessingBatches = this.state.batches.some(
                batch => batch.status === 'processing'
            );
            
            if (hasProcessingBatches) {
                this.loadBatchHistory();
            }
        }, 5000); // Refresh every 5 seconds
    }
    
    /**
     * Switch between tabs
     */
    switchTab(tabName) {
        const validTabs = ['history', 'details', 'statistics'];
        if (validTabs.includes(tabName)) {
            this.state.selectedTab = tabName;
        }
    }
    
    /**
     * View batch details
     */
    async viewBatchDetails(batchId) {
        this.state.isLoading = true;
        
        try {
            const response = await this.rpc({
                route: `/mailing/batch/${batchId}`,
                params: { include_contacts: true, include_audit: true }
            });
            
            if (response.success) {
                this.state.currentBatch = response.data;
                this.state.selectedTab = 'details';
            } else {
                throw new Error(response.error?.message || "Failed to load batch details");
            }
            
        } catch (error) {
            this.trigger('show-error', { 
                message: `Failed to load batch details: ${error.message}` 
            });
            console.error("Batch details loading error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * Show rollback confirmation dialog
     */
    showRollbackDialog(batch) {
        if (!batch.can_rollback) {
            this.trigger('show-error', { 
                message: "This batch cannot be rolled back" 
            });
            return;
        }
        
        this.state.rollbackBatch = batch;
        this.state.rollbackReason = '';
        this.state.showRollbackDialog = true;
    }
    
    /**
     * Hide rollback dialog
     */
    hideRollbackDialog() {
        this.state.showRollbackDialog = false;
        this.state.rollbackBatch = null;
        this.state.rollbackReason = '';
    }
    
    /**
     * Execute batch rollback
     */
    async executeRollback() {
        if (!this.state.rollbackBatch || !this.state.rollbackReason.trim()) {
            return;
        }
        
        this.state.isRollingBack = true;
        
        try {
            const response = await this.rpc({
                route: `/mailing/batch/${this.state.rollbackBatch.id}/rollback`,
                params: {
                    reason: this.state.rollbackReason.trim(),
                    confirmed: true
                }
            });
            
            if (response.success) {
                this.trigger('show-success', { 
                    message: "Batch rollback initiated successfully" 
                });
                
                // Refresh batch history
                await this.loadBatchHistory();
                
                // Hide dialog
                this.hideRollbackDialog();
                
            } else {
                throw new Error(response.error?.message || "Rollback failed");
            }
            
        } catch (error) {
            this.trigger('show-error', { 
                message: `Rollback failed: ${error.message}` 
            });
            console.error("Rollback error:", error);
        } finally {
            this.state.isRollingBack = false;
        }
    }
    
    /**
     * Handle filter changes
     */
    onFilterChange(filterType, value) {
        this.state[filterType] = value;
        this.state.currentPage = 1; // Reset to first page
        this.loadBatchHistory();
    }
    
    /**
     * Handle search input
     */
    onSearchInput(event) {
        this.state.searchTerm = event.target.value;
        
        // Debounce search
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.state.currentPage = 1;
            this.loadBatchHistory();
        }, 500);
    }
    
    /**
     * Handle sorting
     */
    sortBatches(field) {
        if (this.state.sortField === field) {
            // Toggle direction if same field
            this.state.sortDirection = this.state.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            // New field, default to descending
            this.state.sortField = field;
            this.state.sortDirection = 'desc';
        }
        
        this.loadBatchHistory();
    }
    
    /**
     * Navigate to specific page
     */
    goToPage(pageNumber) {
        if (pageNumber >= 1 && pageNumber <= this.totalPages) {
            this.state.currentPage = pageNumber;
            this.loadBatchHistory();
        }
    }
    
    /**
     * Go to next page
     */
    nextPage() {
        if (this.state.currentPage < this.totalPages) {
            this.state.currentPage++;
            this.loadBatchHistory();
        }
    }
    
    /**
     * Go to previous page
     */
    previousPage() {
        if (this.state.currentPage > 1) {
            this.state.currentPage--;
            this.loadBatchHistory();
        }
    }
    
    /**
     * Get total pages for pagination
     */
    get totalPages() {
        return Math.ceil(this.state.totalBatches / this.state.pageSize);
    }
    
    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return '-';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
            return 'Today';
        } else if (diffDays === 2) {
            return 'Yesterday';
        } else if (diffDays <= 7) {
            return `${diffDays - 1} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
    
    /**
     * Format duration
     */
    formatDuration(seconds) {
        if (!seconds) return '-';
        
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            return `${minutes}m`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }
    
    /**
     * Format number with thousands separator
     */
    formatNumber(number) {
        return new Intl.NumberFormat().format(number);
    }
    
    /**
     * Get status badge CSS class
     */
    getStatusClass(status) {
        const classes = ['badge'];
        
        switch (status) {
            case 'completed':
                classes.push('badge-success');
                break;
            case 'error':
                classes.push('badge-danger');
                break;
            case 'processing':
                classes.push('badge-info');
                break;
            case 'cancelled':
                classes.push('badge-warning');
                break;
            case 'rolled_back':
                classes.push('badge-secondary');
                break;
            default:
                classes.push('badge-light');
        }
        
        return classes.join(' ');
    }
    
    /**
     * Get status icon
     */
    getStatusIcon(status) {
        const icons = {
            'completed': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'processing': 'fa-spinner fa-spin',
            'cancelled': 'fa-times-circle',
            'rolled_back': 'fa-undo'
        };
        
        return icons[status] || 'fa-question-circle';
    }
    
    /**
     * Check if batch can be rolled back
     */
    canRollback(batch) {
        return batch.status === 'completed' && 
               batch.can_rollback && 
               !batch.rolled_back &&
               batch.rollback_deadline && 
               new Date(batch.rollback_deadline) > new Date();
    }
    
    /**
     * Get rollback deadline text
     */
    getRollbackDeadlineText(batch) {
        if (!batch.rollback_deadline) return '';
        
        const deadline = new Date(batch.rollback_deadline);
        const now = new Date();
        const diffHours = Math.ceil((deadline - now) / (1000 * 60 * 60));
        
        if (diffHours <= 0) {
            return 'Expired';
        } else if (diffHours <= 24) {
            return `${diffHours}h remaining`;
        } else {
            const diffDays = Math.floor(diffHours / 24);
            return `${diffDays}d remaining`;
        }
    }
    
    /**
     * Export batch data
     */
    exportBatchData(batch) {
        const exportData = {
            batch_info: {
                id: batch.id,
                created_date: batch.created_date,
                status: batch.status,
                mailing_list: batch.mailing_list_name,
                user: batch.user_name
            },
            statistics: batch.statistics,
            contacts: batch.contacts,
            audit_trail: batch.audit_entries
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `batch_${batch.id}_export.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    /**
     * Refresh data
     */
    async refresh() {
        await Promise.all([
            this.loadBatchHistory(),
            this.loadStatistics()
        ]);
    }
    
    /**
     * Get filter badge count
     */
    getFilterBadgeCount(filter) {
        // Count batches matching specific filter
        return this.state.batches.filter(batch => {
            switch (filter) {
                case 'completed':
                    return batch.status === 'completed';
                case 'error':
                    return batch.status === 'error';
                case 'processing':
                    return batch.status === 'processing';
                default:
                    return true;
            }
        }).length;
    }
    
    /**
     * Get statistics summary for display
     */
    get statisticsSummary() {
        const stats = this.state.statistics;
        
        return {
            totalBatches: stats.total_batches || 0,
            successfulBatches: stats.successful_batches || 0,
            failedBatches: stats.failed_batches || 0,
            totalContactsProcessed: stats.total_contacts_processed || 0,
            averageExecutionTime: stats.average_execution_time || 0,
            successRate: stats.success_rate || 0
        };
    }
}

// OWL 1.0 component registration
BatchManagerComponent.template = 'mailing_list_updater_t.BatchManagerTemplate';
BatchManagerComponent.props = {
    mailingListId: { validate: (value) => value === null || value === undefined || typeof value === 'number' },
};

export { BatchManagerComponent };