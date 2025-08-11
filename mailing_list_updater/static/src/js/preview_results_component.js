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
    
        this.env.services.action.doAction({
            res_model: modelName,
            type: 'ir.actions.act_window',
            views: [[false, "list"]],
        });
    }
    
}


PreviewResultsComponent.template = 'mailing_list_updater.PreviewResultsTemplate';

PreviewResultsComponent.props = {
    selectedMailingList: { validate: (value) => value === null || typeof value === 'object' },
    selectedSources: { validate: (value) => Array.isArray(value) },
    filterCriteria: { validate: (value) => value === null || typeof value === 'object' },
};

export { PreviewResultsComponent };