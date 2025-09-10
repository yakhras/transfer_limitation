/** @odoo-module **/

const { Component, useState } = owl;

class SourceSelectorComponent extends Component {

    setup() {
        this.rpc = this.env.services.rpc;
        this.company = this.env.services.company;

        this.state = useState({
            // Original contact source selection (KEEP)
            availableSources: [],
            filteredSources: [],
            selectedSources: this.props.selectedSources || [],
            isLoading: false,
            searchTerm: '',
            companyRecordCounts: {},
            currentCompany: this.company?.currentCompany || null,
        });

        this.selectedMailingList = this.props.selectedMailingList;
    }

    async willStart() {
        // Only load contact sources on init, target lists load on search
        if (this.company && this.company.currentCompany) {
            this.state.currentCompany = this.company.currentCompany;
        }
        await this.loadContactSources();
    }

    // ===== FIX: Add mounted lifecycle to trigger initial notification =====
    mounted() {
        console.log('=== SOURCE SELECTOR MOUNTED ===');
        console.log('Initial selected sources:', this.state.selectedSources);
        
        // Trigger initial notification if sources are pre-selected
        if (this.state.selectedSources.length > 0) {
            console.log('Triggering initial notification for pre-selected sources');
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

    // ===== FIX: Modified preSelectRecommended to NOT notify initially =====
    preSelectRecommended() {
        console.log('=== PRE-SELECT RECOMMENDED ===');
        console.log('Current selected sources:', this.state.selectedSources);
        console.log('Props selected sources:', this.props.selectedSources);
        
        if (this.state.selectedSources.length === 0) {
            this.state.selectedSources = this.state.availableSources
                .filter(s => s.recommended)
                .map(s => s.model_name);
            
            console.log('Pre-selected recommended sources:', this.state.selectedSources);
            
            // DON'T notify here - let mounted() handle it
            // this.notifyParentOfSelection(); // REMOVED
        }
    }

    willUpdateProps(nextProps) {
        console.log('=== SOURCE SELECTOR PROPS UPDATE ===');
        console.log('Current props selectedSources:', this.props.selectedSources);
        console.log('Next props selectedSources:', nextProps.selectedSources);
        
        if (nextProps.selectedSources !== this.props.selectedSources) {
            this.state.selectedSources = nextProps.selectedSources || [];
            console.log('Updated selectedSources from props:', this.state.selectedSources);
        }
    }

    onSourceToggle(event) {
        const modelName = event.currentTarget.dataset.model;
        const index = this.state.selectedSources.indexOf(modelName);

        console.log('=== SOURCE TOGGLE ===');
        console.log('Toggling model:', modelName);
        console.log('Current selected:', this.state.selectedSources);

        if (index >= 0) {
            this.state.selectedSources = this.state.selectedSources.filter(name => name !== modelName);
        } else {
            this.state.selectedSources.push(modelName);
        }
        
        console.log('New selected sources:', this.state.selectedSources);
        this.notifyParentOfSelection();
    }

    isSourceSelected(modelName) {
        return this.state.selectedSources.includes(modelName);
    }

    async fetchCompanyRecordCount(modelName) {
        try {
            const domain = [['company_id', '=', this.company.currentCompany.id]];
            console.log('Fetching count for model:', modelName);
            console.log('Using domain:', domain);
            
            const count = await this.rpc({
                model: modelName,
                method: 'search_count',
                args: [domain]
            });
            console.log(`Count for ${modelName}:`, count);
            this.state.companyRecordCounts[modelName] = count;
        } catch (error) {
            console.error(`Failed to get record count for ${modelName}:`, error);
            this.state.companyRecordCounts[modelName] = 'N/A';
        }
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

    // ===== FIX: Enhanced notification with better logging =====
    notifyParentOfSelection() {
        console.log('=== NOTIFY PARENT OF SELECTION ===');
        console.log('Selected source model names:', this.state.selectedSources);
        console.log('Available sources:', this.state.availableSources);
        
        const selectedSourcesData = this.state.availableSources.filter(source =>
            this.state.selectedSources.includes(source.model_name)
        );
        
        console.log('Selected sources data:', selectedSourcesData);
        
        const eventData = {
            // Target mailing list (if applicable)
            targetMailingList: this.state.selectedTargetList || null,
            
            // Contact sources (ORIGINAL)
            selectedSources: this.state.selectedSources,
            selectedSourcesData: selectedSourcesData,
            
            // Validation
            isValid: selectedSourcesData.length > 0,
        };
        
        console.log('Triggering sources-changed event with:', eventData);
        
        this.trigger('sources-changed', eventData);
    }

    getSourceItemClass(source) {
        let classes = ['source-item'];
        if (this.isSourceSelected(source.model_name)) classes.push('selected');
        if (!source.available) classes.push('unavailable');
        if (source.recommended) classes.push('recommended');
        return classes.join(' ');
    }
}

SourceSelectorComponent.template = 'mailing_list_updater_t.SourceSelectorTemplate';
SourceSelectorComponent.props = {
    selectedMailingList: { validate: (value) => value === null || typeof value === 'object' },
    selectedSources: { validate: (value) => Array.isArray(value), optional: true },
};

export { SourceSelectorComponent };