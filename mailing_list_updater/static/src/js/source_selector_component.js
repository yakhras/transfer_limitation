/** @odoo-module **/

const { Component, useState } = owl;

class SourceSelectorComponent extends Component {

    setup() {
        this.rpc = this.env.services.rpc;

        this.state = useState({
            // Target mailing list selection (NEW)
            availableTargetLists: [],
            selectedTargetList: null,
            targetListsLoading: false,
            targetSearchTerm: '',
            
            // Original contact source selection (KEEP)
            availableSources: [],
            filteredSources: [],
            selectedSources: [],
            isLoading: false,
            searchTerm: '',
            showSourceDetails: {},
        });

        this.selectedMailingList = this.props.selectedMailingList;
    }

    async willStart() {
        // Load both target lists and contact sources
        await Promise.all([
            this.loadTargetMailingLists(),
            this.loadContactSources()
        ]);
    }

    // ========================================
    // TARGET MAILING LIST METHODS (NEW)
    // ========================================

    async loadTargetMailingLists() {
        this.state.targetListsLoading = true;
        console.log('=== TARGET MAILING LIST DEBUG ===');
        console.log('Search term:', this.state.targetSearchTerm);
        
        try {
            console.log('Making RPC call to /mailing/update/mailing-lists');
            const response = await this.rpc({
                route: "/mailing/update/mailing-lists",
                params: {
                    search: this.state.targetSearchTerm,
                    limit: 100
                }
            });

            console.log('RPC Response:', response);

            if (response.success) {
                this.state.availableTargetLists = response.data.sources || [];
                console.log('Target lists loaded:', this.state.availableTargetLists);
            } else {
                console.error('RPC failed:', response.error);
                this.state.availableTargetLists = [];
            }
        } catch (error) {
            console.error('RPC Error:', error);
            this.state.availableTargetLists = [];
        } finally {
            this.state.targetListsLoading = false;
            console.log('=== END TARGET DEBUG ===');
        }
    }

    onTargetListSelect(targetList) {
        this.state.selectedTargetList = targetList;
        this.notifyParentOfSelection();
    }

    onTargetSearchInput(event) {
        this.state.targetSearchTerm = event.target.value;
        clearTimeout(this.targetSearchTimeout);
        this.targetSearchTimeout = setTimeout(() => {
            this.loadTargetMailingLists();
        }, 300);
    }

    // ========================================
    // ORIGINAL CONTACT SOURCE METHODS (KEEP)
    // ========================================

    async loadContactSources() {
        this.state.isLoading = true;
        console.log('=== CONTACT SOURCES DEBUG ===');
        
        try {
            console.log('Making RPC call to /mailing/update/sources');
            const response = await this.rpc({
                route: "/mailing/update/sources",
                params: {}
            });

            console.log('Contact sources response:', response);

            if (response.success) {
                this.state.availableSources = response.data.sources;
                this.updateFilteredSources();
                this.preSelectRecommended();
                console.log('Contact sources loaded:', this.state.availableSources);
            } else {
                console.error('Contact sources RPC failed:', response.error);
                this.state.availableSources = [];
            }
        } catch (error) {
            console.error('Contact sources RPC Error:', error);
            this.state.availableSources = [];
        } finally {
            this.state.isLoading = false;
            console.log('=== END CONTACT SOURCES DEBUG ===');
        }
    }

    updateFilteredSources() {
        const term = this.state.searchTerm.toLowerCase();
        this.state.filteredSources = term
            ? this.state.availableSources.filter(s =>
                s.name.toLowerCase().includes(term) ||
                s.description?.toLowerCase().includes(term)
            )
            : [...this.state.availableSources];
    }

    preSelectRecommended() {
        this.state.selectedSources = this.state.availableSources
            .filter(s => s.recommended)
            .map(s => s.model_name);
        this.notifyParentOfSelection();
    }

    onSourceToggle(event) {
        const modelName = event.currentTarget.dataset.model;
        const index = this.state.selectedSources.indexOf(modelName);

        if (index >= 0) {
            this.state.selectedSources = this.state.selectedSources.filter(name => name !== modelName);
        } else {
            this.state.selectedSources.push(modelName);
        }
        this.notifyParentOfSelection();
    }

    isSourceSelected(modelName) {
        return this.state.selectedSources.includes(modelName);
    }

    toggleSourceDetails(event) {
        const modelName = event.currentTarget.dataset.model;
        this.state.showSourceDetails[modelName] = !this.state.showSourceDetails[modelName];
        event.stopPropagation();
    }

    onSearchInput(event) {
        this.state.searchTerm = event.target.value;
        this.updateFilteredSources();
    }

    selectAllRecommended() {
        // Method kept for compatibility but does nothing
    }

    clearAllSelections() {
        // Method kept for compatibility but does nothing
    }

    // ========================================
    // SHARED METHODS
    // ========================================

    notifyParentOfSelection() {
        const selectedSourcesData = this.state.availableSources.filter(source =>
            this.state.selectedSources.includes(source.model_name)
        );

        this.trigger('sources-changed', {
            // Target mailing list (NEW)
            targetMailingList: this.state.selectedTargetList,
            
            // Contact sources (ORIGINAL)
            selectedSources: this.state.selectedSources,
            selectedSourcesData: selectedSourcesData,
            
            // Validation
            isValid: this.state.selectedTargetList !== null && selectedSourcesData.length > 0,
        });
    }

    getSourceItemClass(source) {
        let classes = ['source-item'];
        if (this.isSourceSelected(source.model_name)) classes.push('selected');
        if (!source.available) classes.push('unavailable');
        if (source.recommended) classes.push('recommended');
        return classes.join(' ');
    }

    formatContactCount(count) {
        if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
        if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
        return count.toString();
    }
}

SourceSelectorComponent.template = 'mailing_list_updater.SourceSelectorTemplate';
SourceSelectorComponent.props = {
    selectedMailingList: { validate: (value) => value === null || typeof value === 'object' },
};

export { SourceSelectorComponent };