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

    
 
    def create_session(self, user_id, login_date):
        """ Create a new session record for the user. If it is the first login, set stored_login_date """
        session = self.create({
            'user_id': user_id,
            'stored_login_date': login_date,
        })

        # Check if this is the first time the user is logging in (stored_login_date is empty)
        if session.stored_login_date != login_date:
            session.stored_login_date = login_date 

        return session