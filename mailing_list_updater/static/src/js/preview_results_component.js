/** @odoo-module **/

const { Component, useState } = owl;

/**
 * Preview Results Component for OWL 1.0 - Minimal version
 */
class PreviewResultsComponent extends Component {
    
    setup() {
        // Basic props from parent
        this.selectedMailingList = this.props.selectedMailingList;
        this.selectedSources = this.props.selectedSources || [];
        this.filterCriteria = this.props.filterCriteria || {};
    }
}

PreviewResultsComponent.template = 'mailing_list_updater.PreviewResultsTemplate';

PreviewResultsComponent.props = {
    selectedMailingList: { validate: (value) => value === null || typeof value === 'object' },
    selectedSources: { validate: (value) => Array.isArray(value) },
    filterCriteria: { validate: (value) => value === null || typeof value === 'object' },
};

export { PreviewResultsComponent };