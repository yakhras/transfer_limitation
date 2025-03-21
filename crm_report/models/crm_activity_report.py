# -*- coding: utf-8 -*-

from odoo import models, fields


class ActivityReport(models.Model):

    _inherit = "crm.activity.report"


    lead_id = fields.Many2one('crm.lead', "Opportunity", readonly=False)
    field = fields.Char('Field', readonly=True)
    value = fields.Char('Value', readonly=True)
    
    
    def _select(self):
        return """
            SELECT
                m.id,
                l.create_date AS lead_create_date,
                l.date_conversion,
                l.date_deadline,
                l.date_closed,
                m.subtype_id,
                m.mail_activity_type_id,
                m.author_id,
                m.date,
                m.body,
                t.field_desc AS field,
                t.new_value_char AS value,
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
    
    def _join(self):
        return """
            JOIN crm_lead AS l ON m.res_id = l.id
            LEFT JOIN mail_tracking_value AS t ON t.mail_message_id = m.id
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
