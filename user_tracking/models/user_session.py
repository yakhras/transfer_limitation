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

    def get_context(self):
        user_id = self.env.context.get('uid')
        user = self.env['res.users'].browse(user_id)
        self.context = user.login_date
 


class ResUsers(models.Model):
    _inherit = 'res.users'

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        """ Override to link the logged in user's res.partner to website.visitor.
        If both a request-based visitor and a user-based visitor exist we try
        to update them (have same partner_id), and move sub records to the main
        visitor (user one). Purpose is to try to keep a main visitor with as
        much sub-records (tracked pages, leads, ...) as possible. """
        uid = super(ResUsers, cls).authenticate(db, login, password, user_agent_env)
        if uid:
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, uid, {})
                user = env['res.users'].browse(uid)
                session = env['user.session'].create({'user_id': user.id, 'login_date': user.login_date})
                session.context = user

        return uid
