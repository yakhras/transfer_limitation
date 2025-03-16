# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
import json




class UserSession(models.Model):
    _name = 'user.session'
    _description = 'User Session Tracking'


    user_id = fields.Many2one('res.users', string="User", required=True)
    login_date = fields.Datetime(related='user_id.login_date', string="Login Date")
    stored_login_date = fields.Datetime(string="Stored Login Date", readonly=True)
    context = fields.Char()

    
 
class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """ Capture login event and create session record """
        res = super(ResUsers, self)._auth_oauth_signin(provider, validation, params)


        self.env['user.session'].create({
            'user_id': self.id,
        })
        return res