/** @odoo-module **/

const { Component, useState } = owl;

/**
 * Progress Tracker Component for OWL 1.0 (Fixed for Odoo 15.0)
 * 
 * Displays real-time progress updates during mailing list batch execution
 * with WebSocket integration and fallback mechanisms.
 */
class ProgressTrackerComponent extends Component {
    
    setup() {
        // Services (OWL 1.0 style)
        this.rpc = this.env.services.rpc;
        
        // Component state
        this.state = useState({
            // Progress data
            progress: 0, // 0-100
            status: 'idle', // idle, processing, completed, error, cancelled
            statusMessage: 'Waiting to start...',
            
            // Operation details
            currentOperation: '',
            processedCount: 0,
            totalCount: 0,
            
            // Time tracking
            startTime: null,
            estimatedTimeRemaining: null,
            elapsedTime: 0,
            
            // Statistics
            statistics: {
                contactsAdded: 0,
                duplicatesSkipped: 0,
                errorsEncountered: 0,
                successRate: 0
            },
            
            // UI state
            isVisible: false,
            canCancel: true,
            showDetails: false,
            logs: [],
            
            // Animation
            isAnimating: false
        });
        
        // Props from parent
        this.batchId = this.props.batchId;
        this.initialProgress = this.props.initialProgress || 0;
        this.initialStatus = this.props.initialStatus || 'idle';
        
        // Timer references
        this.progressTimer = null;
        this.elapsedTimer = null;
        
        // Initialize progress if provided
        if (this.initialProgress > 0) {
            this.state.progress = this.initialProgress;
            this.state.status = this.initialStatus;
            this.state.isVisible = true;
        }
        
        // Listen for parent events as fallback
        this.env.bus?.addEventListener('progress-update', this.onProgressUpdate.bind(this));
        this.env.bus?.addEventListener('start-tracking', this.onStartTracking.bind(this));
    }
    
    /**
     * OWL 1.0 Lifecycle - Mounted
     * Component mounted - start tracking if batch is active
     */
    mounted() {
        if (this.batchId && this.state.status === 'processing') {
            this.startTracking();
        }
        
        // Notify parent that component is ready
        this.trigger('progress-tracker-ready', { component: this });
    }
    
    /**
     * OWL 1.0 Lifecycle - Will Unmount
     * Component cleanup
     */
    willUnmount() {
        this.cleanup();
    }
    
    /**
     * Handle progress update events from parent
     */
    onProgressUpdate(event) {
        if (event.detail) {
            this.updateProgress(event.detail);
        }
    }
    
    /**
     * Handle start tracking events from parent
     */
    onStartTracking(event) {
        if (event.detail?.batchId) {
            this.batchId = event.detail.batchId;
            this.startTracking();
        }
    }
    
    /**
     * Update batch ID (for dynamic assignment)
     */
    setBatchId(batchId) {
        this.batchId = batchId;
    }
    
    /**
     * Start progress tracking
     */
    startTracking() {
        this.state.isVisible = true;
        this.state.startTime = new Date();
        this.state.status = 'processing';
        this.state.statusMessage = 'Starting batch operation...';
        
        // Start elapsed time counter
        this.startElapsedTimer();
        
        // Start progress monitoring
        this.startProgressMonitoring();
        
        // Add initial log entry
        this.addLogEntry('info', 'Batch operation started');
    }
    
    /**
     * Update progress from external source (WebSocket/polling)
     */
    updateProgress(progressData) {
        this.state.progress = Math.min(100, Math.max(0, progressData.progress || 0));
        this.state.status = progressData.status || this.state.status;
        this.state.statusMessage = progressData.message || this.state.statusMessage;
        this.state.currentOperation = progressData.current_operation || this.state.currentOperation;
        
        // Update counts
        if (progressData.processed_count !== undefined) {
            this.state.processedCount = progressData.processed_count;
        }
        if (progressData.total_count !== undefined) {
            this.state.totalCount = progressData.total_count;
        }
        
        // Update statistics
        if (progressData.statistics) {
            Object.assign(this.state.statistics, progressData.statistics);
        }
        
        // Calculate time estimates
        this.updateTimeEstimates();
        
        // Handle completion
        if (progressData.status === 'completed') {
            this.handleCompletion();
        } else if (progressData.status === 'error') {
            this.handleError(progressData.error || 'Unknown error occurred');
        }
        
        // Add log entry for significant updates
        if (progressData.log_message) {
            this.addLogEntry(progressData.log_level || 'info', progressData.log_message);
        }
        
        // Trigger animation for visual feedback
        this.triggerProgressAnimation();
    }
    
