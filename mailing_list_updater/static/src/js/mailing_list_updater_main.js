/** @odoo-module **/

const { Component, useState, onWillStart, onMounted } = owl;

/**
 * Main Mailing List Updater Component - OWL 1.0
 * 
 * This is the core component that orchestrates the entire mailing list update process.
 * It manages the overall state and coordinates child components.
 */
class MailingListUpdaterMain extends Component {
    
    setup() {
        // Services (OWL 1.0 style)
        this.rpc = this.env.services.rpc;
        this.notification = this.env.services.notification;
        this.orm = this.env.services.orm;
        
        // Component State
        this.state = useState({
            // Current step in the update process
            currentStep: 'source_selection', // source_selection, filter_building, preview, execution, batch_management
            
            // Loading states
            isLoading: false,
            isExecuting: false,
            
            // Data
            selectedMailingList: null,
            selectedSources: [],
            filterCriteria: {},
            previewData: null,
            currentBatch: null,
            lastCompletedBatch: null,
            
            // UI State
            showAdvancedFilters: false,
            errors: [],
            
            // Progress tracking
            executionProgress: 0,
            executionStatus: 'idle' // idle, ready, processing, completed, error
        });
        
        // WebSocket connection for real-time updates
        this.websocket = null;
        
        // Component references
        this.progressTrackerRef = null;
        
        // Lifecycle hooks
        onWillStart(this.onWillStart);
        onMounted(this.onMounted);
    }
    
    /**
     * Get currently selected sources for child components
     */
    get currentSelectedSources() {
        return this.state.selectedSources || [];
    }
    
    /**
     * Get current filter criteria for child components
     */
    get currentFilterCriteria() {
        return this.state.filterCriteria || {};
    }
    
    /**
     * Get current selected mailing list for child components
     */
    get currentSelectedMailingList() {
        return this.state.selectedMailingList;
    }
    
    /**
     * Get current batch ID for progress tracking
     */
    get currentBatchId() {
        return this.state.currentBatch?.batch_id || null;
    }
    
    /**
     * Get current execution status for progress tracking
     */
    get currentExecutionStatus() {
        return this.state.executionStatus;
    }
    
    /**
     * Open batch management view
     */
    openBatchManager() {
        this.state.currentStep = 'batch_management';
    }
    
    /**
     * View last completed batch in batch manager
     */
    viewLastCompletedBatch() {
        if (this.state.lastCompletedBatch) {
            this.state.currentStep = 'batch_management';
            
            // Emit event to batch manager to view specific batch
            this.trigger('view-batch', { 
                batchId: this.state.lastCompletedBatch 
            });
        }
    }
    
    /**
     * Handle batch manager events
     */
    onBatchManagerEvent(event) {
        // Handle various batch manager events
        switch (event.detail.type) {
            case 'batch_rolled_back':
                this.showSuccess(`Batch ${event.detail.batchId} rolled back successfully`);
                break;
            case 'rollback_failed':
                this.showError(`Rollback failed: ${event.detail.error}`);
                break;
        }
    }
    
    /**
     * Get current execution progress for progress tracking
     */
    get currentExecutionProgress() {
        return this.state.executionProgress;
    }
    
    /**
     * Get current mailing list ID for batch manager
     */
    get currentMailingListId() {
        return this.state.selectedMailingList?.id || null;
    }
    
    /**
     * Check if there are any recent batch operations
     */
    get hasRecentBatches() {
        return this.state.lastCompletedBatch !== null;
    }
    
    /**
     * Handle source selection changes from SourceSelector
     */
    onSourcesChanged(event) {
        this.state.selectedSources = event.detail.selectedSourcesData;
        
        // Reset filters when sources change
        this.state.filterCriteria = {};
        this.state.previewData = null;
        
        // If we're past source selection step, stay there until filters are rebuilt
        if (this.state.currentStep !== 'source_selection') {
            this.state.currentStep = 'filter_building';
        }
    }
    
