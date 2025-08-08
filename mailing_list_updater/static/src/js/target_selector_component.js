/** @odoo-module **/

const { Component, useState } = owl;

class TargetSelectorComponent extends Component {

    setup() {
        this.rpc = this.env.services.rpc;

        this.state = useState({
            // Target mailing list selection (NEW)
            availableTargetLists: [],
            selectedTargetList: this.props.selectedMailingList,
            targetListsLoading: false,
            targetSearchTerm: '',
            
        });

        this.selectedMailingList = this.props.selectedMailingList;
    }

    willUpdateProps(nextProps) {
        // Sync local state with parent when props change
        if (nextProps.selectedMailingList !== this.props.selectedMailingList) {
            this.state.selectedTargetList = nextProps.selectedMailingList;
        }
    }

    // async willStart() {
    //     // Only load contact sources on init, target lists load on search
    //     await this.loadContactSources();
    // }

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
            // Simple search - just get basic fields without contact counts for now
            const response = await this.env.services.orm.searchRead(
                'mailing.list',
                [['name', 'ilike', this.state.targetSearchTerm]],
                ['id', 'name', 'contact_count', 'display_name'], // Only fetch id, name, and contact_count
                { limit: 20, context: {} }
            );

            console.log('Search successful:', response.length, 'results');
            // Log each list with its contact count
            response.forEach(list => {
                console.log(`List: ${list.name} | ID: ${list.id} | Contact Count: ${list.contact_count}`);
            });

            this.state.availableTargetLists = response.map(list => ({
                mailing_list_id: list.id,
                display_name: list.contact_ids.email,
                name: list.name,
                contact_count: list.contact_count, // Skip contact count for now
                estimated_count: 0,
                description: `Mailing list: ${list.name}`,
                available: true,
                recommended: false // Skip recommendation logic for now
            }));

            console.log('Lists loaded:', this.state.availableTargetLists);

        } catch (error) {
            console.error('Search failed:', error.message, error);
            this.state.availableTargetLists = [];
        } finally {
            this.state.targetListsLoading = false;
        }
    }





    async onTargetListSelect(targetList) {
        this.state.selectedTargetList = targetList;

        // ✅ Replace search results with only the selected list
        this.state.availableTargetLists = [targetList];

        // ✅ Clear the search term to hide search UI/status
        this.state.targetSearchTerm = '';

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

    // async loadContactSources() {
    //     this.state.isLoading = true;
    //     console.log('=== CONTACT SOURCES DEBUG ===');
        
    //     console.log('Skipping /mailing/update/sources - using fallback directly');
    //     this.loadFallbackSources();
        
    //     this.state.isLoading = false;
    //     console.log('=== END CONTACT SOURCES DEBUG ===');
    // }

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
        this.trigger('sources-changed', {
            targetMailingList: this.state.selectedTargetList,
            isValid: this.state.selectedTargetList !== null,
        });
    }

    getSourceItemClass(source) {
        let classes = ['source-item'];
        if (this.isSourceSelected(source.model_name)) classes.push('selected');
        if (!source.available) classes.push('unavailable');
        if (source.recommended) classes.push('recommended');
        return classes.join(' ');
    }

    
}

TargetSelectorComponent.template = 'mailing_list_updater.TargetSelectorTemplate';
TargetSelectorComponent.props = {
    selectedMailingList: { validate: (value) => value === null || typeof value === 'object' },
};

export { TargetSelectorComponent };