from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
import json




class UserSession(models.Model):
    _name = 'user.session'
    _description = 'User Session Tracking'


    user_id = fields.Many2one('res.users', string="User", required=True, default=lambda self: self.env.user)
    login_date = fields.Datetime(related='user_id.login_date', string="Login Date")

 
    

class ResUsers(models.Model):
    _inherit = 'res.users'

    
    def write(self, values):
        """ Create a new session record when the login_date is updated """
        if 'login_date' in values:
            # Call the session creation method when login_date is updated
            self.env['user.session'].create(self.id, values['login_date'])
        
        # Ensure the normal write process happens
        return super(ResUsers, self).write(values)