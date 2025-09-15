/** @odoo-module **/

import { SourceSelectorComponent } from './source_selector_component.js';
import { TargetSelectorComponent } from './target_selector_component.js';
import { FilterBuilderComponent } from './filter_builder_component.js';
import { PreviewResultsComponent } from './preview_results_component.js';
import { ExecutionComponent } from './progress_tracker_component.js';

const { Component, useState } = owl;

/**
 * Main Mailing List Updater Component - OWL 1.0 (Fixed for Odoo 15.0)
 * 
 * This is the core component that orchestrates the entire mailing list update process.
 * It manages the overall state and coordinates child components.
 * Enhanced with context handling for different entry points.
 */
class MailingListUpdaterMain extends Component {
    
    setup() {
        // Services (OWL 1.0 style)
        this.rpc = this.env.services.rpc;
        this.notification = this.env.services.notification;
        this.orm = this.env.services.orm;
        this.action = this.env.services.action;
        
        // Component State
        this.state = useState({
            // Current step in the update process
            currentStep: 'target_selection', // Will be set from context
            
            // Loading states
            isLoading: false,
            isExecuting: false,
            
            // Data
            selectedMailingList: null,
            selectedSources: [],
            operationType: null,
            selectedSourceMailingList: null,
            filterCriteria: {},
            previewData: null,
            currentBatch: null,
            lastCompletedBatch: null,
            
            // UI State
            showAdvancedFilters: false,
            errors: [],
            
            // Progress tracking
            executionProgress: 0,
            executionStatus: 'idle', // idle, ready, processing, completed, error
            
            // Context information
            entryPoint: 'main_menu', // main_menu, smart_button, batch_history
            preSelectedMailingListId: null,
            showBreadcrumb: true
        });
        
        // WebSocket connection for real-time updates
        this.websocket = null;
        
        // Component references
        this.progressTrackerRef = null;
        
        // Store available data for child components
        this.mailingLists = [];
        this.availableSources = [];
    }
    
