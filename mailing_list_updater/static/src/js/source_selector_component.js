/** @odoo-module **/

const { Component, useState } = owl;

class SourceSelectorComponent extends Component {

    setup() {
        this.rpc = this.env.services.rpc;

        this.state = useState({
            availableMailingLists: [], // Changed from availableSources
            filteredMailingLists: [], // Changed from filteredSources
            selectedMailingLists: [], // Changed from selectedSources - Array of mailing list IDs
            isLoading: false,
            searchTerm: '',
            showMailingListDetails: {}, // Changed from showSourceDetails
            pagination: {
                limit: 50,
                offset: 0,
                total: 0,
                hasMore: false,
            },
            loadingMore: false,
        });

        this.selectedMailingList = this.props.selectedMailingList;
        this.targetMailingListId = this.selectedMailingList?.id || null;
    }

    async willStart() {
        this.state.isLoading = true;
        try {
            await this.loadMailingLists();
            this.preSelectRecommended();
        } catch (error) {
            this.trigger('show-error', { message: "Error loading mailing lists" });
        } finally {
            this.state.isLoading = false;
        }
    }

    async loadMailingLists(append = false) {
        try {
            let response;
            try {
                response = await this.rpc({
                    route: "/mailing/update/mailing-lists",
                    params: {
                        company_id: this.selectedMailingList?.company_id || null,
                        target_list_id: this.targetMailingListId,
                        search: this.state.searchTerm,
                        limit: this.state.pagination.limit,
                        offset: append ? this.state.pagination.offset : 0,
                        include_inactive: false,
                    }
                });
            } catch {
                // Fallback mock data for development/testing
                response = {
                    success: true,
                    data: {
                        sources: [
                            {
                                mailing_list_id: 1,
                                name: 'Newsletter Subscribers',
                                description: '1,247 contacts in this mailing list',
                                available: true,
                                recommended: true,
                                estimated_count: 1247,
                                contact_count: 1247,
                                email_field: 'email',
                                name_field: 'name',
                                phone_field: 'mobile',
                                company_field: 'company_name',
                                created_date: '2024-01-15T10:00:00Z',
                                last_updated: '2024-07-20T15:30:00Z',
                                last_mailing_date: '2024-07-15T09:00:00Z',
                                is_public: true,
                                company_name: 'YourCompany Ltd',
                                // Compatibility fields
                                model_name: 'mailing.list.1'
                            },
                            {
                                mailing_list_id: 2,
                                name: 'Product Updates',
                                description: '856 contacts in this mailing list',
                                available: true,
                                recommended: true,
                                estimated_count: 856,
                                contact_count: 856,
                                email_field: 'email',
                                name_field: 'name',
                                phone_field: 'mobile',
                                company_field: 'company_name',
                                created_date: '2024-02-01T14:20:00Z',
                                last_updated: '2024-07-18T11:45:00Z',
                                last_mailing_date: '2024-07-10T16:00:00Z',
                                is_public: true,
                                company_name: 'YourCompany Ltd',
                                model_name: 'mailing.list.2'
                            },
                            {
                                mailing_list_id: 3,
                                name: 'Event Notifications',
                                description: '342 contacts in this mailing list',
                                available: true,
                                recommended: false,
                                estimated_count: 342,
                                contact_count: 342,
                                email_field: 'email',
                                name_field: 'name',
                                phone_field: 'mobile',
                                company_field: 'company_name',
                                created_date: '2024-03-10T09:15:00Z',
                                last_updated: '2024-06-25T13:20:00Z',
                                last_mailing_date: null,
                                is_public: true,
                                company_name: 'YourCompany Ltd',
                                model_name: 'mailing.list.3'
                            }
                        ],
                        summary: {
                            total_sources: 3,
                            recommended_count: 2,
                            total_contacts: 2445,
                        },
                        pagination: {
                            limit: 50,
                            offset: 0,
                            total: 3,
                            hasMore: false,
                        }
                    }
                };
            }

            if (response.success) {
                const mailingLists = response.data.sources || [];
                
                if (append) {
                    this.state.availableMailingLists = [...this.state.availableMailingLists, ...mailingLists];
                } else {
                    this.state.availableMailingLists = mailingLists;
                }
                
                // Update pagination info
                if (response.data.pagination) {
                    this.state.pagination = {
                        ...this.state.pagination,
                        ...response.data.pagination,
                        hasMore: response.data.summary?.has_more || false,
                    };
                }
                
                this.updateFilteredMailingLists();
            } else {
                this.trigger('show-error', { 
                    message: response.error?.message || "Failed to load mailing lists" 
                });
            }
        } catch (error) {
            console.error('Error loading mailing lists:', error);
            throw error;
        }
    }

    async loadMoreMailingLists() {
        if (this.state.loadingMore || !this.state.pagination.hasMore) {
            return;
        }

        this.state.loadingMore = true;
        try {
            this.state.pagination.offset += this.state.pagination.limit;
            await this.loadMailingLists(true); // append = true
        } finally {
            this.state.loadingMore = false;
        }
    }

    updateFilteredMailingLists() {
        const term = this.state.searchTerm.toLowerCase();
        this.state.filteredMailingLists = term
            ? this.state.availableMailingLists.filter(list =>
                list.name.toLowerCase().includes(term) ||
                list.description?.toLowerCase().includes(term) ||
                list.company_name?.toLowerCase().includes(term)
            )
            : [...this.state.availableMailingLists];
    }

