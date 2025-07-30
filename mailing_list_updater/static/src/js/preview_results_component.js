/** @odoo-module **/

const { Component, useState } = owl;

/**
 * Preview Results Component for OWL 1.0 (Fixed for Odoo 15.0)
 * 
 * Displays contact preview with statistics, sample data, and deduplication info
 * before the user executes the mailing list update.
 */
class PreviewResultsComponent extends Component {
    
    setup() {
        // Services (OWL 1.0 style)
        this.rpc = this.env.services.rpc;
        
        // Component state
        this.state = useState({
            // Preview data
            previewData: null,
            sampleContacts: [],
            statistics: {},
            deduplicationStats: {},
            
            // Loading states
            isLoading: false,
            isGeneratingPreview: false,
            
            // UI state
            selectedTab: 'overview', // overview, contacts, deduplication
            sortField: 'name',
            sortDirection: 'asc',
            currentPage: 1,
            pageSize: 20,
            
            // Error handling
            errors: [],
            
            // Execution state
            canExecute: false,
            executionEstimate: null
        });
        
        // Props from parent
        this.selectedMailingList = this.props.selectedMailingList;
        this.selectedSources = this.props.selectedSources || [];
        this.filterCriteria = this.props.filterCriteria || {};
    }
    
    /**
     * OWL 1.0 Lifecycle - Will Start
     * Auto-generate preview when component loads
     */
    async willStart() {
        await this.generatePreview();
    }
    
    /**
     * Generate contact preview based on current selections
     */
    async generatePreview() {
        if (!this.selectedMailingList || !this.selectedSources.length) {
            return;
        }
        
        this.state.isGeneratingPreview = true;
        this.state.errors = [];
        
        try {
            const requestData = {
                mailing_list_id: this.selectedMailingList.id,
                source_models: this.selectedSources.map(source => ({
                    model_name: source.model_name,
                    enabled: true
                })),
                quick_filters: this.filterCriteria.quick_filters || {},
                advanced_filters: this.filterCriteria.advanced_filters || {}
            };
            
            const response = await this.rpc({
                route: "/mailing/update/preview",
                params: requestData
            });
            
            if (response.success) {
                this.state.previewData = response.data;
                this.state.sampleContacts = response.data.sample_contacts || [];
                this.state.statistics = response.data.statistics || {};
                this.state.deduplicationStats = response.data.deduplication_stats || {};
                this.state.executionEstimate = response.data.execution_estimate || null;
                this.state.canExecute = response.data.total_after_dedup > 0;
                
                // Notify parent that preview is ready
                this.trigger('preview-ready', {
                    previewData: this.state.previewData,
                    canExecute: this.state.canExecute
                });
                
            } else {
                throw new Error(response.error?.message || "Preview generation failed");
            }
            
        } catch (error) {
            this.state.errors.push(error.message);
            this.trigger('show-error', { 
                message: `Preview generation failed: ${error.message}` 
            });
            console.error("Preview generation error:", error);
        } finally {
            this.state.isGeneratingPreview = false;
        }
    }
    
    /**
     * Refresh preview with current settings
     */
    async refreshPreview() {
        await this.generatePreview();
    }
    
    /**
     * Switch between tabs
     */
    switchTab(tabName) {
        const validTabs = ['overview', 'contacts', 'deduplication'];
        if (validTabs.includes(tabName)) {
            this.state.selectedTab = tabName;
        }
    }
    
    /**
     * Handle contact table sorting
     */
    sortContacts(field) {
        if (this.state.sortField === field) {
            // Toggle direction if same field
            this.state.sortDirection = this.state.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            // New field, default to ascending
            this.state.sortField = field;
            this.state.sortDirection = 'asc';
        }
        
        this.applySorting();
    }
    
    /**
     * Apply sorting to sample contacts
     */
    applySorting() {
        this.state.sampleContacts.sort((a, b) => {
            const field = this.state.sortField;
            const direction = this.state.sortDirection;
            
            let valueA = a[field] || '';
            let valueB = b[field] || '';
            
            // Handle different data types
            if (typeof valueA === 'string') {
                valueA = valueA.toLowerCase();
                valueB = valueB.toLowerCase();
            }
            
            let comparison = 0;
            if (valueA > valueB) {
                comparison = 1;
            } else if (valueA < valueB) {
                comparison = -1;
            }
            
            return direction === 'desc' ? comparison * -1 : comparison;
        });
    }
    
    /**
     * Get paginated contacts for display
     */
    get paginatedContacts() {
        const startIndex = (this.state.currentPage - 1) * this.state.pageSize;
        const endIndex = startIndex + this.state.pageSize;
        return this.state.sampleContacts.slice(startIndex, endIndex);
    }
    
    /**
     * Get total pages for pagination
     */
    get totalPages() {
        return Math.ceil(this.state.sampleContacts.length / this.state.pageSize);
    }
    