    /**
     * OWL 1.0 Lifecycle - Will Start
     * Initialize component data before rendering
     */
    async willStart() {
        try {
            this.state.isLoading = true;
            
            // Handle context parameters first
            this.handleContextParameters();
            
            // Load initial data
            // await this.loadMailingLists();
            
            // Apply context-based initialization
            await this.applyContextInitialization();
            
        } catch (error) {
            // this.showError("Failed to initialize mailing list updater");
            console.error("Initialization error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * OWL 1.0 Lifecycle - Mounted
     * Setup after component is mounted to DOM
     */
    mounted() {
        // Setup keyboard shortcuts, focus management, etc.
        this.setupKeyboardShortcuts();
        
        // Set page title based on entry point
        this.updatePageTitle();
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
     * Enhanced context parameter handling
     */
    handleContextParameters() {
        try {
            // Get context from various possible sources (enhanced for Odoo client actions)
            const context = this.env.services?.action?.currentController?.actionDefinition?.context || 
                           this.props?.context || 
                           this.env?.context ||
                           this.props?.action?.context ||
                           {};
            
            console.log('Mailing List Updater Context:', context);
            
            // Handle initial step from context
            if (context.initial_step) {
                this.state.currentStep = context.initial_step;
                console.log('Setting initial step to:', context.initial_step);
            }
            
            // Handle pre-selected mailing list
            if (context.default_mailing_list_id) {
                this.state.preSelectedMailingListId = context.default_mailing_list_id;
                console.log('Pre-selected mailing list ID:', context.default_mailing_list_id);
            }
            
            // Handle entry point identification
            if (context.from_mailing_list) {
                this.state.entryPoint = 'smart_button';
            } else if (context.initial_step === 'batch_management') {
                this.state.entryPoint = 'batch_history';
            } else {
                this.state.entryPoint = 'main_menu';
            }
            
            // Handle breadcrumb visibility
            if (context.show_breadcrumb !== undefined) {
                this.state.showBreadcrumb = context.show_breadcrumb;
            }
            
            console.log('Entry point detected:', this.state.entryPoint);
            
        } catch (error) {
            console.warn('Context handling error:', error);
            // Continue without context - not critical
        }
    }
    
    /**
     * Apply context-based initialization after data loading
     */
    async applyContextInitialization() {
        // Pre-select mailing list if provided in context
        if (this.state.preSelectedMailingListId && this.mailingLists) {
            const preSelectedList = this.mailingLists.find(
                list => list.id === this.state.preSelectedMailingListId
            );
            
            if (preSelectedList) {
                this.state.selectedMailingList = preSelectedList;
                console.log('Pre-selected mailing list:', preSelectedList.name);
                
                // If coming from smart button, auto-select recommended sources
                if (this.state.entryPoint === 'smart_button') {
                    await this.autoSelectRecommendedSources();
                }
            }
        }
        
        // Handle specific entry point logic
        switch (this.state.entryPoint) {
            case 'smart_button':
                // Coming from mailing list form, make the flow more direct
                this.showSuccess(`Ready to update "${this.state.selectedMailingList?.name}" mailing list`);
                break;
                
            case 'batch_history':
                // Coming from batch history menu, show recent batches
                await this.loadRecentBatchInfo();
                break;
                
            case 'main_menu':
            default:
                // Standard entry, no special handling needed
                break;
        }
    }

    onSourceMailingListChanged(event) {
        this.state.selectedSourceMailingList = event.detail.selectedSourceMailingList;
    }


    /**
     * Handle operation type changes from SourceSelector
     */
    onOperationTypeChanged(event) {
        this.state.operationType = event.detail.operationType;
        
        // Reset relevant selections when switching operation types
        if (event.detail.operationType === 'update') {
            // Clear merge-related selections
            this.state.selectedSourceMailingList = null;
        } else if (event.detail.operationType === 'merge') {
            // Clear update-related selections
            this.state.selectedSources = [];
            this.state.filterCriteria = {};
            this.state.previewData = null;
        }
    }
    
    /**
     * Auto-select recommended sources for smart button entry
     */
    async autoSelectRecommendedSources() {
        if (this.availableSources && this.availableSources.length > 0) {
            // Select contacts and CRM by default
            const recommendedSources = this.availableSources.filter(source => 
                ['res.partner', 'crm.lead'].includes(source.model_name) && source.available
            );
            
            if (recommendedSources.length > 0) {
                this.state.selectedSources = recommendedSources;
                console.log('Auto-selected recommended sources:', recommendedSources.map(s => s.name));
            }
        }
    }
    
    /**
     * Load recent batch information for batch history entry point
     */
    async loadRecentBatchInfo() {
        try {
            const response = await this.rpc({
                route: "/mailing/batch/recent",
                params: { limit: 5 }
            });
            
            if (response.success && response.data.batches.length > 0) {
                this.state.lastCompletedBatch = response.data.batches[0].id;
            }
        } catch (error) {
            console.warn('Failed to load recent batch info:', error);
        }
    }
    
    /**
     * Update page title based on context
     */
    updatePageTitle() {
        const titles = {
            'smart_button': `Update "${this.state.selectedMailingList?.name}" - Mailing List Updater`,
            'batch_history': 'Batch History - Mailing List Updater',
            'main_menu': 'Mailing List Updater'
        };
        
        const title = titles[this.state.entryPoint] || titles['main_menu'];
        
        // Update browser title if possible
        if (document.title) {
            document.title = title;
        }
    }
    
    /**
     * Load available mailing lists for selection
     */
    // async loadMailingLists() {
    //     try {
    //         const result = await this.rpc({
    //             model: "mailing.list",
    //             method: "search_read",
    //             args: [[["active", "=", true]]],
    //             kwargs: {
    //                 fields: ["id", "name", "contact_count", "company_id"],
    //                 order: "name"
    //             }
    //         });
            
    //         this.mailingLists = result;
            
    //     } catch (error) {
    //         this.showError("Failed to load mailing lists");
    //         throw error;
    //     }
    // }
    
    /**
     * Load available contact sources from registry
     */
   
    
    /**
     * Handle mailing list selection
     */
    async onMailingListSelected(mailingListId) {
        const selectedList = this.mailingLists.find(list => list.id === mailingListId);
        this.state.selectedMailingList = selectedList;
        selectedList.contacts = [];

        await this.loadMailingListContacts(mailingListId);  // ⏳ Wait for contacts
        console.log('contacts', selectedList.contacts);      // ✅ Now it's filled

        // Clear other state
        this.state.selectedSources = [];
        this.state.filterCriteria = {};
        this.state.previewData = null;

        this.updatePageTitle();
    }


    async loadMailingListContacts(mailingListId, offset = 0, limit = 20) {
        try {
            const contacts = await this.rpc({
                model: "mailing.contact",
                method: "search_read", 
                args: [[["list_ids", "in", [mailingListId]]]],
                kwargs: { 
                    fields: ["name", "email"],
                    offset: offset,
                    limit: limit,
                    order: "name"
                }
            });
            
            // Add contacts directly to selectedMailingList
            if (offset === 0) {
                this.state.selectedMailingList.contacts = contacts;
            } else {
                this.state.selectedMailingList.contacts.push(...contacts);
            }
        } catch (error) {
            console.error("Failed to load contacts:", error);
        }
    }
    

    // Add new method
    onTargetSelected(event) {
        this.state.selectedMailingList = event.detail.targetMailingList;
        
        // Don't auto-navigate - let user click Next
        // this.state.currentStep = 'source_selection'; // Remove this
    }
    
    /**
     * Handle source selection changes from SourceSelector
     */
    onSourcesChanged(event) {
        const newSources = event.detail.selectedSourcesData || [];

        // Only reset filters if selected sources truly changed
        const currentModels = this.state.selectedSources.map(s => s.model_name).sort().join(',');
        const newModels = newSources.map(s => s.model_name).sort().join(',');

        if (currentModels !== newModels) {
            this.state.selectedSources = newSources;
            this.state.filterCriteria = {};  // Reset only if sources changed
            this.state.previewData = null;
        }

        // Move to filter step if needed
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
     * Navigate between steps
     */
    goToStep(stepName) {
        const validSteps = ['target_selection', 'source_selection', 'filter_building', 'preview', 'execution', 'batch_management'];
        
        if (validSteps.includes(stepName)) {
            this.state.currentStep = stepName;
        }
    }
    
    /**
     * Move to next step in the process
     */
    nextStep() {
        const stepOrder = ['target_selection', 'source_selection', 'filter_building', 'preview', 'execution', 'batch_management'];
        const currentIndex = stepOrder.indexOf(this.state.currentStep);
        
        if (currentIndex < stepOrder.length - 1) {
            this.state.currentStep = stepOrder[currentIndex + 1];
        }
    }
    
    /**
     * Move to previous step
     */
    previousStep() {
        const stepOrder = ['target_selection', 'source_selection', 'filter_building', 'preview', 'execution', 'batch_management'];
        const currentIndex = stepOrder.indexOf(this.state.currentStep);
        
        if (currentIndex > 0) {
            this.state.currentStep = stepOrder[currentIndex - 1];
        }
    }

    closeUpdater() {
        // Just go back in browser history
        window.history.back();
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
            case 'target_selection':
                return this.state.selectedMailingList !== null;
            case 'source_selection':
                return this.state.selectedSources.length > 0;
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
     * Get step display information for breadcrumbs
     */
    getStepInfo(stepName) {
        const stepInfo = {
            'target_selection': { title: 'Select Target', icon: 'fa-envelope' },
            'source_selection': { title: 'Select Sources', icon: 'fa-database' },
            'filter_building': { title: 'Build Filters', icon: 'fa-filter' },
            'preview': { title: 'Preview Results', icon: 'fa-eye' },
            'execution': { title: 'Execute', icon: 'fa-play' },
            'batch_management': { title: 'Batch History', icon: 'fa-history' }
        };
        
        return stepInfo[stepName] || { title: stepName, icon: 'fa-question' };
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
MailingListUpdaterMain.template = "mailing_list_updater_t.MainTemplate";

// Register child components for OWL 1.0
MailingListUpdaterMain.components = {
    TargetSelectorComponent,
    SourceSelectorComponent,
    FilterBuilderComponent,
    PreviewResultsComponent,
    ExecutionComponent,
};

export { MailingListUpdaterMain };