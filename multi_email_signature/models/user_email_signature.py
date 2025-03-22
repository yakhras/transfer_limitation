# -*- coding: utf-8 -*-

from odoo import models, fields


class UserEmailSignature(models.Model):
    _name = 'res.users.email.signature'
    _description = 'User Email Signature'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    email = fields.Char(string='Email Address', required=True)
    signature_name = fields.Char(string='Signature Name', required=True, help='A descriptive name for the signature')
    signature = fields.Html(string='Signature', required=True)


class ResUsers(models.Model):
    _inherit = 'res.users'

    email_signatures = fields.One2many('res.users.email.signature', 'user_id', string='Email Signatures')
    