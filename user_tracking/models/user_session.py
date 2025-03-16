from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
import json




class UserSession(models.Model):
    _name = 'user.session'
    _description = 'User Session Tracking'


    user_id = fields.Many2one('res.users', string="User", required=True, default=lambda self: self.env.user)
    login_date = fields.Datetime(related='user_id.login_date', string="Login Date")