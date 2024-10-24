/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { ListController } from '@web/views/list/list_controller';
import { registry } from '@web/core/registry';

class ExportPdfButtonListController extends ListController {
    setup() {
        super.setup();
        const actionService = useService('action');
        const { doAction } = actionService;

        this.addExportPdfButton();
    }

    addExportPdfButton() {
        if (this.modelName === 'partner.balance') {
            const exportPdfButton = {
                type: 'button',
                text: 'Export to PDF',
                class: 'btn btn-primary',
                icon: 'fa fa-file-pdf-o',
                handler: () => {
                    const context = {
                        active_model: this.modelName,
                        active_ids: this.model.localIds,
                    };
                    doAction({
                        name: 'Export to PDF',
                        type: 'ir.actions.report',
                        report_type: 'qweb-pdf',
                        report_name: 'partner_balance.partner_balance_tree_report_template',
                        context,
                    });
                },
            };

            this.actionButtons.push(exportPdfButton);
        }
    }
}

registry.category('view.controllers').add('partner_balance_tree', ExportPdfButtonListController);
