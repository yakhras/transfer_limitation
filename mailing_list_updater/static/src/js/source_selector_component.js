/** @odoo-module **/

const { Component, useState, onWillStart } = owl;

/**
 * Source Selector Component for OWL 1.0
 * 
 * Allows users to select which contact sources (models) to include
 * in their mailing list update operation.
 */
class SourceSelectorComponent extends Component {
    
    setup() {
        // Services (OWL 1.0 style) 
        this.rpc = this.env.services.rpc;
        
        // Component state
        this.state = useState({
            availableSources: [],
            selectedSources: new Set(),
            isLoading: false,
            searchTerm: '',
            showSourceDetails: {},
        });
        
        // Props from parent
        this.selectedMailingList = this.props.selectedMailingList;
        
        // Load sources on component start
        onWillStart(this.loadSources);
    }
    
    /**
     * Load available contact sources from the registry
     */
    async loadSources() {
        this.state.isLoading = true;
        
        try {
            const response = await this.rpc({
                route: "/mailing/update/sources",
                params: {
                    company_id: this.selectedMailingList?.company_id || null
                }
            });
            
            if (response.success) {
                this.state.availableSources = response.data.sources;
                this.preSelectRecommended();
            } else {
                this.trigger('show-error', { 
                    message: response.error?.message || "Failed to load sources" 
                });
            }
        } catch (error) {
            this.trigger('show-error', { 
                message: "Error loading contact sources" 
            });
            console.error("Source loading error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * Pre-select recommended sources based on mailing list context
     */
    preSelectRecommended() {
        this.state.availableSources.forEach(source => {
            if (source.recommended) {
                this.state.selectedSources.add(source.model_name);
            }
        });
        
        this.notifyParentOfSelection();
    }
    
    /**
     * Handle source selection/deselection
     */
    onSourceToggle(modelName) {
        if (this.state.selectedSources.has(modelName)) {
            this.state.selectedSources.delete(modelName);
        } else {
            this.state.selectedSources.add(modelName);
        }
        
        // Force reactivity update for Set
        this.state.selectedSources = new Set(this.state.selectedSources);
        
        this.notifyParentOfSelection();
    }
    
    /**
     * Check if a source is currently selected
     */
    isSourceSelected(modelName) {
        return this.state.selectedSources.has(modelName);
    }
    
    /**
     * Toggle source details visibility
     */
    toggleSourceDetails(modelName) {
        this.state.showSourceDetails[modelName] = !this.state.showSourceDetails[modelName];
    }
    
    /**
     * Filter sources based on search term
     */
    get filteredSources() {
        if (!this.state.searchTerm) {
            return this.state.availableSources;
        }
        
        const searchLower = this.state.searchTerm.toLowerCase();
        return this.state.availableSources.filter(source => 
            source.name.toLowerCase().includes(searchLower) ||
            source.description?.toLowerCase().includes(searchLower)
        );
    }
    
    /**
     * Handle search input
     */
    onSearchInput(event) {
        this.state.searchTerm = event.target.value;
    }
    
    /**
     * Get selected sources data
     */
    getSelectedSourcesData() {
        return this.state.availableSources.filter(source => 
            this.state.selectedSources.has(source.model_name)
        );
    }
    
    /**
     * Notify parent component of selection changes
     */
    notifyParentOfSelection() {
        const selectedData = this.getSelectedSourcesData();
        
        this.trigger('sources-changed', {
            selectedSources: Array.from(this.state.selectedSources),
            selectedSourcesData: selectedData,
            isValid: selectedData.length > 0
        });
    }
    
    /**
     * Get CSS classes for source item
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
        
        return classes.join(' ');
    }
    
    /**
     * Handle select all recommended sources
     */
    selectAllRecommended() {
        this.state.availableSources.forEach(source => {
            if (source.recommended && source.available) {
                this.state.selectedSources.add(source.model_name);
            }
        });
        
        this.state.selectedSources = new Set(this.state.selectedSources);
        this.notifyParentOfSelection();
    }
    
    /**
     * Handle clear all selections
     */
    clearAllSelections() {
        this.state.selectedSources.clear();
        this.state.selectedSources = new Set();
        this.notifyParentOfSelection();
    }
    
    /**
     * Format contact count for display
     */
    formatContactCount(count) {
        if (count >= 1000000) {
            return `${(count / 1000000).toFixed(1)}M`;
        } else if (count >= 1000) {
            return `${(count / 1000).toFixed(1)}K`;
        }
        return count.toString();
    }
}

// OWL 1.0 component registration
SourceSelectorComponent.template = 'mailing_list_updater.SourceSelectorTemplate';
SourceSelectorComponent.props = {
    selectedMailingList: { type: Object, optional: true },
};

export { SourceSelectorComponent };