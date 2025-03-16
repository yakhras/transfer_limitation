# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
import json




class UserSession(models.Model):
    _name = 'user.session'
    _description = 'User Session Tracking'


    user_id = fields.Many2one('res.users', string="User", required=True)
    login_date = fields.Datetime(string="Login Date", readonly=True)
    context = fields.Char()

 
class UserSessionline(models.Model):
    _name = 'user.session.line'
    _description = 'User Session Line'

    rec_name = fields.Char()
    model = fields.Char()
    date = fields.Datetime()

    

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