    /**
     * Navigate to specific page
     */
    goToPage(pageNumber) {
        if (pageNumber >= 1 && pageNumber <= this.totalPages) {
            this.state.currentPage = pageNumber;
        }
    }
    
    /**
     * Go to next page
     */
    nextPage() {
        if (this.state.currentPage < this.totalPages) {
            this.state.currentPage++;
        }
    }
    
    /**
     * Go to previous page
     */
    previousPage() {
        if (this.state.currentPage > 1) {
            this.state.currentPage--;
        }
    }
    
    /**
     * Format number with thousands separator
     */
    formatNumber(number) {
        return new Intl.NumberFormat().format(number);
    }
    
    /**
     * Format percentage
     */
    formatPercentage(value, total) {
        if (!total || total === 0) return '0%';
        return `${Math.round((value / total) * 100)}%`;
    }
    
    /**
     * Get CSS class for statistic based on value
     */
    getStatisticClass(key, value) {
        const classes = ['statistic-item'];
        
        switch (key) {
            case 'duplicates_removed':
                if (value > 0) classes.push('warning');
                break;
            case 'invalid_emails':
                if (value > 0) classes.push('danger');
                break;
            case 'total_after_dedup':
                if (value === 0) classes.push('danger');
                else if (value > 100) classes.push('success');
                break;
        }
        
        return classes.join(' ');
    }
    
    /**
     * Get deduplication method description
     */
    getDeduplicationMethodDescription(method) {
        const descriptions = {
            'email': 'Contacts with identical email addresses',
            'phone': 'Contacts with identical phone numbers',
            'name_company': 'Contacts with identical name and company',
            'custom': 'Custom deduplication rules'
        };
        
        return descriptions[method] || method;
    }
    
    /**
     * Get source statistics for display
     */
    get sourceStatistics() {
        if (!this.state.statistics.by_source) return [];
        
        return Object.entries(this.state.statistics.by_source).map(([sourceName, stats]) => ({
            name: sourceName,
            total: stats.total || 0,
            valid: stats.valid || 0,
            invalid: stats.invalid || 0,
            percentage: this.formatPercentage(stats.valid, this.state.statistics.total_found)
        }));
    }
    
    /**
     * Export preview data (for debugging or analysis)
     */
    exportPreviewData() {
        const exportData = {
            timestamp: new Date().toISOString(),
            mailing_list: this.selectedMailingList.name,
            sources: this.selectedSources.map(s => s.name),
            statistics: this.state.statistics,
            sample_contacts: this.state.sampleContacts,
            filters_applied: this.filterCriteria
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mailing_preview_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    /**
     * Handle execution request
     */
    executeUpdate() {
        if (!this.state.canExecute) {
            return;
        }
        
        this.trigger('execute-update', {
            previewData: this.state.previewData,
            confirmedEstimate: this.state.executionEstimate
        });
    }
    
    /**
     * Get execution button text based on state
     */
    get executionButtonText() {
        if (!this.state.canExecute) {
            return 'No contacts to add';
        }
        
        const count = this.state.statistics.total_after_dedup || 0;
        return `Add ${this.formatNumber(count)} contacts`;
    }
    
    /**
     * Get execution button class
     */
    get executionButtonClass() {
        const classes = ['btn', 'btn-primary'];
        
        if (!this.state.canExecute) {
            classes.push('btn-secondary');
            classes.push('disabled');
        }
        
        return classes.join(' ');
    }
    
    /**
     * Format execution time estimate
     */
    formatExecutionTime(seconds) {
        if (seconds < 60) {
            return `${seconds} seconds`;
        } else if (seconds < 3600) {
            return `${Math.round(seconds / 60)} minutes`;
        } else {
            return `${Math.round(seconds / 3600)} hours`;
        }
    }
    
    /**
     * Check if preview data is valid and complete
     */
    get isPreviewValid() {
        return this.state.previewData && 
               this.state.statistics && 
               !this.state.isGeneratingPreview &&
               this.state.errors.length === 0;
    }
    
    /**
     * Get contact field display value
     */
    getContactFieldValue(contact, field) {
        const value = contact[field];
        
        if (value === null || value === undefined) {
            return '-';
        }
        
        // Handle different field types
        if (field.includes('date') && value) {
            return new Date(value).toLocaleDateString();
        }
        
        if (typeof value === 'boolean') {
            return value ? 'Yes' : 'No';
        }
        
        if (Array.isArray(value)) {
            return value.join(', ');
        }
        
        return value.toString();
    }
}

// OWL 1.0 component registration
PreviewResultsComponent.template = 'mailing_list_updater.PreviewResultsTemplate';
PreviewResultsComponent.props = {
    selectedMailingList: { type: Object, optional: true },
    selectedSources: { type: Array, optional: true },
    filterCriteria: { type: Object, optional: true },
};

export { PreviewResultsComponent };