    /**
     * Start elapsed time counter
     */
    startElapsedTimer() {
        this.elapsedTimer = setInterval(() => {
            if (this.state.startTime && this.state.status === 'processing') {
                this.state.elapsedTime = Math.floor((new Date() - this.state.startTime) / 1000);
            }
        }, 1000);
    }
    
    /**
     * Start progress monitoring (fallback polling)
     */
    startProgressMonitoring() {
        if (!this.batchId) return;
        
        this.progressTimer = setInterval(async () => {
            if (this.state.status !== 'processing') {
                clearInterval(this.progressTimer);
                return;
            }
            
            try {
                const response = await this.rpc({
                    route: `/mailing/update/progress/${this.batchId}`
                });
                
                if (response.success) {
                    this.updateProgress(response.data);
                }
            } catch (error) {
                console.warn('Progress monitoring error:', error);
            }
        }, 3000); // Poll every 3 seconds
    }
    
    /**
     * Update time estimates
     */
    updateTimeEstimates() {
        if (this.state.progress > 0 && this.state.elapsedTime > 0) {
            const progressRatio = this.state.progress / 100;
            const totalEstimatedTime = this.state.elapsedTime / progressRatio;
            this.state.estimatedTimeRemaining = Math.max(0, totalEstimatedTime - this.state.elapsedTime);
        }
    }
    
    /**
     * Handle successful completion
     */
    handleCompletion() {
        this.state.status = 'completed';
        this.state.progress = 100;
        this.state.statusMessage = 'Batch operation completed successfully!';
        this.state.canCancel = false;
        
        this.addLogEntry('success', 'Batch operation completed successfully');
        
        // Notify parent
        this.trigger('operation-completed', {
            batchId: this.batchId,
            statistics: this.state.statistics,
            elapsedTime: this.state.elapsedTime
        });
        
        // Auto-hide after delay
        setTimeout(() => {
            this.state.isVisible = false;
        }, 5000);
    }
    
    /**
     * Handle error
     */
    handleError(errorMessage) {
        this.state.status = 'error';
        this.state.statusMessage = `Error: ${errorMessage}`;
        this.state.canCancel = false;
        
        this.addLogEntry('error', errorMessage);
        
        // Notify parent
        this.trigger('operation-error', {
            batchId: this.batchId,
            error: errorMessage,
            statistics: this.state.statistics
        });
    }
    
    /**
     * Cancel batch operation
     */
    async cancelOperation() {
        if (!this.state.canCancel || !this.batchId) return;
        
        try {
            const response = await this.rpc({
                route: `/mailing/batch/${this.batchId}/cancel`,
                params: { reason: 'User requested cancellation' }
            });
            
            if (response.success) {
                this.state.status = 'cancelled';
                this.state.statusMessage = 'Operation cancelled by user';
                this.state.canCancel = false;
                
                this.addLogEntry('warning', 'Operation cancelled by user');
                
                // Notify parent
                this.trigger('operation-cancelled', {
                    batchId: this.batchId
                });
            }
        } catch (error) {
            this.addLogEntry('error', `Failed to cancel operation: ${error.message}`);
        }
    }
    
    /**
     * Add log entry
     */
    addLogEntry(level, message) {
        const entry = {
            id: Date.now(),
            timestamp: new Date(),
            level: level, // info, success, warning, error
            message: message
        };
        
        this.state.logs.unshift(entry);
        
        // Keep only last 50 entries
        if (this.state.logs.length > 50) {
            this.state.logs = this.state.logs.slice(0, 50);
        }
    }
    
