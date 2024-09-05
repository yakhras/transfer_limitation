# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def _visit_count(self):
        for rec in self: 
            rec.visit_count = len(rec.visit_ids)

    visit_count = fields.Integer(compute="_visit_count", readonly=True, string="Visits")
    visit_ids = fields.One2many('visit.visit', 'project_id', string='Project Visits')

    def project_visit_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_visits.visit_visit_action")
        action['domain'] = [('id','in', self.visit_ids.ids)]
        action['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_project_id': self.id
        }
        return action

class ProjectTask(models.Model):
    _inherit = 'project.task'

    def _visit_count(self):
        for rec in self: 
            rec.visit_count = self.env['visit.visit'].search_count([('task_id', '=', rec.id)])

    visit_count = fields.Integer(compute="_visit_count", readonly=True, string="Visits")
    visit_id = fields.Many2one('visit.visit', string='Project Visit')

    def task_visit_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_visits.visit_visit_action")
        action['domain'] = [('task_id','=', self.id)]
        action['context'] = {
            'default_partner_id': self.project_id and self.project_id.partner_id and self.project_id.partner_id.id or False,
            'default_project_id': self.project_id and self.project_id.id or False,
            'default_task_id': self.id,
            'default_sale_id': self.sale_line_id and self.sale_line_id.order_id.id or False
        }
        return action
