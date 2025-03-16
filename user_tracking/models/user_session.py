# -*- coding: utf-8 -*-

from odoo import models, fields




class UserSession(models.Model):
    _name = 'user.session'
    _description = 'User Session Tracking'


    user_id = fields.Many2one('res.users', string="User", required=True)
    login_date = fields.Datetime(string="Login Date", readonly=True)
    session_lines = fields.One2many('user.session.line', 'session_id', string="Session Lines")
    context = fields.Char(compute='get_context')

    def get_context(self):
        self.context = self.env.context.get('active_model')
