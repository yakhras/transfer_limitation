# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
import json




class UserSession(models.Model):
    _name = 'user.session'
    _description = 'User Session Tracking'


    user_id = fields.Many2one('res.users', string="User", required=True)
    login_date = fields.Datetime(string="Login Date")


    
 
    

class ResUsers(models.Model):
    _inherit = 'res.users'

    
    # def write(self, values):
    #     for rec in self:
    #         """ Create a new session record when the login_date is updated """
    #         if 'login_date' in values:
    #             # Call the session creation method when login_date is updated
    #             self.env['user.session'].create({'user_id': rec.id, 'login_date': values['login_date']})
        
    #     # Ensure the normal write process happens
    #     return super(ResUsers, self).write(values)
    

    @api.depends('login_date')
    def _create_session(self):
        for rec in self:
            rec.livechat_username = rec.login_date