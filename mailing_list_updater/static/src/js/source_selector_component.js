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
        // Only load contact sources on init, target lists load on search
        await this.loadContactSources();
    }

    // ========================================
    // TARGET MAILING LIST METHODS (NEW)
    // ========================================

    async loadTargetMailingLists() {
        // Don't load if search is empty
        if (!this.state.targetSearchTerm || this.state.targetSearchTerm.length < 2) {
            this.state.availableTargetLists = [];
            this.state.targetListsLoading = false;
            return;
        }

        this.state.targetListsLoading = true;
        console.log('Searching for:', this.state.targetSearchTerm);
        
        try {
            // Simple search - just get basic fields
            const response = await this.env.services.orm.searchRead(
                'mailing.list',
                [['name', 'ilike', this.state.targetSearchTerm]],
                ['id', 'name'],
                { limit: 20, context: {} }
            );

            console.log('Basic search successful:', response.length, 'results');

            // Get contact counts separately for each list
            const listsWithCounts = await Promise.all(
                response.map(async (list) => {
                    try {
                        const contactCount = await this.env.services.orm.call(
                            'mailing.contact',
                            'search_count',
                            [[['list_ids', 'in', list.id]]],
                            {}
                        );
                        
                        return {
                            mailing_list_id: list.id,
                            name: list.name,
                            contact_count: contactCount || 0,
                            estimated_count: contactCount || 0,
                            description: `${contactCount || 0} contacts in this mailing list`,
                            available: true,
                            recommended: (contactCount || 0) > 50
                        };
                    } catch (countError) {
                        console.warn('Could not get contact count for list', list.id, countError);
                        return {
                            mailing_list_id: list.id,
                            name: list.name,
                            contact_count: 0,
                            estimated_count: 0,
                            description: 'Contact count unavailable',
                            available: true,
                            recommended: false
                        };
                    }
                })
            );

            this.state.availableTargetLists = listsWithCounts;
            console.log('Lists with counts loaded:', this.state.availableTargetLists);

        } catch (error) {
            console.error('Search failed:', error.message, error);
            // Fallback to basic search without counts
            try {
                const basicResponse = await this.env.services.orm.searchRead(
                    'mailing.list',
                    [['name', 'ilike', this.state.targetSearchTerm]],
                    ['id', 'name'],
                    { limit: 20, context: {} }
                );
                
                this.state.availableTargetLists = basicResponse.map(list => ({
                    mailing_list_id: list.id,
                    name: list.name,
                    contact_count: 0,
                    estimated_count: 0,
                    description: list.name,
                    available: true,
                    recommended: false
                }));
                
                console.log('Fallback search successful');
            } catch (fallbackError) {
                console.error('Fallback search also failed:', fallbackError);
                this.state.availableTargetLists = [];
            }
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
        
        // Clear previous timeout
        clearTimeout(this.targetSearchTimeout);
        
        // Instant search with shorter debounce (150ms)
        this.targetSearchTimeout = setTimeout(() => {
            this.loadTargetMailingLists();
        }, 150);
    }

    clearTargetSearch() {
        this.state.targetSearchTerm = '';
        this.state.availableTargetLists = [];
        // Clear selection if target was selected
        if (this.state.selectedTargetList) {
            this.state.selectedTargetList = null;
            this.notifyParentOfSelection();
        }
    }

    // ========================================
    // ORIGINAL CONTACT SOURCE METHODS (KEEP)
    // ========================================

    async loadContactSources() {
        this.state.isLoading = true;
        console.log('=== CONTACT SOURCES DEBUG ===');
        
        console.log('Skipping /mailing/update/sources - using fallback directly');
        this.loadFallbackSources();
        
        this.state.isLoading = false;
        console.log('=== END CONTACT SOURCES DEBUG ===');
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
        // Show all sources since search was removed
        this.state.filteredSources = [...this.state.availableSources];
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
        // Method kept for compatibility but does nothing since search was removed
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