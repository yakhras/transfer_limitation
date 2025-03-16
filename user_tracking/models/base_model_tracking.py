# -*- coding: utf-8 -*-

from odoo import models, api




class BaseModelTracking(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def create(self, vals):
        # Prevent recursion for tracking models
        if self._name in ['user.session', 'user.session.line']:
            return super(BaseModelTracking, self).create(vals)

        records = super(BaseModelTracking, self).create(vals)

        # Get the current user's session
        session = self.env['user.session'].search(
            [('user_id', '=', self.env.uid)], 
            order='login_date desc', limit=1
        )

        if session:
            # Fetch model description from ir.model
            model_description = self.env['ir.model'].search(
                [('model', '=', self._name)], limit=1
            ).name or self._name  # Fallback to technical name if not found

            # Create session lines for all created records
            session_lines = [{
                'session_id': session.id,
                'rec_name': model_description,  # Store model's readable name
                'model': self._name,  # Store technical model name
                'res_id': record.id,
                # 'date': record.create_date,  # Store actual creation date
            } for record in records]

            # Create session lines safely without recursion
            if session_lines:
                self.env['user.session.line'].sudo().create(session_lines)

        return records
    

    @api.model
    def write(self, vals):
        result = super(BaseModelTracking, self).write(vals)

        # Get the current user's session
        session = self.env['user.session'].search([('user_id', '=', self.env.uid)], order='login_date desc', limit=1)

        if session:
            # Fetch model description from ir.model
            model_description = self.env['ir.model'].search([('model', '=', self._name)], limit=1).name or self._name

            # Create session lines for all updated records
            session_lines = [{
                'session_id': session.id,
                'rec_name': model_description,
                'model': self._name,
                'res_id': record.id,
                # 'date': fields.Datetime.now(),
            } for record in self]

            self.env['user.session.line'].create(session_lines)

        return result
