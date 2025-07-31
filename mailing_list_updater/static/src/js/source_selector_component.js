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
            console.log('Making RPC call to search_read mailing.list');
            const domain = this.state.targetSearchTerm ? 
                [['name', 'ilike', this.state.targetSearchTerm]] : [];
                
            const response = await this.rpc({
                model: 'mailing.list',
                method: 'search_read',
                args: [domain, ['id', 'name', 'contact_ids']],
                kwargs: { limit: 100 }
            });

            console.log('Search_read response:', response);

            const mailingLists = response.map(list => ({
                mailing_list_id: list.id,
                name: list.name,
                contact_count: list.contact_ids ? list.contact_ids.length : 0,
                estimated_count: list.contact_ids ? list.contact_ids.length : 0,
                description: `${list.contact_ids ? list.contact_ids.length : 0} contacts in this mailing list`,
                available: true,
                recommended: (list.contact_ids ? list.contact_ids.length : 0) > 50
            }));

            this.state.availableTargetLists = mailingLists;
            console.log('Target lists loaded:', this.state.availableTargetLists);

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
                // Fallback to basic sources
                this.loadFallbackSources();
            }
        } catch (error) {
            console.error('Contact sources RPC Error:', error);
            // Fallback to basic sources
            this.loadFallbackSources();
        } finally {
            this.state.isLoading = false;
            console.log('=== END CONTACT SOURCES DEBUG ===');
        }
    }

    loadFallbackSources() {
        console.log('Using fallback contact sources');
        this.state.availableSources = [
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
            }
        ];
        this.updateFilteredSources();
        this.preSelectRecommended();
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