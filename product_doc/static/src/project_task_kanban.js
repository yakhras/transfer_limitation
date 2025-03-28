/** @odoo-module **/

import KanbanColumn from 'web.KanbanColumn';
import KanbanView from 'web.KanbanView';
import viewRegistry from 'web.view_registry';
import KanbanRenderer from 'web.KanbanRenderer';
import viewUtils from 'web.viewUtils';


console.log('start');

const ProjectTaskKanbanColumn = KanbanColumn.extend({
    /**
     * @override
     * @private
     */
    _onDeleteColumn: function (event) {
        if (this.groupedBy === 'stage_id') {
            event.preventDefault();
            this.trigger_up('kanban_column_delete_wizard');
        } else {
            this._super(...arguments);
        }
    },

    /**
     * Open alternative view when editing personal stages.
     *
     * @private
     * @override
     */
    _onEditColumn: function (event) {
        if (this.groupedBy !== 'personal_stage_type_ids') {
            this._super(...arguments);
            return;
        }
        event.preventDefault();
        const context = Object.assign({}, this.getSession().user_context, {
            form_view_ref: 'project.personal_task_type_edit',
        });
        new view_dialogs.FormViewDialog(this, {
            res_model: this.relation,
            res_id: this.id,
            context: context,
            title: _t("Edit Personal Stage"),
            on_saved: this.trigger_up.bind(this, 'reload'),
        }).open();
    },
});
console.log('ProjectTaskKanbanColumn');


const CustomProjectTaskKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanColumn: ProjectTaskKanbanColumn,
    }),

    init: function () {
        this._super.apply(this, arguments);
        this.isProjectManager = false;
    },

    willStart: function () {
        const superPromise = this._super.apply(this, arguments);

        const isProjectManager = this.getSession().user_has_group('project.group_project_user').then((hasGroup) => {
            this.isProjectManager = hasGroup;
            this._setState();
            return Promise.resolve();
        });

        return Promise.all([superPromise, isProjectManager]);
    },

    /**
     * Allows record drag when grouping by `personal_stage_type_ids`
     *
     * @override
     */
    _setState() {
        this._super(...arguments);
        const groupedBy = this.state.groupedBy[0];
        const groupByFieldName = viewUtils.getGroupByField(groupedBy);
        const field = this.state.fields[groupByFieldName] || {};
        const fieldInfo = this.state.fieldsInfo.kanban[groupByFieldName] || {};

        const grouped_by_date = ["date", "datetime"].includes(field.type);
        const grouped_by_m2m = field.type === "many2many";
        const readonly = !!field.readonly || !!fieldInfo.readonly;
        const groupedByPersonalStage = (groupByFieldName === 'personal_stage_type_ids');

        const draggable = !readonly && (!grouped_by_m2m || groupedByPersonalStage) &&
            (!grouped_by_date || fieldInfo.allowGroupRangeValue);

        // When grouping by personal stage we allow any project user to create
        let editable = this.columnOptions.editable;
        let deletable = this.columnOptions.deletable;
        if (['stage_id', 'personal_stage_type_ids'].includes(groupByFieldName)) {
            this.groupedByM2O = groupedByPersonalStage || this.groupedByM2O;
            const allow_crud = this.isProjectManager || groupedByPersonalStage;
            this.createColumnEnabled = editable = deletable = allow_crud;
        }

        Object.assign(this.columnOptions, {
            draggable,
            grouped_by_m2o: this.groupedByM2O,
            editable: editable,
            deletable: deletable,
        });
    }
});
console.log('CustomProjectTaskKanbanRenderer');

const CustomProjectKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Renderer: CustomProjectTaskKanbanRenderer,
    }),
});
console.log('CustomProjectKanbanView');

viewRegistry.add('custom_project_task_kanban', CustomProjectKanbanView);

 console.log('thanks');