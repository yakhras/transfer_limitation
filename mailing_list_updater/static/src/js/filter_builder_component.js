/** @odoo-module **/

const { Component, useState } = owl;

/**
 * Filter Builder Component - Connected to Source Selection
 * Now dynamically loads fields based on selected source models
 */
class FilterBuilderComponent extends Component {
    
    setup() {
        console.log('=== FILTER BUILDER SETUP ===');
        console.log('Received selectedSources prop:', this.props.selectedSources);
        
        // Services (OWL 1.0 style for Odoo 15.0)
        this.orm = this.env.services.orm;
        this.rpc = this.env.services.rpc;
        
        // Component state
        this.state = useState({
            // Quick filters (common for all sources)
            quickFilters: {
                active_only: true,
                date_range: {
                    enabled: true,
                    from: '2025-01-01',
                    to: '2025-12-31',
                    field: 'create_date'
                },
                responsible_users: [],
                tags: [],
                category_ids: [],
                country_ids: []
            },
            
            // User search functionality
            userSearch: {
                query: '',
                results: [],
                showSuggestions: false,
                loading: false
            },
            
            // Advanced filters - now model-aware
            advancedFilters: {
                enabled: false,
                logic: 'AND',
                rules: []
            },
            
            // Available fields per model - NEW
            availableFieldsByModel: {}, // { 'res.partner': [...], 'crm.lead': [...] }
            availableFields: [], // Combined fields with model prefix
            selectedModels: [], // Currently selected source models
            
            // UI state
            isLoading: false,
            showAdvanced: false,
            domainTestResults: null, // NEW - Store test results
            
            // Form state
            newRule: {
                field: '',
                operator: '',
                value: '',
                field_type: '',
                model: '' // NEW - track which model the field belongs to
            }
        });
        
        // Store selected sources from props
        this.selectedSources = this.props.selectedSources || [];
        console.log('Initial selectedSources from props:', this.selectedSources);
        console.log('Props selectedSources type:', typeof this.props.selectedSources);
        console.log('Props selectedSources length:', this.props.selectedSources?.length || 0);
        
        // Debounce timer for user search
        this.searchTimeout = null;
    }
    
