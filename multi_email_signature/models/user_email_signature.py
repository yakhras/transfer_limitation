# -*- coding: utf-8 -*-

import ast
import base64

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError
from odoo.tools import email_re


class UserEmailSignature(models.Model):
    _name = 'res.users.email.signature'
    _description = 'User Email Signature'
    _rec_name = 'email'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    email = fields.Char(string='Email Address', required=True)
    signature_name = fields.Char(string='Signature Name', required=True, help='A descriptive name for the signature')
    signature = fields.Html(string='Signature')
    result = fields.Char(string='Result')


    def name_get(self):
        """Override the name_get method to explicitly return email"""
        result = []
        for record in self:
            name = record.email
            result.append((record.id, name))
        return result
    
class ResUsers(models.Model):
    _inherit = 'res.users'

    email_signatures = fields.One2many('res.users.email.signature', 'user_id', string='Email Signatures')
    

class MailComposeMessageInherited(models.TransientModel):
    _inherit = 'mail.compose.message'


    email_signature_id = fields.Many2one(
        'res.users.email.signature', 
        string='Email Signature', 
        help='Select an email signature to use for this email',
        domain="[('user_id', '=', uid)]"
    )
    