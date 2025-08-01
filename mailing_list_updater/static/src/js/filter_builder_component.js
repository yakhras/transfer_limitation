/** @odoo-module **/

const { Component, useState } = owl;

/**
 * Filter Builder Component for OWL 1.0 (Fixed for Odoo 15.0)
 * 
 * Allows users to build dynamic filters for contact selection
 * with both quick filters and advanced rule-based filtering.
 */
class FilterBuilderComponent extends Component {
    
    setup() {
        // Services (OWL 1.0 style)
        console.log('=== COMPONENT SETUP ===');
        console.log('Environment:', this.env);
        console.log('Environment services:', this.env.services);
        
        this.rpc = this.env.services.rpc;
        console.log('RPC service initialized:', !!this.rpc);
        console.log('RPC service type:', typeof this.rpc);
        
        // Component state
        this.state = useState({
            // Quick filters
            quickFilters: {
                active_only: true,
                date_range: {
                    enabled: true,  // Always enabled now
                    from: '2024-01-01',
                    to: '2024-12-31',
                    field: 'create_date'
                },
                responsible_users: [],  // Array of user objects
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
            
            // Advanced filters
            advancedFilters: {
                enabled: false,
                logic: 'AND', // AND/OR
                rules: []
            },
            
            // Available filter options per model
            filterOptions: {},
            
            // UI state
            isLoading: false,
            showAdvanced: false,
            availableFields: [],
            presetTemplates: [],
            
            // Form state
            newRule: {
                field: '',
                operator: '',
                value: '',
                field_type: ''
            }
        });
        
        console.log('Component state initialized:', this.state);
        
        // Props from parent
        this.selectedSources = this.props.selectedSources || [];
        console.log('Selected sources:', this.selectedSources);
        
        // Debounce timer for user search
        this.searchTimeout = null;
    }
    
    /**
     * OWL 1.0 Lifecycle - Will Start
     * Load available filter options for selected sources
     */
    async willStart() {
        if (!this.selectedSources.length) return;
        
        this.state.isLoading = true;
        
        try {
            // Load filter options for each selected source model
            for (const source of this.selectedSources) {
                const response = await this.rpc({
                    route: `/mailing/update/filters/${source.model_name}`,
                    params: { include_sample_data: true }
                });
                
                if (response.success) {
                    this.state.filterOptions[source.model_name] = response.data;
                }
            }
            
            // Merge available fields from all sources
            this.mergeAvailableFields();
            
            // Load filter templates
            await this.loadFilterTemplates();
            
            // Load initial users (optional - could load default salespeople)
            await this.loadDefaultUsers();
            
        } catch (error) {
            this.trigger('show-error', { 
                message: "Failed to load filter options" 
            });
            console.error("Filter options loading error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * OWL 1.0 Lifecycle - Mounted
     * Setup event listeners for click outside
     */
    mounted() {
        // Close user suggestions when clicking outside
        document.addEventListener('click', this.handleClickOutside.bind(this));
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
     * Handle click outside to close user suggestions
     */
    handleClickOutside(event) {
        const userSearchContainer = event.target.closest('.position-relative');
        if (!userSearchContainer) {
            this.state.userSearch.showSuggestions = false;
        }
    }
    
    /**
     * Load default users (e.g., current user or sales team)
     */
    async loadDefaultUsers() {
        console.log('=== LOAD DEFAULT USERS ===');
        
        try {
            console.log('Attempting to load default users via RPC...');
            
            // First, let's test a simple RPC call
            console.log('Testing basic RPC connectivity...');
            
            const response = await this.rpc({
                model: 'res.users',
                method: 'search_read',
                args: [
                    [['active', '=', true], ['share', '=', false]], // Active internal users
                    ['id', 'name', 'email']
                ],
                kwargs: { limit: 3 }  // Load first 3 users as default
            });
            
            console.log('Default users RPC response:', response);
            console.log('Response type:', typeof response);
            console.log('Is array:', Array.isArray(response));
            
            if (response && response.length) {
                console.log('Loading', response.length, 'default users');
                console.log('Default users data:', response);
                
                this.state.quickFilters.responsible_users = response;
                console.log('Updated responsible_users state:', this.state.quickFilters.responsible_users);
            } else {
                console.log('No default users found or empty response');
            }
        } catch (error) {
            console.error("=== DEFAULT USERS LOAD ERROR ===");
            console.error("Error object:", error);
            console.error("Error message:", error.message);
            console.error("Error stack:", error.stack);
            
            if (error.data) {
                console.error("Error data:", error.data);
            }
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
            
            const rpcParams = {
                model: 'res.users',
                method: 'search_read',
                args: [domain, ['id', 'name', 'email']],
                kwargs: { limit: 10 }
            };
            
            console.log('RPC call parameters:', JSON.stringify(rpcParams, null, 2));
            console.log('RPC service available:', !!this.rpc);
            
            const response = await this.rpc(rpcParams);
            
            console.log('RPC response received:', response);
            console.log('Response type:', typeof response);
            console.log('Response length:', response ? response.length : 'N/A');
            
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
            console.error("Error message:", error.message);
            console.error("Error stack:", error.stack);
            
            if (error.data) {
                console.error("Error data:", error.data);
            }
            
            this.state.userSearch.results = [];
        } finally {
            this.state.userSearch.loading = false;
            console.log('Set loading to false');
            console.log('Final search state:', {
                query: this.state.userSearch.query,
                results: this.state.userSearch.results,
                showSuggestions: this.state.userSearch.showSuggestions,
                loading: this.state.userSearch.loading
            });
        }
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
        console.log('Final user search state:', this.state.userSearch);
        
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
     * Merge available fields from all selected sources
     */
    mergeAvailableFields() {
        const fieldsMap = new Map();
        
        Object.values(this.state.filterOptions).forEach(options => {
            if (options.fields) {
                options.fields.forEach(field => {
                    if (!fieldsMap.has(field.name)) {
                        fieldsMap.set(field.name, field);
                    }
                });
            }
        });
        
        this.state.availableFields = Array.from(fieldsMap.values());
    }
    
    /**
     * Load saved filter templates
     */
    async loadFilterTemplates() {
        try {
            const response = await this.rpc({
                route: "/mailing/templates",
                params: { template_type: 'filter' }
            });
            
            if (response.success) {
                this.state.presetTemplates = response.data.templates;
            }
        } catch (error) {
            console.warn("Could not load filter templates:", error);
        }
    }
    
    /**
     * Handle quick filter changes
     */
    onQuickFilterChange(filterType, value) {
        this.state.quickFilters[filterType] = value;
        this.notifyFilterChange();
    }
    
    /**
     * Handle date range filter changes
     */
    onDateRangeChange(field, value) {
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
     * Toggle advanced filters
     */
    toggleAdvancedFilters() {
        this.state.showAdvanced = !this.state.showAdvanced;
        this.state.advancedFilters.enabled = this.state.showAdvanced;
        this.notifyFilterChange();
    }
    
    /**
     * Handle new rule field selection
     */
    onRuleFieldChange(fieldName) {
        const field = this.state.availableFields.find(f => f.name === fieldName);
        
        this.state.newRule.field = fieldName;
        this.state.newRule.field_type = field?.type || '';
        this.state.newRule.operator = this.getDefaultOperator(field?.type);
        this.state.newRule.value = '';
    }
    
    /**
     * Get default operator for field type
     */
    getDefaultOperator(fieldType) {
        const defaultOperators = {
            'char': 'ilike',
            'text': 'ilike', 
            'integer': '=',
            'float': '=',
            'date': '>=',
            'datetime': '>=',
            'boolean': '=',
            'selection': '=',
            'many2one': '=',
            'many2many': 'in'
        };
        
        return defaultOperators[fieldType] || '=';
    }
    
    /**
     * Get available operators for field type
     */
    getOperatorsForFieldType(fieldType) {
        const operators = {
            'char': [
                { value: 'ilike', label: 'Contains' },
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: 'not ilike', label: 'Does not contain' }
            ],
            'text': [
                { value: 'ilike', label: 'Contains' },
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' }
            ],
            'integer': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: '>', label: 'Greater than' },
                { value: '<', label: 'Less than' },
                { value: '>=', label: 'Greater or equal' },
                { value: '<=', label: 'Less or equal' }
            ],
            'float': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: '>', label: 'Greater than' },
                { value: '<', label: 'Less than' },
                { value: '>=', label: 'Greater or equal' },
                { value: '<=', label: 'Less or equal' }
            ],
            'date': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: '>', label: 'After' },
                { value: '<', label: 'Before' },
                { value: '>=', label: 'After or on' },
                { value: '<=', label: 'Before or on' }
            ],
            'datetime': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' },
                { value: '>', label: 'After' },
                { value: '<', label: 'Before' },
                { value: '>=', label: 'After or on' },
                { value: '<=', label: 'Before or on' }
            ],
            'boolean': [
                { value: '=', label: 'Is' }
            ],
            'selection': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' }
            ],
            'many2one': [
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' }
            ],
            'many2many': [
                { value: 'in', label: 'Contains' },
                { value: 'not in', label: 'Does not contain' }
            ]
        };
        
        return operators[fieldType] || operators['char'];
    }
    
    /**
     * Add new rule to advanced filters
     */
    addFilterRule() {
        if (!this.state.newRule.field || !this.state.newRule.operator) {
            return;
        }
        
        const rule = {
            id: Date.now(), // Simple ID for removal
            field: this.state.newRule.field,
            operator: this.state.newRule.operator,
            value: this.state.newRule.value,
            field_type: this.state.newRule.field_type
        };
        
        this.state.advancedFilters.rules.push(rule);
        
        // Reset form
        this.state.newRule = {
            field: '',
            operator: '',
            value: '',
            field_type: ''
        };
        
        this.notifyFilterChange();
    }
    
    /**
     * Remove filter rule
     */
    removeFilterRule(ruleId) {
        const index = this.state.advancedFilters.rules.findIndex(rule => rule.id === ruleId);
        if (index !== -1) {
            this.state.advancedFilters.rules.splice(index, 1);
            this.notifyFilterChange();
        }
    }
    
    /**
     * Change advanced filter logic (AND/OR)
     */
    changeFilterLogic(logic) {
        this.state.advancedFilters.logic = logic;
        this.notifyFilterChange();
    }
    
    /**
     * Apply filter template
     */
    applyTemplate(template) {
        if (template.quick_filters) {
            Object.assign(this.state.quickFilters, template.quick_filters);
        }
        
        if (template.advanced_filters) {
            Object.assign(this.state.advancedFilters, template.advanced_filters);
            this.state.showAdvanced = true;
        }
        
        this.notifyFilterChange();
    }
    
    /**
     * Clear all filters
     */
    clearAllFilters() {
        // Reset quick filters
        this.state.quickFilters = {
            active_only: true,
            date_range: { enabled: true, from: '2024-01-01', to: '2024-12-31', field: 'create_date' },
            responsible_users: [],
            tags: [],
            category_ids: [],
            country_ids: []
        };
        
        // Reset advanced filters
        this.state.advancedFilters = {
            enabled: false,
            logic: 'AND',
            rules: []
        };
        
        // Reset user search
        this.state.userSearch = {
            query: '',
            results: [],
            showSuggestions: false,
            loading: false
        };
        
        this.state.showAdvanced = false;
        this.notifyFilterChange();
    }
    
    /**
     * Get current filter data
     */
    getCurrentFilters() {
        return {
            quick_filters: {
                ...this.state.quickFilters,
                responsible_users: this.state.quickFilters.responsible_users.map(u => u.id) // Send only IDs
            },
            advanced_filters: this.state.advancedFilters
        };
    }
    
    /**
     * Validate current filters
     */
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
     * Notify parent of filter changes
     */
    notifyFilterChange() {
        const filters = this.getCurrentFilters();
        const validation = this.validateFilters();
        
        this.trigger('filters-changed', {
            filters: filters,
            isValid: validation.isValid,
            errors: validation.errors
        });
    }
    
    /**
     * Get field display name
     */
    getFieldDisplayName(fieldName) {
        const field = this.state.availableFields.find(f => f.name === fieldName);
        return field?.string || fieldName;
    }
    
    /**
     * Format rule display
     */
    formatRuleDisplay(rule) {
        const fieldName = this.getFieldDisplayName(rule.field);
        const operator = this.getOperatorsForFieldType(rule.field_type)
            .find(op => op.value === rule.operator)?.label || rule.operator;
        
        return `${fieldName} ${operator} ${rule.value}`;
    }
}

// OWL 1.0 component registration
FilterBuilderComponent.template = 'mailing_list_updater.FilterBuilderTemplate';
FilterBuilderComponent.props = {
    selectedSources: { validate: (value) => Array.isArray(value) },
};

export { FilterBuilderComponent };