    /**
     * OWL 1.0 Lifecycle - Will Start
     */
    async willStart() {
        this.state.isLoading = true;
        
        try {
            // Load fields based on initially selected sources
            await this.updateFieldsForSelectedSources();
            
            // Load filter templates and default users
            await this.loadFilterTemplates();
            await this.loadDefaultUsers();
            
        } catch (error) {
            console.error("Filter options loading error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * FIX: Add mounted lifecycle to handle initial props
     */
    mounted() {
        console.log('=== FILTER BUILDER MOUNTED ===');
        console.log('Props selectedSources on mount:', this.props.selectedSources);
        console.log('State selectedSources on mount:', this.selectedSources);
        
        // If we have initial sources from props, update fields
        if (this.props.selectedSources && this.props.selectedSources.length > 0) {
            console.log('Processing initial selectedSources from props');
            this.selectedSources = this.props.selectedSources;
            this.updateFieldsForSelectedSources();
        }
        
        // Setup event listeners for click outside (for user suggestions)
        document.addEventListener('click', this.handleClickOutside.bind(this));
    }
    
    /**
     * NEW - React to prop changes (when sources are selected/deselected)
     */
    willUpdateProps(nextProps) {
        console.log('=== PROPS UPDATE ===');
        console.log('Current selectedSources:', this.selectedSources);
        console.log('New selectedSources:', nextProps.selectedSources);
        
        if (nextProps.selectedSources !== this.selectedSources) {
            this.selectedSources = nextProps.selectedSources || [];
            // Update fields when sources change
            this.updateFieldsForSelectedSources();
        }
    }
    
    /**
     * NEW - Update available fields based on selected sources
     */
    async updateFieldsForSelectedSources() {
        console.log('=== UPDATE FIELDS FOR SOURCES ===');
        console.log('Selected sources:', this.selectedSources);
        
        if (!this.selectedSources || this.selectedSources.length === 0) {
            console.log('No sources selected, clearing fields');
            this.state.availableFieldsByModel = {};
            this.state.availableFields = [];
            this.state.selectedModels = [];
            return;
        }
        
        // Extract model names from selected sources
        const modelNames = this.selectedSources.map(source => source.model_name);
        console.log('Model names to load:', modelNames);
        
        this.state.selectedModels = modelNames;
        this.state.isLoading = true;
        
        try {
            // Load fields for each selected model
            const fieldsByModel = {};
            
            for (const modelName of modelNames) {
                console.log(`Loading fields for model: ${modelName}`);
                const fields = await this.loadFieldsForModel(modelName);
                fieldsByModel[modelName] = fields;
                console.log(`Loaded ${fields.length} fields for ${modelName}`);
            }
            
            this.state.availableFieldsByModel = fieldsByModel;
            
            // Combine all fields with model prefix for the dropdown
            this.combineFieldsWithModelPrefix();
            
            console.log('Final availableFieldsByModel:', this.state.availableFieldsByModel);
            console.log('Final combined fields count:', this.state.availableFields.length);
            
        } catch (error) {
            console.error('Error loading fields for sources:', error);
            // Fallback to empty fields
            this.state.availableFieldsByModel = {};
            this.state.availableFields = [];
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * NEW - Load fields for a specific model
     */
    async loadFieldsForModel(modelName) {
        console.log(`=== LOAD FIELDS FOR MODEL: ${modelName} ===`);
        
        try {
            let response = null;
            
            // Method 1: Try ORM service
            if (this.orm) {
                try {
                    response = await this.orm.call(modelName, 'fields_get', [], {
                        attributes: ['string', 'type', 'required', 'readonly', 'selection']
                    });
                    console.log(`ORM fields_get response for ${modelName}:`, response);
                } catch (ormError) {
                    console.log(`ORM fields_get failed for ${modelName}:`, ormError);
                }
            }
            
            // Method 2: Try RPC service
            if (!response && this.rpc) {
                try {
                    response = await this.rpc('/web/dataset/call_kw', {
                        model: modelName,
                        method: 'fields_get',
                        args: [],
                        kwargs: {
                            attributes: ['string', 'type', 'required', 'readonly', 'selection']
                        }
                    });
                    console.log(`RPC fields_get response for ${modelName}:`, response);
                } catch (rpcError) {
                    console.log(`RPC fields_get failed for ${modelName}:`, rpcError);
                }
            }
            
            // Method 3: Use mock fields if API fails
            if (!response) {
                console.log(`Using mock fields for ${modelName}`);
                response = this.getMockFieldsForModel(modelName);
            }
            
            // Convert fields response to array format
            const fieldsArray = [];
            
            if (response && typeof response === 'object') {
                // Get common fields for the model
                const commonFields = this.getCommonFieldsForModel(modelName);
                
                Object.keys(response).forEach(fieldName => {
                    const field = response[fieldName];
                    
                    // Include common fields or non-system fields
                    if (commonFields.includes(fieldName) || 
                        (!fieldName.startsWith('__') && !fieldName.startsWith('message_') && 
                         !fieldName.startsWith('activity_'))) {
                        
                        fieldsArray.push({
                            name: fieldName,
                            string: field.string || fieldName,
                            type: field.type || 'char',
                            required: field.required || false,
                            readonly: field.readonly || false,
                            selection: field.selection || null,
                            model: modelName // Add model reference
                        });
                    }
                });
                
                // Sort fields alphabetically by display name
                fieldsArray.sort((a, b) => a.string.localeCompare(b.string));
            }
            
            return fieldsArray;
            
        } catch (error) {
            console.error(`Error loading fields for ${modelName}:`, error);
            // Return mock fields as fallback
            return this.getMockFieldsArrayForModel(modelName);
        }
    }
    
    /**
     * NEW - Get common fields for specific models
     */
    getCommonFieldsForModel(modelName) {
        const commonFieldsByModel = {
            'res.partner': [
                'name', 'email', 'phone', 'mobile', 'street', 'street2', 'city', 
                'state_id', 'country_id', 'zip', 'website', 'is_company', 'category_id',
                'user_id', 'create_date', 'write_date', 'active', 'customer_rank',
                'supplier_rank', 'title', 'function', 'industry_id', 'comment'
            ],
            'crm.lead': [
                'name', 'email_from', 'phone', 'mobile', 'street', 'street2', 'city',
                'state_id', 'country_id', 'zip', 'website', 'partner_id', 'user_id',
                'team_id', 'stage_id', 'tag_ids', 'create_date', 'write_date', 'active',
                'probability', 'expected_revenue', 'date_deadline', 'description'
            ]
        };
        
        return commonFieldsByModel[modelName] || [];
    }
    
    /**
     * NEW - Get mock fields for specific models
     */
    getMockFieldsForModel(modelName) {
        const mockFields = {
            'res.partner': {
                'name': { string: 'Name', type: 'char', required: true },
                'email': { string: 'Email', type: 'char' },
                'phone': { string: 'Phone', type: 'char' },
                'mobile': { string: 'Mobile', type: 'char' },
                'street': { string: 'Street', type: 'char' },
                'city': { string: 'City', type: 'char' },
                'state_id': { string: 'State', type: 'many2one' },
                'country_id': { string: 'Country', type: 'many2one' },
                'is_company': { string: 'Is a Company', type: 'boolean' },
                'category_id': { string: 'Tags', type: 'many2many' },
                'user_id': { string: 'Salesperson', type: 'many2one' },
                'create_date': { string: 'Created on', type: 'datetime' },
                'active': { string: 'Active', type: 'boolean' }
            },
            'crm.lead': {
                'name': { string: 'Opportunity', type: 'char', required: true },
                'email_from': { string: 'Email', type: 'char' },
                'phone': { string: 'Phone', type: 'char' },
                'mobile': { string: 'Mobile', type: 'char' },
                'partner_id': { string: 'Customer', type: 'many2one' },
                'user_id': { string: 'Salesperson', type: 'many2one' },
                'team_id': { string: 'Sales Team', type: 'many2one' },
                'stage_id': { string: 'Stage', type: 'many2one' },
                'tag_ids': { string: 'Tags', type: 'many2many' },
                'probability': { string: 'Probability', type: 'float' },
                'expected_revenue': { string: 'Expected Revenue', type: 'monetary' },
                'create_date': { string: 'Created on', type: 'datetime' },
                'active': { string: 'Active', type: 'boolean' }
            }
        };
        
        return mockFields[modelName] || {};
    }
    
    /**
     * NEW - Get mock fields array for specific model
     */
    getMockFieldsArrayForModel(modelName) {
        const mockFields = this.getMockFieldsForModel(modelName);
        return Object.keys(mockFields).map(fieldName => ({
            name: fieldName,
            string: mockFields[fieldName].string,
            type: mockFields[fieldName].type,
            required: mockFields[fieldName].required || false,
            readonly: mockFields[fieldName].readonly || false,
            selection: mockFields[fieldName].selection || null,
            model: modelName
        })).sort((a, b) => a.string.localeCompare(b.string));
    }
    
    /**
     * NEW - Combine fields from all models with model prefix
     */
    combineFieldsWithModelPrefix() {
        console.log('=== COMBINE FIELDS WITH MODEL PREFIX ===');
        
        const combinedFields = [];
        
        // Get source names for display
        const sourceNamesByModel = {};
        this.selectedSources.forEach(source => {
            sourceNamesByModel[source.model_name] = source.name;
        });
        
        // Add fields from each model with prefix
        Object.keys(this.state.availableFieldsByModel).forEach(modelName => {
            const fields = this.state.availableFieldsByModel[modelName];
            const sourceName = sourceNamesByModel[modelName] || modelName;
            
            fields.forEach(field => {
                combinedFields.push({
                    name: `${modelName}.${field.name}`, // Prefixed field name
                    originalName: field.name, // Keep original for domain building
                    string: `${field.string} (${sourceName})`, // Display with source name
                    type: field.type,
                    required: field.required,
                    readonly: field.readonly,
                    selection: field.selection,
                    model: modelName
                });
            });
        });
        
        // Sort by display name
        combinedFields.sort((a, b) => a.string.localeCompare(b.string));
        
        this.state.availableFields = combinedFields;
        console.log(`Combined ${combinedFields.length} fields from ${Object.keys(this.state.availableFieldsByModel).length} models`);
    }

    /**
     * Load filter templates
     */
    async loadFilterTemplates() {
        // Keep existing implementation or add mock
    }
    
    /**
     * Load default users (existing implementation)
     */
    async loadDefaultUsers() {
        console.log('=== LOAD DEFAULT USERS ===');
        
        try {
            console.log('Attempting to load default users...');
            
            const domain = [['active', '=', true], ['share', '=', false]]; // Active internal users
            let response = null;
            
            // Method 1: Try ORM service (Odoo 15.0 preferred)
            if (this.orm) {
                console.log('Trying ORM service for default users...');
                try {
                    response = await this.orm.searchRead(
                        'res.users',
                        domain,
                        ['id', 'name', 'email'],
                        { limit: 3 }
                    );
                    console.log('ORM service response for default users:', response);
                } catch (ormError) {
                    console.log('ORM service failed for default users:', ormError);
                }
            }
            
            // Method 2: Try RPC service
            if (!response && this.rpc) {
                console.log('Trying RPC service for default users...');
                try {
                    response = await this.rpc('/web/dataset/search_read', {
                        model: 'res.users',
                        domain: domain,
                        fields: ['id', 'name', 'email'],
                        limit: 3
                    });
                    
                    if (response && response.records) {
                        response = response.records;
                    }
                    console.log('RPC service response for default users:', response);
                } catch (rpcError) {
                    console.log('RPC service failed for default users:', rpcError);
                }
            }
            
            // Method 3: Use mock data fallback
            if (!response) {
                console.log('Using mock data for default users');
                response = [
                    { id: 1, name: 'John Smith', email: 'john.smith@company.com' },
                    { id: 2, name: 'Sarah Johnson', email: 'sarah.johnson@company.com' },
                    { id: 3, name: 'Mike Davis', email: 'mike.davis@company.com' }
                ];
            }
            
            console.log('Final default users response:', response);
            
            if (response && response.length) {
                console.log('Loading', response.length, 'default users');
                this.state.quickFilters.responsible_users = response;
                console.log('Updated responsible_users state:', this.state.quickFilters.responsible_users);
            } else {
                console.log('No default users found or empty response');
            }
        } catch (error) {
            console.error("=== DEFAULT USERS LOAD ERROR ===");
            console.error("Error object:", error);
            
            // Set mock data on error
            console.log('Setting mock default users due to error');
            this.state.quickFilters.responsible_users = [
                { id: 1, name: 'John Smith', email: 'john.smith@company.com' },
                { id: 2, name: 'Sarah Johnson', email: 'sarah.johnson@company.com' },
                { id: 3, name: 'Mike Davis', email: 'mike.davis@company.com' }
            ];
        }
    }
    
    /**
     * Handle user search input
     */
    onUserSearch(query) {
        console.log('=== USER SEARCH DEBUG ===');
        console.log('Search query input:', query);
        
        this.state.userSearch.query = query;
        
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
            console.log('Cleared previous search timeout');
        }
        
        // Debounce search
        this.searchTimeout = setTimeout(() => {
            console.log('Executing debounced search for:', query);
            this.searchUsers(query);
        }, 300);
        
        console.log('Search timeout set for 300ms');
    }
    
    /**
     * Search users in res.users model
     */
    async searchUsers(query) {
        console.log('=== SEARCH USERS METHOD ===');
        console.log('Query:', query);
        console.log('Query length:', query ? query.length : 0);
        
        if (!query || query.length < 2) {
            console.log('Query too short, clearing results');
            this.state.userSearch.results = [];
            return;
        }
        
        this.state.userSearch.loading = true;
        console.log('Set loading to true');
        
        try {
            const domain = [
                ['active', '=', true],
                ['share', '=', false], // Internal users only
                '|',
                ['name', 'ilike', query],
                ['email', 'ilike', query]
            ];
            
            console.log('Search domain:', JSON.stringify(domain, null, 2));
            
            let response = null;
            
            // Method 1: Try ORM service (Odoo 15.0 preferred)
            if (this.orm) {
                console.log('Trying ORM service...');
                try {
                    response = await this.orm.searchRead(
                        'res.users',
                        domain,
                        ['id', 'name', 'email'],
                        { limit: 10 }
                    );
                    console.log('ORM service response:', response);
                } catch (ormError) {
                    console.log('ORM service failed:', ormError);
                }
            }
            
            // Method 2: Try RPC service with correct format
            if (!response && this.rpc) {
                console.log('Trying RPC service...');
                try {
                    response = await this.rpc('/web/dataset/search_read', {
                        model: 'res.users',
                        domain: domain,
                        fields: ['id', 'name', 'email'],
                        limit: 10
                    });
                    console.log('RPC service response:', response);
                    
                    // Extract records if response has records property
                    if (response && response.records) {
                        response = response.records;
                    }
                } catch (rpcError) {
                    console.log('RPC service failed:', rpcError);
                }
            }
            
            // Method 3: Mock data fallback for development
            if (!response) {
                console.log('All methods failed, using mock data for development');
                response = this.getMockUsers(query);
            }
            
            console.log('Final response:', response);
            
            if (response && response.length > 0) {
                console.log('Sample user from response:', response[0]);
            }
            
            // Filter out already selected users
            const selectedIds = this.state.quickFilters.responsible_users.map(u => u.id);
            console.log('Currently selected user IDs:', selectedIds);
            
            const filteredResults = response.filter(user => !selectedIds.includes(user.id));
            console.log('Filtered results (excluding selected):', filteredResults);
            
            this.state.userSearch.results = filteredResults;
            console.log('Updated search results state:', this.state.userSearch.results);
            
        } catch (error) {
            console.error("=== USER SEARCH ERROR ===");
            console.error("Error object:", error);
            
            // Fallback to mock data on error
            console.log('Using mock data fallback due to error');
            this.state.userSearch.results = this.getMockUsers(query);
        } finally {
            this.state.userSearch.loading = false;
            console.log('Set loading to false');
        }
    }
    
    /**
     * Mock users for development/fallback
     */
    getMockUsers(query) {
        const mockUsers = [
            { id: 1, name: 'John Smith', email: 'john.smith@company.com' },
            { id: 2, name: 'Sarah Johnson', email: 'sarah.johnson@company.com' },
            { id: 3, name: 'Mike Davis', email: 'mike.davis@company.com' },
            { id: 4, name: 'Emily Brown', email: 'emily.brown@company.com' },
            { id: 5, name: 'David Wilson', email: 'david.wilson@company.com' },
            { id: 6, name: 'Lisa Anderson', email: 'lisa.anderson@company.com' },
            { id: 7, name: 'Tom Miller', email: 'tom.miller@company.com' },
            { id: 8, name: 'Jennifer Taylor', email: 'jennifer.taylor@company.com' }
        ];
        
        // Filter mock users based on query
        return mockUsers.filter(user => 
            user.name.toLowerCase().includes(query.toLowerCase()) ||
            user.email.toLowerCase().includes(query.toLowerCase())
        );
    }
    
    /**
     * Show/hide user suggestions
     */
    showUserSuggestions(show) {
        console.log('=== SHOW USER SUGGESTIONS ===');
        console.log('Show suggestions:', show);
        console.log('Current query:', this.state.userSearch.query);
        
        this.state.userSearch.showSuggestions = show;
        
        if (show && this.state.userSearch.query) {
            console.log('Triggering search because suggestions shown and query exists');
            this.searchUsers(this.state.userSearch.query);
        } else {
            console.log('Not triggering search - show:', show, 'query:', this.state.userSearch.query);
        }
        
        console.log('Updated showSuggestions state:', this.state.userSearch.showSuggestions);
    }
    
    /**
     * Select a user from search results
     */
    selectUser(user) {
        console.log('=== SELECT USER ===');
        console.log('Selected user:', user);
        console.log('Current responsible users:', this.state.quickFilters.responsible_users);
        
        // Add user to selected list
        this.state.quickFilters.responsible_users.push(user);
        console.log('Updated responsible users:', this.state.quickFilters.responsible_users);
        
        // Clear search
        this.state.userSearch.query = '';
        this.state.userSearch.results = [];
        this.state.userSearch.showSuggestions = false;
        
        console.log('Cleared search state');
        
        // Notify change
        this.notifyFilterChange();
        console.log('Notified filter change');
    }
    
    /**
     * Remove selected user
     */
    removeSelectedUser(userId) {
        console.log('=== REMOVE USER ===');
        console.log('Removing user ID:', userId);
        console.log('Current users:', this.state.quickFilters.responsible_users);
        
        const index = this.state.quickFilters.responsible_users.findIndex(u => u.id === userId);
        console.log('Found user at index:', index);
        
        if (index !== -1) {
            this.state.quickFilters.responsible_users.splice(index, 1);
            console.log('User removed, updated list:', this.state.quickFilters.responsible_users);
            this.notifyFilterChange();
        } else {
            console.log('User not found in list');
        }
    }
    
    /**
     * Handle click outside to close user suggestions
     */
    handleClickOutside(event) {
        const userSearchContainer = event.target.closest('.position-relative');
        if (!userSearchContainer) {
            this.state.userSearch.showSuggestions = false;
        }
    }
    
    /**
     * Handle quick filter changes
     */
    onQuickFilterChange(filterType, value) {
        console.log('Quick filter change:', filterType, value);
        this.state.quickFilters[filterType] = value;
        this.notifyFilterChange();
    }
    
    /**
     * Handle date range filter changes
     */
    onDateRangeChange(field, value) {
        console.log('Date range change:', field, value);
        this.state.quickFilters.date_range[field] = value;
        this.notifyFilterChange();
    }
    
    /**
     * Toggle date range filter
     */
    toggleDateRange() {
        this.state.quickFilters.date_range.enabled = !this.state.quickFilters.date_range.enabled;
        this.notifyFilterChange();
    }
    
    /**
     * Change advanced filter logic (AND/OR)
     */
    changeFilterLogic(logic) {
        this.state.advancedFilters.logic = logic;
        this.notifyFilterChange();
    }
    
    /**
     * OWL 1.0 Lifecycle - Will Unmount
     * Cleanup event listeners
     */
    willUnmount() {
        document.removeEventListener('click', this.handleClickOutside.bind(this));
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
    }
    
    /**
     * Handle new rule field selection - UPDATED for model-aware fields
     */
    onRuleFieldChange(fieldName) {
        console.log('=== RULE FIELD CHANGE ===');
        console.log('Selected field name:', fieldName);
        
        const field = this.state.availableFields.find(f => f.name === fieldName);
        console.log('Found field definition:', field);
        
        this.state.newRule.field = fieldName;
        this.state.newRule.field_type = field?.type || '';
        this.state.newRule.model = field?.model || ''; // NEW - track model
        this.state.newRule.operator = this.getDefaultOperator(field?.type);
        this.state.newRule.value = '';
        
        console.log('Updated new rule state:', this.state.newRule);
    }
    
    // ... (keep all other existing methods like getDefaultOperator, etc.)
    
    /**
     * Format rule display - UPDATED to show model context
     */
    formatRuleDisplay(rule) {
        const field = this.state.availableFields.find(f => f.name === rule.field);
        const fieldName = field?.string || rule.field;
        const operator = this.getOperatorsForFieldType(rule.field_type)
            .find(op => op.value === rule.operator)?.label || rule.operator;
        
        return `${fieldName} ${operator} ${rule.value}`;
    }
    
    /**
     * Get current filter data - UPDATED to include model information and generate domains
     */
    getCurrentFilters() {
        return {
            quick_filters: {
                ...this.state.quickFilters,
                responsible_users: this.state.quickFilters.responsible_users.map(u => u.id)
            },
            advanced_filters: {
                ...this.state.advancedFilters,
                rules: this.state.advancedFilters.rules.map(rule => ({
                    ...rule,
                    model: rule.model || this.extractModelFromField(rule.field),
                    original_field: this.extractOriginalFieldName(rule.field)
                }))
            },
            selected_models: this.state.selectedModels, // Include selected models
            generated_domains: this.generateOdooDomainsPerModel() // NEW - Generate actual Odoo domains
        };
    }
    
    /**
     * NEW - Generate actual Odoo domains for each model
     */
    generateOdooDomainsPerModel() {
        console.log('=== GENERATE ODOO DOMAINS ===');
        
        const domainsByModel = {};
        
        // Initialize domains for each selected model
        this.state.selectedModels.forEach(modelName => {
            domainsByModel[modelName] = [];
        });
        
        console.log('Initialized domains for models:', Object.keys(domainsByModel));
        
        // Add quick filters (common to all models)
        this.addQuickFilterDomains(domainsByModel);
        
        // Add advanced filter rules (model-specific)
        this.addAdvancedFilterDomains(domainsByModel);
        
        console.log('Final generated domains:', domainsByModel);
        return domainsByModel;
    }
    
    /**
     * NEW - Add quick filter domains to all models
     */
    addQuickFilterDomains(domainsByModel) {
        console.log('=== ADD QUICK FILTER DOMAINS ===');
        
        // Date range filter (applies to all models)
        if (this.state.quickFilters.date_range.enabled && 
            this.state.quickFilters.date_range.from && 
            this.state.quickFilters.date_range.to) {
            
            const dateField = this.state.quickFilters.date_range.field || 'create_date';
            const fromDate = this.state.quickFilters.date_range.from;
            const toDate = this.state.quickFilters.date_range.to;
            
            Object.keys(domainsByModel).forEach(modelName => {
                domainsByModel[modelName].push([dateField, '>=', fromDate]);
                domainsByModel[modelName].push([dateField, '<=', toDate]);
            });
            
            console.log(`Added date range filter: ${dateField} >= ${fromDate} AND <= ${toDate}`);
        }
        
        // Active only filter (applies to all models)
        if (this.state.quickFilters.active_only) {
            Object.keys(domainsByModel).forEach(modelName => {
                domainsByModel[modelName].push(['active', '=', true]);
            });
            console.log('Added active_only filter to all models');
        }
        
        // Responsible users filter (model-specific field mapping)
        if (this.state.quickFilters.responsible_users.length > 0) {
            const userIds = this.state.quickFilters.responsible_users.map(u => u.id);
            
            Object.keys(domainsByModel).forEach(modelName => {
                const userField = this.getUserFieldForModel(modelName);
                if (userField) {
                    domainsByModel[modelName].push([userField, 'in', userIds]);
                    console.log(`Added user filter for ${modelName}: ${userField} in [${userIds.join(', ')}]`);
                }
            });
        }
    }
    
    /**
     * NEW - Get user field name for different models
     */
    getUserFieldForModel(modelName) {
        const userFieldMapping = {
            'res.partner': 'user_id',     // Salesperson field
            'crm.lead': 'user_id',        // Salesperson field
            'crm.opportunity': 'user_id'  // Future support
        };
        
        return userFieldMapping[modelName] || 'user_id'; // Default fallback
    }
    
    /**
     * NEW - Add advanced filter rule domains per model
     */
    addAdvancedFilterDomains(domainsByModel) {
        console.log('=== ADD ADVANCED FILTER DOMAINS ===');
        console.log('Advanced rules:', this.state.advancedFilters.rules);
        
        if (!this.state.advancedFilters.enabled || this.state.advancedFilters.rules.length === 0) {
            console.log('No advanced filters to process');
            return;
        }
        
        // Group rules by model
        const rulesByModel = {};
        this.state.advancedFilters.rules.forEach(rule => {
            const modelName = rule.model || this.extractModelFromField(rule.field);
            const originalField = rule.original_field || this.extractOriginalFieldName(rule.field);
            
            if (!rulesByModel[modelName]) {
                rulesByModel[modelName] = [];
            }
            
            // Convert rule to Odoo domain tuple
            const domainTuple = this.convertRuleToDomainTuple(rule, originalField);
            if (domainTuple) {
                rulesByModel[modelName].push(domainTuple);
            }
        });
        
        console.log('Rules grouped by model:', rulesByModel);
        
        // Add rules to each model's domain
        Object.keys(rulesByModel).forEach(modelName => {
            if (domainsByModel[modelName]) {
                const modelRules = rulesByModel[modelName];
                
                if (modelRules.length === 1) {
                    // Single rule - add directly
                    domainsByModel[modelName].push(modelRules[0]);
                } else if (modelRules.length > 1) {
                    // Multiple rules - combine with logic operator
                    if (this.state.advancedFilters.logic === 'OR') {
                        // OR logic: ['|', rule1, rule2]
                        domainsByModel[modelName].push('|');
                        modelRules.forEach(rule => {
                            domainsByModel[modelName].push(rule);
                        });
                    } else {
                        // AND logic (default) - add each rule separately
                        modelRules.forEach(rule => {
                            domainsByModel[modelName].push(rule);
                        });
                    }
                }
                
                console.log(`Added ${modelRules.length} advanced rules to ${modelName}`);
            }
        });
    }
    
    /**
     * NEW - Convert a filter rule to Odoo domain tuple
     */
    convertRuleToDomainTuple(rule, fieldName) {
        console.log('=== CONVERT RULE TO DOMAIN ===');
        console.log('Rule:', rule);
        console.log('Field name:', fieldName);
        
        try {
            let value = rule.value;
            
            // Convert value based on field type
            switch (rule.field_type) {
                case 'boolean':
                    value = value === 'true' || value === true;
                    break;
                    
                case 'integer':
                    value = parseInt(value, 10);
                    if (isNaN(value)) {
                        console.warn('Invalid integer value:', rule.value);
                        return null;
                    }
                    break;
                    
                case 'float':
                case 'monetary':
                    value = parseFloat(value);
                    if (isNaN(value)) {
                        console.warn('Invalid float value:', rule.value);
                        return null;
                    }
                    break;
                    
                case 'many2one':
                    // Try to parse as integer ID, fallback to string for name search
                    const intValue = parseInt(value, 10);
                    if (!isNaN(intValue) && rule.operator === '=') {
                        value = intValue;
                    }
                    // Otherwise keep as string for name-based operators like 'ilike'
                    break;
                    
                case 'many2many':
                case 'one2many':
                    // Handle list values
                    if (rule.operator === 'in' || rule.operator === 'not in') {
                        if (typeof value === 'string') {
                            // Split comma-separated values and convert to integers if possible
                            value = value.split(',').map(v => {
                                const trimmed = v.trim();
                                const intVal = parseInt(trimmed, 10);
                                return isNaN(intVal) ? trimmed : intVal;
                            });
                        }
                    }
                    break;
                    
                case 'char':
                case 'text':
                default:
                    // Keep as string
                    break;
            }
            
            const domainTuple = [fieldName, rule.operator, value];
            console.log('Generated domain tuple:', domainTuple);
            
            return domainTuple;
            
        } catch (error) {
            console.error('Error converting rule to domain:', error, rule);
            return null;
        }
    }
    
    /**
     * NEW - Get human-readable domain preview for debugging/testing
     */
    getDomainPreview() {
        const domains = this.generateOdooDomainsPerModel();
        const preview = {};
        
        Object.keys(domains).forEach(modelName => {
            const sourceName = this.selectedSources.find(s => s.model_name === modelName)?.name || modelName;
            preview[sourceName] = {
                model: modelName,
                domain: domains[modelName],
                readable: this.formatDomainAsReadable(domains[modelName])
            };
        });
        
        return preview;
    }
    
    /**
     * NEW - Format domain as human-readable text
     */
    formatDomainAsReadable(domain) {
        if (!domain || domain.length === 0) {
            return 'No filters applied';
        }
        
        const conditions = [];
        
        domain.forEach(condition => {
            if (Array.isArray(condition) && condition.length === 3) {
                const [field, operator, value] = condition;
                const readableOperator = this.getReadableOperator(operator);
                const readableValue = this.getReadableValue(value);
                conditions.push(`${field} ${readableOperator} ${readableValue}`);
            }
        });
        
        return conditions.join(' AND ');
    }
    
    /**
     * NEW - Get readable operator text
     */
    getReadableOperator(operator) {
        const operatorMap = {
            '=': 'equals',
            '!=': 'not equals', 
            'ilike': 'contains',
            'not ilike': 'does not contain',
            '>': 'greater than',
            '<': 'less than',
            '>=': 'greater or equal',
            '<=': 'less or equal',
            'in': 'in',
            'not in': 'not in'
        };
        
        return operatorMap[operator] || operator;
    }
    
    /**
     * NEW - Get readable value representation
     */
    getReadableValue(value) {
        if (Array.isArray(value)) {
            return `[${value.join(', ')}]`;
        }
        if (typeof value === 'string') {
            return `"${value}"`;
        }
        return String(value);
    }
    
    /**
     * NEW - Test domain generation and show results in UI
     */
    testDomainGeneration() {
        console.log('=== DOMAIN GENERATION TEST ===');
        
        const filters = this.getCurrentFilters();
        console.log('Current filters:', filters);
        
        const domains = filters.generated_domains;
        console.log('Generated domains by model:', domains);
        
        const preview = this.getDomainPreview();
        console.log('Human-readable preview:', preview);
        
        // Test individual components
        console.log('Quick filters:', filters.quick_filters);
        console.log('Advanced rules:', filters.advanced_filters.rules);
        console.log('Selected models:', filters.selected_models);
        
        // Prepare formatted domains for template display
        const formattedDomains = {};
        Object.keys(domains).forEach(modelName => {
            formattedDomains[modelName] = {
                raw: domains[modelName],
                formatted: JSON.stringify(domains[modelName], null, 2), // Format here instead of template
                count: domains[modelName].length
            };
        });
        
        // Store results in state for display
        this.state.domainTestResults = {
            success: true,
            domains: domains,
            formattedDomains: formattedDomains, // NEW - Pre-formatted for template
            preview: preview,
            filters: filters,
            timestamp: new Date().toLocaleString(),
            totalConditions: Object.values(domains).reduce((sum, domain) => sum + domain.length, 0),
            modelCount: Object.keys(domains).length
        };
        
        console.log('Test results stored in state');
        console.log('Formatted domains:', formattedDomains);
        
        return this.state.domainTestResults;
    }
    
    /**
     * NEW - Clear domain test results
     */
    clearDomainTestResults() {
        console.log('Clearing domain test results');
        this.state.domainTestResults = null;
    }
    
    /**
     * NEW - Extract model name from prefixed field name
     */
    extractModelFromField(fieldName) {
        if (fieldName.includes('.')) {
            return fieldName.split('.')[0];
        }
        return null;
    }
    
    /**
     * NEW - Extract original field name from prefixed field name
     */
    extractOriginalFieldName(fieldName) {
        if (fieldName.includes('.')) {
            return fieldName.split('.').slice(1).join('.');
        }
        return fieldName;
    }
    
    // Keep all other existing methods...
    getDefaultOperator(fieldType) {
        const defaultOperators = {
            'char': 'ilike', 'text': 'ilike', 'integer': '=', 'float': '=',
            'date': '>=', 'datetime': '>=', 'boolean': '=', 'selection': '=',
            'many2one': '=', 'many2many': 'in', 'one2many': 'in'
        };
        return defaultOperators[fieldType] || '=';
    }
    
    getOperatorsForFieldType(fieldType) {
        const operators = {
            'char': [
                { value: 'ilike', label: 'Contains' },
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: 'not ilike', label: 'Does not contain' },
                { value: 'in', label: 'In list' },
                { value: 'not in', label: 'Not in list' }
            ],
            'text': [
                { value: 'ilike', label: 'Contains' },
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: 'not ilike', label: 'Does not contain' }
            ],
            'integer': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: '>', label: 'Greater than' },
                { value: '<', label: 'Less than' },
                { value: '>=', label: 'Greater or equal' },
                { value: '<=', label: 'Less or equal' },
                { value: 'in', label: 'In list' },
                { value: 'not in', label: 'Not in list' }
            ],
            'float': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: '>', label: 'Greater than' },
                { value: '<', label: 'Less than' },
                { value: '>=', label: 'Greater or equal' },
                { value: '<=', label: 'Less or equal' }
            ],
            'monetary': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: '>', label: 'Greater than' },
                { value: '<', label: 'Less than' },
                { value: '>=', label: 'Greater or equal' },
                { value: '<=', label: 'Less or equal' }
            ],
            'date': [
                { value: '=', label: 'On date' },
                { value: '!=', label: 'Not on date' },
                { value: '>', label: 'After' },
                { value: '<', label: 'Before' },
                { value: '>=', label: 'On or after' },
                { value: '<=', label: 'On or before' }
            ],
            'datetime': [
                { value: '=', label: 'At exact time' },
                { value: '!=', label: 'Not at time' },
                { value: '>', label: 'After' },
                { value: '<', label: 'Before' },
                { value: '>=', label: 'On or after' },
                { value: '<=', label: 'On or before' }
            ],
            'boolean': [
                { value: '=', label: 'Is' }
            ],
            'selection': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: 'in', label: 'In list' },
                { value: 'not in', label: 'Not in list' }
            ],
            'many2one': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: 'ilike', label: 'Name contains' },
                { value: 'not ilike', label: 'Name does not contain' },
                { value: 'in', label: 'In list' },
                { value: 'not in', label: 'Not in list' }
            ],
            'many2many': [
                { value: 'in', label: 'Contains any' },
                { value: 'not in', label: 'Does not contain' },
                { value: '=', label: 'Exact match' },
                { value: '!=', label: 'Not exact match' }
            ],
            'one2many': [
                { value: 'in', label: 'Contains' },
                { value: 'not in', label: 'Does not contain' }
            ]
        };
        
        return operators[fieldType] || operators['char'];
    }
    
    // Keep all other methods: onQuickFilterChange, toggleAdvancedFilters, etc.
    onQuickFilterChange(filterType, value) {
        this.state.quickFilters[filterType] = value;
        this.notifyFilterChange();
    }
    
    toggleAdvancedFilters() {
        this.state.showAdvanced = !this.state.showAdvanced;
        this.state.advancedFilters.enabled = this.state.showAdvanced;
        this.notifyFilterChange();
    }
    
    addFilterRule() {
        if (!this.state.newRule.field || !this.state.newRule.operator) {
            return;
        }
        
        const rule = {
            id: Date.now(),
            field: this.state.newRule.field,
            original_field: this.extractOriginalFieldName(this.state.newRule.field),
            operator: this.state.newRule.operator,
            value: this.state.newRule.value,
            field_type: this.state.newRule.field_type,
            model: this.state.newRule.model
        };
        
        this.state.advancedFilters.rules.push(rule);
        
        // Reset form
        this.state.newRule = {
            field: '', operator: '', value: '', field_type: '', model: ''
        };
        
        this.notifyFilterChange();
    }
    
    removeFilterRule(ruleId) {
        const index = this.state.advancedFilters.rules.findIndex(rule => rule.id === ruleId);
        if (index !== -1) {
            this.state.advancedFilters.rules.splice(index, 1);
            this.notifyFilterChange();
        }
    }
    
    notifyFilterChange() {
        const filters = this.getCurrentFilters();
        const validation = this.validateFilters();
        
        this.trigger('filters-changed', {
            filters: filters,
            isValid: validation.isValid,
            errors: validation.errors
        });
    }
    
    validateFilters() {
        const errors = [];
        
        // Validate date range
        if (this.state.quickFilters.date_range.enabled) {
            if (!this.state.quickFilters.date_range.from || !this.state.quickFilters.date_range.to) {
                errors.push("Date range requires both start and end dates");
            }
        }
        
        // Validate advanced rules
        if (this.state.advancedFilters.enabled) {
            this.state.advancedFilters.rules.forEach((rule, index) => {
                if (!rule.value && rule.field_type !== 'boolean') {
                    errors.push(`Rule ${index + 1}: Value is required`);
                }
            });
        }
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }
    
    /**
     * Get field display name
     */
    getFieldDisplayName(fieldName) {
        const field = this.state.availableFields.find(f => f.name === fieldName);
        return field?.string || fieldName;
    }
    
    clearAllFilters() {
        this.state.quickFilters = {
            active_only: true,
            date_range: { enabled: true, from: '2025-01-01', to: '2025-12-31', field: 'create_date' },
            responsible_users: [], tags: [], category_ids: [], country_ids: []
        };
        this.state.advancedFilters = { enabled: false, logic: 'AND', rules: [] };
        this.state.showAdvanced = false;
        this.notifyFilterChange();
    }
}

FilterBuilderComponent.template = 'mailing_list_updater.FilterBuilderTemplate';
FilterBuilderComponent.props = {
    selectedSources: { validate: (value) => Array.isArray(value) },
};

export { FilterBuilderComponent };