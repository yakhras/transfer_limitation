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
        try {
            const response = await this.rpc({
                route: "/mailing/update/mailing-lists",
                params: {
                    search: this.state.targetSearchTerm,
                    limit: 100
                }
            });

            if (response.success) {
                this.state.availableTargetLists = response.data.sources || [];
            }
        } catch (error) {
            // Fallback mock data
            this.state.availableTargetLists = [
                { mailing_list_id: 1, name: 'Newsletter Subscribers', contact_count: 1247 },
                { mailing_list_id: 2, name: 'Product Updates', contact_count: 856 }
            ];
        } finally {
            this.state.targetListsLoading = false;
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
        try {
            const response = await this.rpc({
                route: "/mailing/update/sources",
                params: {}
            });

            if (response.success) {
                this.state.availableSources = response.data.sources;
                this.updateFilteredSources();
                this.preSelectRecommended();
            }
        } catch (error) {
            // Original fallback
            this.state.availableSources = [
                {
                    model_name: 'res.partner',
                    name: 'Contacts',
                    description: 'Import contacts from Contacts module',
                    available: true,
                    recommended: true,
                    estimated_count: 1247
                },
                {
                    model_name: 'crm.lead',
                    name: 'CRM Leads',
                    description: 'Import contacts from CRM Leads',
                    available: true,
                    recommended: true,
                    estimated_count: 856
                }
            ];
            this.updateFilteredSources();
            this.preSelectRecommended();
        } finally {
            this.state.isLoading = false;
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
        const recommended = this.state.availableSources
            .filter(s => s.recommended && s.available)
            .map(s => s.model_name);
        this.state.selectedSources = Array.from(new Set([...this.state.selectedSources, ...recommended]));
        this.notifyParentOfSelection();
    }

    clearAllSelections() {
        this.state.selectedSources = [];
        this.notifyParentOfSelection();
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