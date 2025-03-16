# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
from odoo.exceptions import UserError
import json




class UserSession(models.Model):
    _name = 'user.session'
    _description = 'User Session Tracking'


    user_id = fields.Many2one('res.users', string="User", required=True)
    login_date = fields.Datetime(string="Login Date", readonly=True)
    session_lines = fields.One2many('user.session.line', 'session_id', string="Session Lines")
    context = fields.Char(compute='get_context')

    def get_context(self):
        self.context = self.env.context.get('active_model')



 
class UserSessionline(models.Model):
    _name = 'user.session.line'
    _description = 'User Session Line'

    rec_name = fields.Char()
    model = fields.Char()
    date = fields.Datetime()
    session_id = fields.Many2one('user.session', string="Session", required=True, ondelete='cascade')
    res_id = fields.Integer(string="Related Record ID")


    def action_open_related_record(self):
        """ Opens the related record in its form view """
        if self.model and self.res_id:
            return {
                'type': 'ir.actions.act_window',
                'name': self.rec_name,
                'res_model': self.model,
                'res_id': self.res_id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError("No related record found.")



class ResUsers(models.Model):
    _inherit = 'res.users'

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        uid = super(ResUsers, cls).authenticate(db, login, password, user_agent_env)
        if uid:
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, uid, {})
                user = env['res.users'].browse(uid)
                session = env['user.session'].create({'user_id': user.id, 'login_date': user.login_date})
                # session.context = user

        return uid
    




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
