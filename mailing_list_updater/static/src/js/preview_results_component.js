/** @odoo-module **/

const { Component, useState } = owl;

/**
 * Preview Results Component for OWL 1.0 - Minimal version
 */
class PreviewResultsComponent extends Component {
    
    setup() {
        console.log('PreviewResultsComponent setup');
        // Basic props from parent
        this.selectedMailingList = this.props.selectedMailingList;
        this.selectedSources = this.props.selectedSources || [];
        this.filterCriteria = this.props.filterCriteria || {};
    }

    onPreviewClick() {
        console.log('Preview button clicked!');
        console.log('Selected sources:', this.selectedSources);
        
        if (this.selectedMailingList) {
            // Get the mailing list ID (either id or mailing_list_id)
            const mailingListId = this.selectedMailingList.id || this.selectedMailingList.mailing_list_id;
            
            // Construct the URL with dynamic ID
            const url = `https://test.menagate.com.tr/web#id=${mailingListId}&menu_id=421&action=546&model=mailing.list&view_type=form`;
            
            console.log('Opening mailing list form:', url);
            
            // Open in new tab
            window.open(url, '_blank');
        } else {
            console.log('No mailing list selected');
        }
    }

    onViewClick(modelName) {
        console.log('Opening tree view for:', modelName);

        const domain = this.getModelDomain(modelName);
        console.log('Domain for model:', domain);

        try {
            // Fetch record count
            const recordCount = this.env.services.orm.call(modelName, 'search_count', [domain]);
            console.log(`Record count for ${modelName} with domain:`, recordCount);

            const action = this._rpc({
                model: 'res.partner',
                method: 'get_contacts_with_email',
                args: [domain],  // With rpc, you can pass args directly
            });

            // Open tree view
            this.env.services.action.doAction({
                res_model: modelName,
                type: 'ir.actions.act_window',
                views: [[false, "list"]],
                domain: domain,
                target: 'new'
            });

        } catch (error) {
            console.error('Error fetching record count:', error);
            // Still open the view even if count fails
            this.env.services.action.doAction({
                res_model: modelName,
                type: 'ir.actions.act_window',
                views: [[false, "list"]],
                domain: domain,
                target: 'new'
            });
        }
    }

    getModelDomain(modelName) {
        // Extract domain from filterCriteria.generated_domains
        if (this.filterCriteria?.generated_domains?.[modelName]) {
            return this.filterCriteria.generated_domains[modelName];
        }
        return [];
    }
    
}


PreviewResultsComponent.template = 'mailing_list_updater.PreviewResultsTemplate';

PreviewResultsComponent.props = {
    selectedMailingList: { validate: (value) => value === null || typeof value === 'object' },
    selectedSources: { validate: (value) => Array.isArray(value) },
    filterCriteria: { validate: (value) => value === null || typeof value === 'object' },
};

export { PreviewResultsComponent };