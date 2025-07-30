/** @odoo-module **/

const { Component, useState } = owl;

class SourceSelectorComponent extends Component {

    setup() {
        this.rpc = this.env.services.rpc;

        this.state = useState({
            availableSources: [],
            filteredSources: [],
            selectedSources: [], // ✅ Array instead of Set
            isLoading: false,
            searchTerm: '',
            showSourceDetails: {},
        });

        this.selectedMailingList = this.props.selectedMailingList;
    }

    async willStart() {
        this.state.isLoading = true;
        try {
            let response;
            try {
                response = await this.rpc({
                    route: "/mailing/update/sources",
                    params: {
                        company_id: this.selectedMailingList?.company_id || null
                    }
                });
            } catch {
                response = {
                    success: true,
                    data: {
                        sources: [
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
                            },
                            {
                                model_name: 'hr.employee',
                                name: 'Employees',
                                description: 'Import contacts from HR Employees',
                                available: true,
                                recommended: false,
                                estimated_count: 42,
                                email_field: 'work_email',
                                name_field: 'name',
                                phone_field: 'work_phone',
                                company_field: 'company_id'
                            }
                        ]
                    }
                };
            }

            if (response.success) {
                this.state.availableSources = response.data.sources;
                this.updateFilteredSources();
                this.preSelectRecommended();
            } else {
                this.trigger('show-error', { message: response.error?.message || "Failed to load sources" });
            }
        } catch (error) {
            this.trigger('show-error', { message: "Error loading contact sources" });
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

    getSelectedSourcesData() {
        return this.state.availableSources.filter(source =>
            this.state.selectedSources.includes(source.model_name)
        );
    }

    notifyParentOfSelection() {
        const selectedData = this.getSelectedSourcesData();
        this.trigger('sources-changed', {
            selectedSources: this.state.selectedSources,
            selectedSourcesData: selectedData,
            isValid: selectedData.length > 0,
        });
    }

    getSourceItemClass(source) {
        let classes = ['source-item'];
        if (this.isSourceSelected(source.model_name)) classes.push('selected');
        if (!source.available) classes.push('unavailable');
        if (source.recommended) classes.push('recommended');
        return classes.join(' ');
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
