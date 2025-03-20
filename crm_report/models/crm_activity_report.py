# -*- coding: utf-8 -*-

from odoo import models, fields


class ActivityReport(models.Model):

    _inherit = "crm.activity.report"


    lead_id = fields.Many2one('crm.lead', "Opportunity", readonly=False)
    last_stage_update = fields.Datetime(
        string='field_nameLast Stage Update',
        related='lead_id.date_last_stage_update', index=True, store=True, readonly=True)
    
    def _select(self):
        return """
            SELECT
                m.id,
                l.create_date AS lead_create_date,
                l.date_last_stage_update AS last_stage_update,
                l.date_conversion,
                l.date_deadline,
                l.date_closed,
                m.subtype_id,
                m.mail_activity_type_id,
                m.author_id,
                m.date,
                m.body,
                l.id as lead_id,
                l.user_id,
                l.team_id,
                l.country_id,
                l.company_id,
                l.stage_id,
                l.partner_id,
                l.type as lead_type,
                l.active
        """

    def _where(self):
        return """
            WHERE 
                l.date_last_stage_update >= %s
        """ % ('2025-01-01 00:00:00')
    