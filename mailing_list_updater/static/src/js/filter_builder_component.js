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
        this.rpc = this.env.services.rpc;
        
        // Component state
        this.state = useState({
            // Quick filters
            quickFilters: {
                active_only: true,
                date_range: {
                    enabled: false,
                    from: '',
                    to: '',
                    field: 'create_date'
                },
                tags: [],
                category_ids: [],
                country_ids: []
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
        
        // Props from parent
        this.selectedSources = this.props.selectedSources || [];
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
     * Setup date picker components
     */
    mounted() {
        // Initialize date pickers for date range filters
        // This would typically integrate with a date picker library
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
            date_range: { enabled: false, from: '', to: '', field: 'create_date' },
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
        
        this.state.showAdvanced = false;
        this.notifyFilterChange();
    }
    
    /**
     * Get current filter data
     */
    getCurrentFilters() {
        return {
            quick_filters: this.state.quickFilters,
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