/** @odoo-module **/

const { Component, useState } = owl;

/**
 * Source Selector Component for OWL 1.0 (FIXED for Odoo 15.0)
 * 
 * Allows users to select which contact sources (models) to include
 * in their mailing list update operation.
 * 
 * FIXED ISSUES:
 * - Moved computed properties to state for template access
 * - Fixed event handlers to work with OWL 1.0
 * - Added console logs for tracking
 * - Corrected method binding patterns
 */
class SourceSelectorComponent extends Component {
    
    setup() {
        console.log('[SourceSelector] Component setup started');
        
        // Services (OWL 1.0 style) 
        this.rpc = this.env.services.rpc;
        console.log('[SourceSelector] RPC service initialized');
        
        // Component state (FIXED: Added filteredSources to state)
        this.state = useState({
            availableSources: [],
            filteredSources: [], // MOVED: From computed property to state
            selectedSources: new Set(),
            isLoading: false,
            searchTerm: '',
            showSourceDetails: {},
        });
        
        console.log('[SourceSelector] State initialized:', {
            availableSources: this.state.availableSources.length,
            selectedSources: this.state.selectedSources.size,
            isLoading: this.state.isLoading
        });
        
        // Props from parent
        this.selectedMailingList = this.props.selectedMailingList;
        console.log('[SourceSelector] Props received:', {
            selectedMailingList: this.selectedMailingList?.name || 'None'
        });
    }
    
    /**
     * OWL 1.0 Lifecycle - Will Start
     * Load available contact sources from the registry
     */
    async willStart() {
        console.log('[SourceSelector] willStart lifecycle started');
        this.state.isLoading = true;
        
        try {
            console.log('[SourceSelector] Making RPC call to load sources');
            
            // TEMPORARY: Try backend route first, fallback to mock data if 404
            let response;
            try {
                response = await this.rpc({
                    route: "/mailing/update/sources",
                    params: {
                        company_id: this.selectedMailingList?.company_id || null
                    }
                });
                console.log('[SourceSelector] RPC response received:', response);
            } catch (rpcError) {
                console.warn('[SourceSelector] Backend route failed, using mock data:', rpcError);
                
                // TEMPORARY: Mock data for testing frontend
                response = {
                    success: true,
                    data: {
                        sources: [
                            {
                                model_name: 'res.partner',
                                name: 'Contacts',
                                description: 'Import contacts from Contacts module',
                                available: true,
                                recommended: true,
                                estimated_count: 1247,
                                email_field: 'email',
                                name_field: 'name',
                                phone_field: 'phone',
                                company_field: 'company_id'
                            },
                            {
                                model_name: 'crm.lead',
                                name: 'CRM Leads',
                                description: 'Import contacts from CRM Leads',
                                available: true,
                                recommended: true,
                                estimated_count: 856,
                                email_field: 'email_from',
                                name_field: 'name',
                                phone_field: 'phone',
                                company_field: 'company_id'
                            },
                            {
                                model_name: 'hr.employee',
                                name: 'Employees',
                                description: 'Import contacts from HR Employees',
                                available: true,
                                recommended: false,
                                estimated_count: 42,
                                email_field: 'work_email',
                                name_field: 'name',
                                phone_field: 'work_phone',
                                company_field: 'company_id'
                            }
                        ]
                    }
                };
                console.log('[SourceSelector] Using mock data:', response);
            }
            
            if (response.success) {
                this.state.availableSources = response.data.sources;
                console.log('[SourceSelector] Available sources loaded:', this.state.availableSources.length);
                
                // FIXED: Update filteredSources in state
                this.updateFilteredSources();
                
                this.preSelectRecommended();
            } else {
                console.error('[SourceSelector] RPC call failed:', response.error);
                this.trigger('show-error', { 
                    message: response.error?.message || "Failed to load sources" 
                });
            }
        } catch (error) {
            console.error('[SourceSelector] Exception during source loading:', error);
            this.trigger('show-error', { 
                message: "Error loading contact sources" 
            });
        } finally {
            this.state.isLoading = false;
            console.log('[SourceSelector] willStart lifecycle completed');
        }
    }
    
    /**
     * FIXED: Update filtered sources in state (was computed property)
     */
    updateFilteredSources() {
        console.log('[SourceSelector] Updating filtered sources with search term:', this.state.searchTerm);
        
        if (!this.state.searchTerm) {
            this.state.filteredSources = [...this.state.availableSources];
        } else {
            const searchLower = this.state.searchTerm.toLowerCase();
            this.state.filteredSources = this.state.availableSources.filter(source => 
                source.name.toLowerCase().includes(searchLower) ||
                source.description?.toLowerCase().includes(searchLower)
            );
        }
        
        console.log('[SourceSelector] Filtered sources updated:', {
            total: this.state.availableSources.length,
            filtered: this.state.filteredSources.length,
            searchTerm: this.state.searchTerm
        });
    }
    
    /**
     * Pre-select recommended sources based on mailing list context
     */
    preSelectRecommended() {
        console.log('[SourceSelector] Pre-selecting recommended sources');
        
        let recommendedCount = 0;
        this.state.availableSources.forEach(source => {
            if (source.recommended) {
                console.log('[SourceSelector] Pre-selecting recommended source:', source.name);
                this.state.selectedSources.add(source.model_name);
                recommendedCount++;
            }
        });
        
        console.log('[SourceSelector] Pre-selected recommended sources:', recommendedCount);
        this.notifyParentOfSelection();
    }
    
