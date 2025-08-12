/** @odoo-module **/

const { Component, useState } = owl;

/**
 * Progress Tracker Component for OWL 1.0 (Fixed for Odoo 15.0)
 * 
 * Displays real-time progress updates during mailing list batch execution
 * with WebSocket integration and fallback mechanisms.
 */
class ExecutionComponent extends Component {
    setup() {
        console.log('ExecutionComponent setup');
        // Basic props from parent
        this.selectedMailingList = this.props.selectedMailingList;
        console.log('Selected mailing list:', this.selectedMailingList);
        this.selectedSources = this.props.selectedSources || [];
        this.filterCriteria = this.props.filterCriteria || {};
    }
}
    


// OWL 1.0 component registration
ExecutionComponent .template = 'mailing_list_updater.ExecutionStepTemplate';
ExecutionComponent .props = {
    selectedMailingList: { validate: (value) => value === null || typeof value === 'object' },
    selectedSources: { validate: (value) => Array.isArray(value) },
    filterCriteria: { validate: (value) => value === null || typeof value === 'object' },
};


export { ExecutionComponent  };