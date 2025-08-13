/** @odoo-module **/

const { Component, useState } = owl;


class ExecutionComponent extends Component {
    setup() {
        console.log('ExecutionComponent setup');
        // Basic props from parent
        this.selectedMailingList = this.props.selectedMailingList;
        this.selectedSources = this.props.selectedSources || [];
        console.log('selectedsources:', this.selectedSources);
        this.filterCriteria = this.props.filterCriteria || {};
    }

    // Best approach: Single call to handle all sources at once

    async onExecuteClick() {
        console.log("Execute button clicked!");
        
        const selectedSources = this.props.selectedSources || [];
        
        if (selectedSources.length === 0) {
            console.log("No sources selected");
            return;
        }
        
        // Prepare sources data
        const sourcesData = selectedSources.map(source => {
            const modelName = source.model_name || source;
            return {
                model: modelName,
                domain: this.getModelDomain(modelName)
            };
        });
        
        try {
            // Single call to handle all sources
            const result = await this.env.services.orm.call(
                'mailing.list',
                'add_contacts_from_sources',
                [this.props.selectedMailingList.id, sourcesData]
            );
            
            if (result.success) {
                console.log(`Successfully added ${result.added} contacts out of ${result.total_found} found`);
                // Update UI to show success
            } else {
                console.error('Error:', result.error);
            }
        } catch (error) {
            console.error('Failed to add contacts:', error);
        }
    }

    // onExecuteClick() {
    //     console.log("Execute button clicked!");
        
    //     // Get selected source models from props
    //     const selectedSources = this.props.selectedSources || [];
        
    //     if (selectedSources.length === 0) {
    //         console.log("No sources selected");
    //         return;
    //     }
        
    //     // Process each selected source
    //     selectedSources.forEach(source => {
    //         const modelName = source.model_name || source;
    //         console.log(`Processing source: ${modelName}`);
            
    //         // Call appropriate function based on model type
    //         switch(modelName) {
    //             case 'res.partner':
    //                 this.onPartnerClick(modelName);
    //                 break;
    //             case 'crm.lead':
    //                 this.onCrmClick(modelName);
    //                 break;
    //             default:
    //                 console.log(`No handler for model: ${modelName}`);
    //         }
    //     });
    // }

    onPartnerClick(modelName) {
        console.log('Opening tree view for:', modelName);

        const domain = this.getModelDomain(modelName);
        console.log('Domain for model:', domain);

        const action = this.env.services.orm.call(
            modelName, 
            'get_contacts_with_email', 
            [[], domain, this.selectedMailingList.mailing_list_id]
        );
        
    }

    onCrmClick(modelName) {
        console.log('Opening tree view for:', modelName);

        const domain = this.getModelDomain(modelName);
        console.log('Domain for model:', domain);

        const action = this.env.services.orm.call(
            modelName, 
            'get_contacts_with_email', 
            [[], domain, this.selectedMailingList.mailing_list_id]
        );
        
    }

    getModelDomain(modelName) {
        // Extract domain from filterCriteria.generated_domains
        if (this.filterCriteria?.generated_domains?.[modelName]) {
            return this.filterCriteria.generated_domains[modelName];
        }
        return [];
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