    /**
     * Toggle details visibility
     */
    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
    }
    
    /**
     * Trigger progress bar animation
     */
    triggerProgressAnimation() {
        this.state.isAnimating = true;
        setTimeout(() => {
            this.state.isAnimating = false;
        }, 300);
    }
    
    /**
     * Format time in human readable format
     */
    formatTime(seconds) {
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}m ${remainingSeconds}s`;
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
     * Get progress bar CSS class
     */
    get progressBarClass() {
        const classes = ['progress-bar'];
        
        switch (this.state.status) {
            case 'processing':
                classes.push('progress-bar-info');
                if (this.state.isAnimating) {
                    classes.push('progress-bar-animated');
                }
                break;
            case 'completed':
                classes.push('progress-bar-success');
                break;
            case 'error':
                classes.push('progress-bar-danger');
                break;
            case 'cancelled':
                classes.push('progress-bar-warning');
                break;
        }
        
        return classes.join(' ');
    }
    
    /**
     * Get status icon based on current status
     */
    get statusIcon() {
        const icons = {
            'idle': 'fa-clock-o',
            'processing': 'fa-spinner fa-spin',
            'completed': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'cancelled': 'fa-times-circle'
        };
        
        return icons[this.state.status] || 'fa-question-circle';
    }
    
    /**
     * Get log entry CSS class
     */
    getLogEntryClass(level) {
        const classes = ['log-entry'];
        
        switch (level) {
            case 'success':
                classes.push('log-success');
                break;
            case 'warning':
                classes.push('log-warning');
                break;
            case 'error':
                classes.push('log-error');
                break;
            default:
                classes.push('log-info');
        }
        
        return classes.join(' ');
    }
    
    /**
     * Get current operation display text
     */
    get operationDisplayText() {
        if (this.state.currentOperation) {
            return this.state.currentOperation;
        }
        
        if (this.state.processedCount > 0 && this.state.totalCount > 0) {
            return `Processing contacts (${this.state.processedCount}/${this.state.totalCount})`;
        }
        
        return this.state.statusMessage;
    }
    
    /**
     * Calculate success rate percentage
     */
    get successRatePercentage() {
        const total = this.state.statistics.contactsAdded + this.state.statistics.errorsEncountered;
        if (total === 0) return 100;
        return Math.round((this.state.statistics.contactsAdded / total) * 100);
    }
    
    /**
     * Check if operation is active
     */
    get isOperationActive() {
        return ['processing'].includes(this.state.status);
    }
    
    /**
     * Check if operation is finished
     */
    get isOperationFinished() {
        return ['completed', 'error', 'cancelled'].includes(this.state.status);
    }
    
    /**
     * Reset progress tracker for new operation
     */
    reset() {
        this.cleanup();
        
        this.state.progress = 0;
        this.state.status = 'idle';
        this.state.statusMessage = 'Waiting to start...';
        this.state.currentOperation = '';
        this.state.processedCount = 0;
        this.state.totalCount = 0;
        this.state.startTime = null;
        this.state.estimatedTimeRemaining = null;
        this.state.elapsedTime = 0;
        this.state.statistics = {
            contactsAdded: 0,
            duplicatesSkipped: 0,
            errorsEncountered: 0,
            successRate: 0
        };
        this.state.isVisible = false;
        this.state.canCancel = true;
        this.state.showDetails = false;
        this.state.logs = [];
    }
    
    /**
     * Cleanup timers and resources
     */
    cleanup() {
        if (this.progressTimer) {
            clearInterval(this.progressTimer);
            this.progressTimer = null;
        }
        
        if (this.elapsedTimer) {
            clearInterval(this.elapsedTimer);
            this.elapsedTimer = null;
        }
        
        // Clean up event listeners
        this.env.bus?.removeEventListener('progress-update', this.onProgressUpdate);
        this.env.bus?.removeEventListener('start-tracking', this.onStartTracking);
    }
}

// OWL 1.0 component registration
ProgressTrackerComponent.template = 'mailing_list_updater.ProgressTrackerTemplate';
ProgressTrackerComponent.props = {
    // batchId: { validate: (value) => value === null || value === undefined || typeof value === 'string' },
    initialProgress: { validate: (value) => value === null || value === undefined || typeof value === 'number' },
    initialStatus: { validate: (value) => value === null || value === undefined || typeof value === 'string' },
};

export { ProgressTrackerComponent };