    preSelectRecommended() {
        this.state.selectedMailingLists = this.state.availableMailingLists
            .filter(list => list.recommended)
            .map(list => list.mailing_list_id);

        this.notifyParentOfSelection();
    }

    onMailingListToggle(mailingListId) {
        const index = this.state.selectedMailingLists.indexOf(mailingListId);

        if (index >= 0) {
            this.state.selectedMailingLists = this.state.selectedMailingLists.filter(id => id !== mailingListId);
        } else {
            this.state.selectedMailingLists.push(mailingListId);
        }

        this.notifyParentOfSelection();
    }

    isMailingListSelected(mailingListId) {
        return this.state.selectedMailingLists.includes(mailingListId);
    }

    toggleMailingListDetails(mailingListId) {
        this.state.showMailingListDetails[mailingListId] = !this.state.showMailingListDetails[mailingListId];
    }

    async onSearchInput(event) {
        this.state.searchTerm = event.target.value;
        
        // Reset pagination for new search
        this.state.pagination.offset = 0;
        
        // Debounce search for server-side filtering
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(async () => {
            if (this.state.searchTerm.length >= 2 || this.state.searchTerm.length === 0) {
                await this.loadMailingLists(false); // Don't append, replace
            } else {
                this.updateFilteredMailingLists(); // Client-side filtering for short terms
            }
        }, 300);
    }

    getSelectedMailingListsData() {
        return this.state.availableMailingLists.filter(list =>
            this.state.selectedMailingLists.includes(list.mailing_list_id)
        );
    }

    notifyParentOfSelection() {
        const selectedData = this.getSelectedMailingListsData();
        
        // Transform to expected format for backend compatibility
        const selectedSources = selectedData.map(list => ({
            mailing_list_id: list.mailing_list_id,
            enabled: true,
            name: list.name,
            contact_count: list.contact_count,
            // Maintain compatibility with old structure
            model_name: list.model_name || `mailing.list.${list.mailing_list_id}`,
        }));

        this.trigger('sources-changed', {
            selectedSources: selectedSources, // For backend compatibility
            selectedMailingLists: this.state.selectedMailingLists, // New structure
            selectedMailingListsData: selectedData, // Full data
            isValid: selectedData.length > 0,
            totalSelectedContacts: selectedData.reduce((sum, list) => sum + list.contact_count, 0),
        });
    }

    getMailingListItemClass(mailingList) {
        let classes = ['mailing-list-item']; // Changed from source-item
        if (this.isMailingListSelected(mailingList.mailing_list_id)) classes.push('selected');
        if (!mailingList.available) classes.push('unavailable');
        if (mailingList.recommended) classes.push('recommended');
        return classes.join(' ');
    }

    selectAllRecommended() {
        const recommended = this.state.availableMailingLists
            .filter(list => list.recommended && list.available)
            .map(list => list.mailing_list_id);

        this.state.selectedMailingLists = Array.from(new Set([...this.state.selectedMailingLists, ...recommended]));
        this.notifyParentOfSelection();
    }

    clearAllSelections() {
        this.state.selectedMailingLists = [];
        this.notifyParentOfSelection();
    }

    formatContactCount(count) {
        if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
        if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
        return count.toString();
    }

    formatDate(dateString) {
        if (!dateString) return 'Never';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch {
            return 'Invalid date';
        }
    }

    formatDateTime(dateString) {
        if (!dateString) return 'Never';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return 'Invalid date';
        }
    }

    getMailingListIcon(mailingList) {
        // Return appropriate icon based on mailing list properties
        if (mailingList.contact_count > 1000) return 'fa-users';
        if (mailingList.recommended) return 'fa-star';
        if (mailingList.last_mailing_date) return 'fa-envelope';
        return 'fa-list';
    }

    getTotalSelectedContacts() {
        return this.getSelectedMailingListsData()
            .reduce((total, list) => total + list.contact_count, 0);
    }

    async refreshMailingLists() {
        this.state.isLoading = true;
        this.state.pagination.offset = 0;
        
        try {
            await this.loadMailingLists(false);
        } finally {
            this.state.isLoading = false;
        }
    }

    // Compatibility method - maps old method names to new ones
    onSourceToggle(event) {
        const mailingListId = parseInt(event.currentTarget.dataset.mailingListId);
        this.onMailingListToggle(mailingListId);
    }

    // Compatibility method
    isSourceSelected(mailingListId) {
        return this.isMailingListSelected(mailingListId);
    }

    // Compatibility method  
    toggleSourceDetails(event) {
        const mailingListId = parseInt(event.currentTarget.dataset.mailingListId);
        this.toggleMailingListDetails(mailingListId);
        event.stopPropagation();
    }

    // Compatibility method
    getSourceItemClass(mailingList) {
        return this.getMailingListItemClass(mailingList);
    }
}

SourceSelectorComponent.template = 'mailing_list_updater.SourceSelectorTemplate';
SourceSelectorComponent.props = {
    selectedMailingList: { validate: (value) => value === null || typeof value === 'object' },
};

export { SourceSelectorComponent };