/** @odoo-module **/

const { Component, useState } = owl;


class ExecutionComponent extends Component {
    setup() {
        console.log('ExecutionComponent setup');
        // Basic props from parent
        this.selectedMailingList = this.props.selectedMailingList;
        this.selectedSources = this.props.selectedSources || [];
        this.filterCriteria = this.props.filterCriteria || {};
    }

    async onExecuteClick() {
        console.log("Execute button clicked!");
        
        const selectedSources = this.props.selectedSources || [];
        
        if (selectedSources.length === 0) {
            console.log("No sources selected");
            return;
        }
        
        // Process sources sequentially to avoid race conditions
        for (const source of selectedSources) {
            const modelName = source.model_name || source;
            console.log(`Processing source: ${modelName}`);
            
            try {
                switch(modelName) {
                    case 'res.partner':
                        await this.onPartnerClick(modelName);
                        break;
                    case 'crm.lead':
                        await this.onCrmClick(modelName);
                        break;
                    default:
                        console.log(`No handler for model: ${modelName}`);
                }
            } catch (error) {
                console.error(`Error processing ${modelName}:`, error);
            }
        }
        
        console.log("All sources processed");
    }

    async onPartnerClick(modelName) {
        console.log('Processing partners:', modelName);
        
        const domain = this.getModelDomain(modelName);
        console.log('Domain for model:', domain);
        
        // Use await to ensure completion before moving to next source
        const result = await this.env.services.orm.call(
            modelName, 
            'get_contacts_with_email', 
            [[], domain, this.props.selectedMailingList.id]
        );
        
        console.log('Partners processed:', result);
        return result;
    }

    async onCrmClick(modelName) {
        console.log('Processing CRM leads:', modelName);
        
        const domain = this.getModelDomain(modelName);
        console.log('Domain for model:', domain);
        
        // Use await to ensure completion before moving to next source
        const result = await this.env.services.orm.call(
            modelName, 
            'get_contacts_with_email', 
            [[], domain, this.props.selectedMailingList.id]
        );
        
        console.log('CRM leads processed:', result);
        return result;
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