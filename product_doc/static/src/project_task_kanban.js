/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ProjectTaskKanbanColumn } from "@project/views/project_task_kanban_column";
import { viewUtils } from "@web/views/view_utils";


console.log("project_task_kanban.js is executed");
const CustomProjectTaskKanbanRenderer = KanbanRenderer.extend({
    
    
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanColumn: ProjectTaskKanbanColumn,
    }),

    init: function () {
        this._super.apply(this, arguments);
        this.isProjectUser = false;
    },

    willStart: function () {
        const superPromise = this._super.apply(this, arguments);

        // Replace 'project.group_project_manager' with 'project.group_project_user'
        const isProjectUser = this.getSession().user_has_group('project.group_project_user').then((hasGroup) => {
            this.isProjectUser = hasGroup;
            this._setState();
            return Promise.resolve();
        });

        return Promise.all([superPromise, isProjectUser]);
    },

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

        let editable = this.columnOptions.editable;
        let deletable = this.columnOptions.deletable;
        if (['stage_id', 'personal_stage_type_ids'].includes(groupByFieldName)) {
            this.groupedByM2O = groupedByPersonalStage || this.groupedByM2O;
            const allow_crud = this.isProjectUser || groupedByPersonalStage;
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
window.projectTaskKanbanLoaded = true;


// Register the new renderer
export default CustomProjectTaskKanbanRenderer;

console.log(window.projectTaskKanbanLoaded);