    /**
     * Handle filter changes from FilterBuilder
     */
    onFiltersChanged(event) {
        this.state.filterCriteria = event.detail.filters;
        
        // Reset preview when filters change
        this.state.previewData = null;
        
        // Validate step completion
        if (event.detail.isValid && this.state.currentStep === 'filter_building') {
            // Filters are valid, can proceed to preview
        } else if (!event.detail.isValid) {
            // Show validation errors
            this.state.errors = event.detail.errors || [];
        }
    }
    
    /**
     * Handle preview ready from PreviewResults
     */
    onPreviewReady(event) {
        this.state.previewData = event.detail.previewData;
        
        // Update execution readiness
        if (event.detail.canExecute) {
            this.state.executionStatus = 'ready';
        }
        
        // Clear any previous errors
        this.state.errors = [];
    }
    
    /**
     * Handle execution request from PreviewResults
     */
    async onExecuteUpdate(event) {
        if (this.state.isExecuting) {
            return; // Prevent double execution
        }
        
        this.state.isExecuting = true;
        this.state.executionStatus = 'processing';
        this.state.executionProgress = 0;
        
        try {
            const requestData = {
                mailing_list_id: this.state.selectedMailingList.id,
                source_models: this.state.selectedSources.map(source => ({
                    model_name: source.model_name,
                    enabled: true
                })),
                quick_filters: this.state.filterCriteria.quick_filters || {},
                advanced_filters: this.state.filterCriteria.advanced_filters || {},
                confirmed: true,
                options: {
                    send_notification: true,
                    batch_size: 1000
                }
            };
            
            const response = await this.rpc({
                route: "/mailing/update/execute",
                params: requestData
            });
            
            if (response.success) {
                this.state.currentBatch = response.data;
                this.state.currentStep = 'execution';
                
                // Start progress tracking
                this.startProgressTracking(response.data.batch_id);
                
                // Start WebSocket connection for progress tracking
                this.setupWebSocketConnection(response.data.batch_id);
                
                this.showSuccess("Mailing list update started successfully!");
                
            } else {
                throw new Error(response.error?.message || "Execution failed");
            }
            
        } catch (error) {
            this.state.executionStatus = 'error';
            this.showError(`Execution failed: ${error.message}`);
            console.error("Execution error:", error);
        } finally {
            this.state.isExecuting = false;
        }
    }
    
    /**
     * Start progress tracking for a batch operation
     */
    startProgressTracking(batchId) {
        // Use reference if available, or emit event for component to catch
        if (this.progressTrackerRef) {
            this.progressTrackerRef.setBatchId(batchId);
            this.progressTrackerRef.startTracking();
        } else {
            // Fallback: emit event that progress tracker can listen to
            this.trigger('start-tracking', { batchId: batchId });
        }
    }
    
