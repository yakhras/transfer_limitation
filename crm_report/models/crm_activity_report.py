# -*- coding: utf-8 -*-

from odoo import models, fields


class ActivityReport(models.Model):

    _inherit = "crm.activity.report"


    lead_id = fields.Many2one('crm.lead', "Opportunity", readonly=False)
    message_type = fields.Many2one('mail.message.message_type', 'Action Type', readonly=True)
    
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
                m.message_type,
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
        # Fetch the IDs of the relevant subtypes (assuming they are defined in 'mail.message.subtype')
        disccusion_subtype = self.env.ref('mail.mt_comment').id
        note_subtype_id = self.env.ref('mail.mt_note').id  # Example: Reference for 'note'
        opportunity_created_subtype_id = self.env.ref('crm.mt_lead_create').id  # Example
        stage_changed_subtype_id = self.env.ref('crm.mt_lead_stage').id  # Example

        return """
            WHERE
                m.model = 'crm.lead'
                AND (
                    m.mail_activity_type_id IS NULL 
                    OR m.subtype_id IN (%s, %s)
                    OR ( m.subtype_id = %s AND m.message_type ='notification')
                    OR ( m.subtype_id = %s AND m.message_type IN ('notification', 'comment'))
                )
                AND m.date > '2025-01-01 00:00:00'
        """ % (disccusion_subtype, opportunity_created_subtype_id,stage_changed_subtype_id, note_subtype_id,)
