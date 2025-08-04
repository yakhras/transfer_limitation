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
        console.log('Initial selectedSources:', this.selectedSources);
        
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

    // ... (keep all existing methods: loadDefaultUsers, onUserSearch, etc.)
    
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
        // Keep existing implementation
        console.log('Loading default users...');
        try {
            this.state.quickFilters.responsible_users = [
                { id: 1, name: 'John Smith', email: 'john.smith@company.com' },
                { id: 2, name: 'Sarah Johnson', email: 'sarah.johnson@company.com' }
            ];
        } catch (error) {
            console.error('Error loading default users:', error);
        }
    }
    
    // ... (keep all other existing methods)
    
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
     * Get current filter data - UPDATED to include model information
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
            selected_models: this.state.selectedModels // NEW - include selected models
        };
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
        // Keep existing implementation
        const operators = {
            'char': [
                { value: 'ilike', label: 'Contains' },
                { value: '=', label: 'Equals' },
                { value: '!=', label: 'Not equals' }
            ],
            'integer': [
                { value: '=', label: 'Equals' },
                { value: '>', label: 'Greater than' },
                { value: '<', label: 'Less than' }
            ]
            // ... add other types
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
        return { isValid: true, errors: [] }; // Simplified for now
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