    /**
     * Setup WebSocket connection for progress tracking
     */
    setupWebSocketConnection(batchId) {
        if (this.websocket) {
            this.websocket.close();
        }
        
        try {
            const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/mailing/progress/${batchId}`;
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log("WebSocket connected for batch:", batchId);
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onerror = (error) => {
                console.error("WebSocket error:", error);
                // Fallback to HTTP polling
                this.startHttpPolling(batchId);
            };
            
            this.websocket.onclose = () => {
                console.log("WebSocket connection closed");
            };
            
        } catch (error) {
            console.error("WebSocket setup failed:", error);
            // Fallback to HTTP polling
            this.startHttpPolling(batchId);
        }
    }
    
    /**
     * Handle WebSocket messages for progress updates
     */
    handleWebSocketMessage(data) {
        // Update local state
        switch (data.type) {
            case 'progress':
                this.state.executionProgress = data.progress || 0;
                break;
                
            case 'status':
                this.state.executionStatus = data.status;
                if (data.status === 'completed') {
                    this.state.executionProgress = 100;
                    this.showSuccess("Mailing list update completed successfully!");
                }
                break;
                
            case 'error':
                this.state.executionStatus = 'error';
                this.showError(`Update failed: ${data.message}`);
                break;
        }
        
        // Pass data to progress tracker component
        this.updateProgressTracker(data);
    }
    
    /**
     * Update progress tracker component with new data
     */
    updateProgressTracker(progressData) {
        // Use reference if available, or emit event for component to catch
        if (this.progressTrackerRef) {
            this.progressTrackerRef.updateProgress(progressData);
        } else {
            // Fallback: emit event that progress tracker can listen to
            this.trigger('progress-update', progressData);
        }
    }
    
    /**
     * Find child component by name - OWL 1.0 compatible
     */
    findChildComponent(componentName) {
        // In OWL 1.0, use a reference approach instead
        // This is a simplified version - in practice, you'd use refs or direct component communication
        if (componentName === 'ProgressTrackerComponent') {
            return this.progressTrackerRef;
        }
        return null;
    }
    
    /**
     * Set progress tracker reference (called from template)
     */
    setProgressTrackerRef(component) {
        this.progressTrackerRef = component;
    }
    
    /**
     * Handle progress tracker component ready event
     */
    onProgressTrackerReady(event) {
        this.progressTrackerRef = event.detail.component;
    }
    
    /**
     * Handle progress tracker events
     */
    onOperationCompleted(event) {
        this.state.executionStatus = 'completed';
        this.state.executionProgress = 100;
        this.state.isExecuting = false;
        
        // Close WebSocket connection
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        const contactsAdded = event.detail.statistics.contactsAdded || 0;
        this.showSuccess(
            `Operation completed! ${contactsAdded} contacts added. ` +
            `View batch history for more details.`
        );
        
        // Store completed batch info for potential navigation
        this.state.lastCompletedBatch = event.detail.batchId;
    }
    
    /**
     * Handle progress tracker errors
     */
    onOperationError(event) {
        this.state.executionStatus = 'error';
        this.state.isExecuting = false;
        
        // Close WebSocket connection
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        this.showError(`Operation failed: ${event.detail.error}`);
    }
    
    /**
     * Handle progress tracker cancellation
     */
    onOperationCancelled(event) {
        this.state.executionStatus = 'cancelled';
        this.state.isExecuting = false;
        
        // Close WebSocket connection
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        this.showSuccess("Operation cancelled successfully");
        
        // Return to preview step
        this.state.currentStep = 'preview';
    }
    
    /**
     * Fallback HTTP polling for progress updates
     */
    startHttpPolling(batchId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await this.rpc({
                    route: `/mailing/update/progress/${batchId}`
                });
                
                if (response.success) {
                    const data = response.data;
                    
                    // Update local state
                    this.state.executionProgress = data.progress || 0;
                    this.state.executionStatus = data.status;
                    
                    // Update progress tracker
                    this.updateProgressTracker({
                        type: 'progress',
                        progress: data.progress,
                        status: data.status,
                        message: data.message,
                        current_operation: data.current_operation,
                        processed_count: data.processed_count,
                        total_count: data.total_count,
                        statistics: data.statistics
                    });
                    
                    if (data.status === 'completed' || data.status === 'error') {
                        clearInterval(pollInterval);
                        
                        if (data.status === 'completed') {
                            this.showSuccess("Mailing list update completed successfully!");
                            this.state.executionStatus = 'completed';
                        } else {
                            this.showError("Mailing list update failed");
                            this.state.executionStatus = 'error';
                        }
                        
                        this.state.isExecuting = false;
                    }
                }
                
            } catch (error) {
                console.error("Progress polling error:", error);
                clearInterval(pollInterval);
                this.state.executionStatus = 'error';
                this.state.isExecuting = false;
            }
        }, 2000); // Poll every 2 seconds
        
        // Clear polling after 10 minutes (failsafe)
        setTimeout(() => {
            clearInterval(pollInterval);
        }, 600000);
    }
    
    /**
     * Initialize component data before rendering
     */
    async onWillStart() {
        try {
            this.state.isLoading = true;
            
            // Load initial data
            await this.loadMailingLists();
            await this.loadAvailableSources();
            
            // Check for pre-selected mailing list from context
            this.handleContextParameters();
            
        } catch (error) {
            this.showError("Failed to initialize mailing list updater");
            console.error("Initialization error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * Handle context parameters (e.g., from smart button)
     */
    handleContextParameters() {
        try {
            // Get context from various possible sources
            const context = this.env.services?.action?.currentController?.actionDefinition?.context || 
                           this.props?.context || 
                           this.env?.context || 
                           {};
            
            console.log('Mailing List Updater Context:', context);
            
            // Pre-select mailing list if provided in context
            if (context.default_mailing_list_id && this.mailingLists) {
                const preSelectedList = this.mailingLists.find(
                    list => list.id === context.default_mailing_list_id
                );
                
                if (preSelectedList) {
                    this.state.selectedMailingList = preSelectedList;
                    console.log('Pre-selected mailing list:', preSelectedList.name);
                }
            }
        } catch (error) {
            console.warn('Context handling error:', error);
            // Continue without context - not critical
        }
    }
    
    /**
     * Setup after component is mounted to DOM
     */
    onMounted() {
        // Setup keyboard shortcuts, focus management, etc.
        this.setupKeyboardShortcuts();
    }
    
    /**
     * Load available mailing lists for selection
     */
    async loadMailingLists() {
        try {
            const result = await this.rpc({
                model: "mailing.list",
                method: "search_read",
                args: [[["active", "=", true]]],
                kwargs: {
                    fields: ["id", "name", "contact_count"],
                    order: "name"
                }
            });
            
            this.mailingLists = result;
            
        } catch (error) {
            this.showError("Failed to load mailing lists");
            throw error;
        }
    }
    
    /**
     * Load available contact sources from registry
     */
    async loadAvailableSources() {
        try {
            const response = await this.rpc({
                route: "/mailing/update/sources"
            });
            
            if (response.success) {
                this.availableSources = response.data.sources;
            } else {
                throw new Error(response.error?.message || "Unknown error");
            }
            
        } catch (error) {
            this.showError("Failed to load contact sources");
            throw error;
        }
    }
    
    /**
     * Handle mailing list selection
     */
    onMailingListSelected(mailingListId) {
        const selectedList = this.mailingLists.find(list => list.id === mailingListId);
        this.state.selectedMailingList = selectedList;
        
        // Reset downstream selections when mailing list changes
        this.state.selectedSources = [];
        this.state.filterCriteria = {};
        this.state.previewData = null;
    }
    
    /**
     * Handle source selection changes from SourceSelector
     */
    onSourcesChanged(event) {
        this.state.selectedSources = event.detail.selectedSourcesData;
        
        // Reset filters when sources change
        this.state.filterCriteria = {};
        this.state.previewData = null;
        
        // If we're past source selection step, stay there until filters are rebuilt
        if (this.state.currentStep !== 'source_selection') {
            this.state.currentStep = 'filter_building';
        }
    }
    
    /**
     * Handle filter changes from FilterBuilder
     */
    onFiltersChanged(event) {
        this.state.filterCriteria = event.detail.filters;
        
        // Reset preview when filters change
        this.state.previewData = null;
        
        // Validate step completion
        if (event.detail.isValid && this.state.currentStep === 'filter_building') {
            // Filters are valid, can proceed to preview
        } else if (!event.detail.isValid) {
            // Show validation errors
            this.state.errors = event.detail.errors || [];
        }
    }
    
    /**
     * Get currently selected sources for child components
     */
    get currentSelectedSources() {
        return this.state.selectedSources || [];
    }
    
    /**
     * Navigate between steps
     */
    goToStep(stepName) {
        const validSteps = ['source_selection', 'filter_building', 'preview', 'execution', 'batch_management'];
        
        if (validSteps.includes(stepName)) {
            this.state.currentStep = stepName;
        }
    }
    
    /**
     * Move to next step in the process
     */
    nextStep() {
        const stepOrder = ['source_selection', 'filter_building', 'preview', 'execution', 'batch_management'];
        const currentIndex = stepOrder.indexOf(this.state.currentStep);
        
        if (currentIndex < stepOrder.length - 1) {
            this.state.currentStep = stepOrder[currentIndex + 1];
        }
    }
    
    /**
     * Move to previous step
     */
    previousStep() {
        const stepOrder = ['source_selection', 'filter_building', 'preview', 'execution', 'batch_management'];
        const currentIndex = stepOrder.indexOf(this.state.currentStep);
        
        if (currentIndex > 0) {
            this.state.currentStep = stepOrder[currentIndex - 1];
        }
    }
    
    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        // Add keyboard navigation, escape handlers, etc.
        document.addEventListener('keydown', this.onKeyDown.bind(this));
    }
    
    /**
     * Handle keyboard events
     */
    onKeyDown(event) {
        // Handle escape to close dialogs
        if (event.key === 'Escape') {
            this.closeDialogs();
        }
        
        // Handle Ctrl+B to open batch manager
        if (event.ctrlKey && event.key === 'b') {
            event.preventDefault();
            this.openBatchManager();
        }
        
        // Handle Ctrl+H to go to batch history
        if (event.ctrlKey && event.key === 'h') {
            event.preventDefault();
            this.state.currentStep = 'batch_management';
        }
    }
    
    /**
     * Close any open dialogs or reset to initial state
     */
    closeDialogs() {
        this.state.showAdvancedFilters = false;
        this.state.errors = [];
    }
    
    /**
     * Display error message to user
     */
    showError(message) {
        this.state.errors.push(message);
        this.notification.add(message, { type: 'danger' });
    }
    
    /**
     * Display success message to user
     */
    showSuccess(message) {
        this.notification.add(message, { type: 'success' });
    }
    
    /**
     * Check if current step is valid/complete
     */
    isStepComplete(stepName) {
        switch (stepName) {
            case 'source_selection':
                return this.state.selectedMailingList && this.state.selectedSources.length > 0;
            case 'filter_building':
                return Object.keys(this.state.filterCriteria).length > 0 && this.state.errors.length === 0;
            case 'preview':
                return this.state.previewData !== null && this.state.executionStatus === 'ready';
            case 'execution':
                return this.state.executionStatus === 'completed';
            case 'batch_management':
                return true; // Always accessible for management
            default:
                return false;
        }
    }
    
    /**
     * Component cleanup
     */
    willUnmount() {
        // Cleanup WebSocket connection
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        // Cleanup progress tracker
        if (this.progressTrackerRef) {
            this.progressTrackerRef.cleanup();
        }
        
        // Remove event listeners
        document.removeEventListener('keydown', this.onKeyDown);
    }
}

// OWL 1.0 component registration
MailingListUpdaterMain.template = "mailing_list_updater.MainTemplate";
MailingListUpdaterMain.components = {
    SourceSelectorComponent: () => import('./source_selector_component.js').then(m => m.SourceSelectorComponent),
    FilterBuilderComponent: () => import('./filter_builder_component.js').then(m => m.FilterBuilderComponent),
    PreviewResultsComponent: () => import('./preview_results_component.js').then(m => m.PreviewResultsComponent),
    ProgressTrackerComponent: () => import('./progress_tracker_component.js').then(m => m.ProgressTrackerComponent),
    BatchManagerComponent: () => import('./batch_manager_component.js').then(m => m.BatchManagerComponent),
};

export { MailingListUpdaterMain };