    /**
     * FIXED: Handle source selection/deselection with proper event handling
     */
    onSourceToggle(event) {
        // FIXED: Get model name from data attribute instead of parameter
        const modelName = event.currentTarget.dataset.model;
        console.log('[SourceSelector] Source toggle clicked:', modelName);
        
        if (!modelName) {
            console.error('[SourceSelector] No model name found for toggle event');
            return;
        }
        
        const wasSelected = this.state.selectedSources.has(modelName);
        
        if (wasSelected) {
            console.log('[SourceSelector] Deselecting source:', modelName);
            this.state.selectedSources.delete(modelName);
        } else {
            console.log('[SourceSelector] Selecting source:', modelName);
            this.state.selectedSources.add(modelName);
        }
        
        // Force reactivity update for Set
        this.state.selectedSources = new Set(this.state.selectedSources);
        
        console.log('[SourceSelector] Selection updated:', {
            modelName,
            action: wasSelected ? 'deselected' : 'selected',
            totalSelected: this.state.selectedSources.size
        });
        
        this.notifyParentOfSelection();
    }
    
    /**
     * Check if a source is currently selected
     */
    isSourceSelected(modelName) {
        const selected = this.state.selectedSources.has(modelName);
        console.log('[SourceSelector] Checking if source selected:', modelName, selected);
        return selected;
    }
    
    /**
     * FIXED: Toggle source details visibility with proper event handling
     */
    toggleSourceDetails(event) {
        // FIXED: Get model name from data attribute
        const modelName = event.currentTarget.dataset.model;
        console.log('[SourceSelector] Toggle details for source:', modelName);
        
        if (!modelName) {
            console.error('[SourceSelector] No model name found for details toggle');
            return;
        }
        
        const wasShowing = this.state.showSourceDetails[modelName];
        this.state.showSourceDetails[modelName] = !wasShowing;
        
        console.log('[SourceSelector] Details toggled:', {
            modelName,
            wasShowing,
            nowShowing: this.state.showSourceDetails[modelName]
        });
        
        // Prevent event bubbling to parent source toggle
        event.stopPropagation();
    }
    
    /**
     * FIXED: Handle search input with proper state management
     */
    onSearchInput(event) {
        const newSearchTerm = event.target.value;
        console.log('[SourceSelector] Search input changed:', {
            oldTerm: this.state.searchTerm,
            newTerm: newSearchTerm
        });
        
        this.state.searchTerm = newSearchTerm;
        
        // FIXED: Update filtered sources when search changes
        this.updateFilteredSources();
    }
    
    /**
     * Get selected sources data for parent component
     */
    getSelectedSourcesData() {
        const selectedData = this.state.availableSources.filter(source => 
            this.state.selectedSources.has(source.model_name)
        );
        
        console.log('[SourceSelector] Getting selected sources data:', {
            selectedCount: selectedData.length,
            selectedNames: selectedData.map(s => s.name)
        });
        
        return selectedData;
    }
    
    /**
     * Notify parent component of selection changes
     */
    notifyParentOfSelection() {
        const selectedData = this.getSelectedSourcesData();
        
        console.log('[SourceSelector] Notifying parent of selection change:', {
            selectedSources: Array.from(this.state.selectedSources),
            selectedCount: selectedData.length,
            isValid: selectedData.length > 0
        });
        
        this.trigger('sources-changed', {
            selectedSources: Array.from(this.state.selectedSources),
            selectedSourcesData: selectedData,
            isValid: selectedData.length > 0
        });
    }
    
    /**
     * FIXED: Get CSS classes for source item (now accessible from template)
     */
    getSourceItemClass(source) {
        let classes = ['source-item'];
        
        if (this.isSourceSelected(source.model_name)) {
            classes.push('selected');
        }
        
        if (!source.available) {
            classes.push('unavailable');
        }
        
        if (source.recommended) {
            classes.push('recommended');
        }
        
        const classString = classes.join(' ');
        console.log('[SourceSelector] Generated CSS classes for', source.name, ':', classString);
        
        return classString;
    }
    
    /**
     * Handle select all recommended sources
     */
    selectAllRecommended() {
        console.log('[SourceSelector] Selecting all recommended sources');
        
        let addedCount = 0;
        this.state.availableSources.forEach(source => {
            if (source.recommended && source.available) {
                if (!this.state.selectedSources.has(source.model_name)) {
                    console.log('[SourceSelector] Adding recommended source:', source.name);
                    this.state.selectedSources.add(source.model_name);
                    addedCount++;
                }
            }
        });
        
        this.state.selectedSources = new Set(this.state.selectedSources);
        
        console.log('[SourceSelector] Selected all recommended sources:', {
            addedCount,
            totalSelected: this.state.selectedSources.size
        });
        
        this.notifyParentOfSelection();
    }
    
    /**
     * Handle clear all selections
     */
    clearAllSelections() {
        console.log('[SourceSelector] Clearing all selections');
        
        const previousCount = this.state.selectedSources.size;
        this.state.selectedSources.clear();
        this.state.selectedSources = new Set();
        
        console.log('[SourceSelector] All selections cleared:', {
            previousCount,
            currentCount: this.state.selectedSources.size
        });
        
        this.notifyParentOfSelection();
    }
    
    /**
     * Format contact count for display
     */
    formatContactCount(count) {
        let formatted;
        if (count >= 1000000) {
            formatted = `${(count / 1000000).toFixed(1)}M`;
        } else if (count >= 1000) {
            formatted = `${(count / 1000).toFixed(1)}K`;
        } else {
            formatted = count.toString();
        }
        
        console.log('[SourceSelector] Formatted contact count:', count, '→', formatted);
        return formatted;
    }
}

// OWL 1.0 component registration
SourceSelectorComponent.template = 'mailing_list_updater.SourceSelectorTemplate';
SourceSelectorComponent.props = {
    selectedMailingList: { validate: (value) => value === null || typeof value === 'object' },
};

console.log('[SourceSelector] Component class definition completed');

export { SourceSelectorComponent };