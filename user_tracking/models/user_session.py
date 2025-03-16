# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
import json




class UserSession(models.Model):
    _name = 'user.session'
    _description = 'User Session Tracking'


    user_id = fields.Many2one('res.users', string="User", required=True)
    login_date = fields.Datetime(string="Login Date", readonly=True)
    session_lines = fields.One2many('user.session.line', 'session_id', string="Session Lines")
    context = fields.Char()

 
class UserSessionline(models.Model):
    _name = 'user.session.line'
    _description = 'User Session Line'

    rec_name = fields.Char()
    model = fields.Char()
    date = fields.Datetime()
    session_id = fields.Many2one('user.session', string="Session", required=True, ondelete='cascade')



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
                session.context = user

        return uid
    

class ResPartner(models.Model):
    _inherit = 'res.partner'


    def create(self, vals):
        partner = super(ResPartner, self).create(vals)

        model_description = self.env['ir.model'].search([
                ('model', '=', 'res.partner')
            ], limit=1).name  # Get human-readable name


        # Get the current user's session
        session = self.env['user.session'].search([
            ('user_id', '=', self.env.uid)
        ], order='login_date desc', limit=1)

        if session:
            self.env['user.session.line'].create({
                'session_id': session.id,
                'rec_name': partner.name,  # Use partner name as record name
                'model': model_description,
                'date': partner.create_date,
            })

        return partner





class BaseModelTracking(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def create(self, vals):
        records = super(BaseModelTracking, self).create(vals)

        # Get the current user's session
        session = self.env['user.session'].search([
            ('user_id', '=', self.env.uid)
        ], order='login_date desc', limit=1)

        if session:
            # Get the model's human-readable name
            model_description = self.env['ir.model'].search([
                ('model', '=', self._name)
            ], limit=1).name or self._name  # Fallback to technical name if not found

            # Create a session line entry
            session_lines = [{
                'session_id': session.id,
                'rec_name': model_description,  # Store model's readable name
                'model': self._name,  # Store technical model name
                'date': record.create_date,  # Store actual creation date
            } for record in records]

            self.env['user.session.line'].create(session_lines)

        return records