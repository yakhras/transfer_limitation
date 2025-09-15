/** @odoo-module **/

const { Component, useState } = owl;

class SourceSelectorComponent extends Component {

    setup() {
        this.rpc = this.env.services.rpc;
        this.company = this.env.services.company;

        this.state = useState({
            // Original contact source selection (KEEP)
            operationType: null,
            selectedSourceMailingList: null,
            sourceMailingListSearchTerm: '',
            availableSourceMailingLists: [],
            isLoadingSourceMailingLists: false,
            availableSources: [],
            filteredSources: [],
            selectedSources: this.props.selectedSources || [],
            isLoading: false,
            searchTerm: '',
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

    selectOperationType(type) {
        this.state.operationType = type;
        
        // Reset only relevant source selections
        if (type === 'update') {
            // Clear selected source mailing list (for merge)
            this.this.selectedSourceMailingList = null;
        } else if (type === 'merge') {
            // Clear selected contact sources (for update)
            this.props.selectedSources = [];
        }
    }

    /**
     * Handle operation type selection (Update/Merge)
     */
    async onOperationTypeChanged(type) {
        // Emit to parent
        this.trigger('operation-type-changed', { 
            operationType: type 
        });
        
        // Handle specific operation
        if (type === 'merge') {
            await this.loadAvailableSourceMailingLists();
        } else if (type === 'update') {
            // Clear merge data
            this.state.availableSourceMailingLists = [];
            this.state.sourceMailingListSearchTerm = '';
        }
    }

    /**
     * Get filtered source mailing lists based on search term and selection
     */
    get filteredSourceMailingLists() {
        console.log("getter called:", this.props.selectedSourceMailingList);
        
        // If user has selected a list, show only that one
        if (this.props.selectedSourceMailingList) {
            return [this.props.selectedSourceMailingList];
        }

        // If user is searching, show filtered results
        if (this.state.sourceMailingListSearchTerm) {
            const searchTerm = this.state.sourceMailingListSearchTerm.toLowerCase().trim();
            return this.state.availableSourceMailingLists.filter(mailingList => {
                const nameMatch = mailingList.name?.toLowerCase().includes(searchTerm);
                const countMatch = mailingList.contact_count?.toString().includes(searchTerm);
                return nameMatch || countMatch;
            });
        }
        
        // Otherwise show nothing
        return [];
    }

    onSourceMailingListSelected(mailingListId) {
        console.log('Selected ID:', mailingListId);
        // Find selected list from loaded data
        const selectedList = this.state.availableSourceMailingLists.find(
            list => list.id === mailingListId
        );
        console.log('Selected List:', selectedList);

        // Emit event to parent
        this.trigger('source-mailing-list-changed', {
            selectedSourceMailingList: selectedList
        });
    }

    /**
     * Load available source mailing lists for merge operation
     * Called when user selects "Merge" operation type
     */
    async loadAvailableSourceMailingLists() {
        // Set loading state
        this.state.isLoadingSourceMailingLists = true;
        
        // Clear previous data
        this.state.availableSourceMailingLists = [];
        this.state.sourceMailingListSearchTerm = '';
        console.log('targetList', this.selectedMailingList);
        
        try {
            // Call Odoo API to get mailing lists
            const response = await this.env.services.orm.call(
                'mailing.list',
                'search_read',
                [
                    [
                        ["id", "!=", this.props.selectedMailingList?.mailing_list_id || 0]
                    ]
                ],
                {
                    fields: ['id', 'name', 'contact_count', 'create_date'],
                }
            );
            
            // Process and format the response
            if (response && Array.isArray(response)) {
                this.state.availableSourceMailingLists = response.map(list => ({
                    id: list.id,
                    name: list.name,
                    contact_count: list.contact_count || 0,
                }));
                
                console.log(`Loaded ${response.length} source mailing lists for merge`);
            } else {
                throw new Error("Invalid response format from server");
            }
            
        } catch (error) {
            console.error("Failed to load source mailing lists:", error);
            
            // Show user-friendly error message
            this.env.services.notification.add(
                "Failed to load mailing lists. Please try again.", 
                { type: 'danger' }
            );
            
            // Reset to empty state
            this.state.availableSourceMailingLists = [];
            
        } finally {
            // Always clear loading state
            this.state.isLoadingSourceMailingLists = false;
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
    operationType: { validate: (value) => ['update', 'merge', null].includes(value) },
    selectedSourceMailingList: { validate: (value) => value === null || typeof value === 'object' },
};

export { SourceSelectorComponent };