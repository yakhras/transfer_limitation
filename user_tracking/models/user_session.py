from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
import json




class UserSession(models.Model):
    _name = 'user.session'
    _description = 'User Session Tracking'


    user_id = fields.Many2one('res.users', string="User", required=True, default=lambda self: self.env.user)
    login_date = fields.Datetime(string="Login Date")


    def create_session(self, user_id, login_date):
        """ Automatically create a new session record when the user logs in """
        return self.create({
            'user_id': user_id,
            'login_date': login_date,
        })
 
    

class ResUsers(models.Model):
    _inherit = 'res.users'

    
    def write(self, values):
        """ Create a new session record when the login_date is updated without removing old records """
        if 'login_date' in values:
            # Ensure that login_date is set correctly
            login_date = values.get('login_date')

            # Create a session record with the login date
            self.env['user.session'].create_session(self.id, login_date)
        
        # Ensure the normal write process happens
        return super(ResUsers, self).write(values)