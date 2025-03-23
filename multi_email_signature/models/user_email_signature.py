# -*- coding: utf-8 -*-

import ast
import base64

from markupsafe import Markup

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
    
    @api.onchange('email_signature_id')
    def _onchange_email_signature(self):
        if self.email_signature_id:
            # Fetch user details from the selected signature
            signature_user = self.email_signature_id.user_id
            email = self.email_signature_id.email
            name = signature_user.name if signature_user else ''
            
            # Set email_from in the format "Name" <email>
            self.email_from = f'"{name}" <{email}>'
            new_context = dict(self.env.context)
            new_context['signature'] = self.email_signature_id.id  # Example value, adjust as needed
            
            # Assign the new value to the result field
            self = self.with_context(signature=self.email_signature_id.id)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'


    @api.model
    def _notify_prepare_template_context(self, message, msg_vals, model_description=False, mail_auto_delete=True):
        # compute send user and its related signature
        signature_id = self.env.context.get('signature')
        result = self.env['res.users.email.signature'].search([('user_id', '=', self.env.user.id)], limit=1)
        if result:
            result.write({'result': str(signature_id)})  # Persist value in DB
        signature = ''
        user = self.env.user
        author = message.env['res.partner'].browse(msg_vals.get('author_id')) if msg_vals else message.author_id
        model = msg_vals.get('model') if msg_vals else message.model
        add_sign = msg_vals.get('add_sign') if msg_vals else message.add_sign
        subtype_id = msg_vals.get('subtype_id') if msg_vals else message.subtype_id.id
        message_id = message.id
        record_name = msg_vals.get('record_name') if msg_vals else message.record_name
        author_user = user if user.partner_id == author else author.user_ids[0] if author and author.user_ids else False
        # trying to use user (self.env.user) instead of browing user_ids if he is the author will give a sudo user,

        # Fallback to the default behavior when no email_signature_id is provided
        if author_user:
            user = author_user
            if add_sign:
                signature = user.signature
        elif add_sign and author.name:
            signature = Markup("<p>-- <br/>%s</p>") % author.name

        # company value should fall back on env.company if:
        # - no company_id field on record
        # - company_id field available but not set
        company = self.company_id.sudo() if self and 'company_id' in self and self.company_id else self.env.company
        if company.website:
            website_url = 'http://%s' % company.website if not company.website.lower().startswith(('http:', 'https:')) else company.website
        else:
            website_url = False

        # Retrieve the language in which the template was rendered, in order to render the custom
        # layout in the same language.
        # TDE FIXME: this whole brol should be cleaned !
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= self.env.context.keys():
            template = self.env['mail.template'].browse(self.env.context['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([self.env.context['default_res_id']])[self.env.context['default_res_id']]

        if not model_description and model:
            model_description = self.env['ir.model'].with_context(lang=lang)._get(model).display_name

        tracking = []
        if msg_vals.get('tracking_value_ids', True) if msg_vals else bool(self): # could be tracking
            for tracking_value in self.env['mail.tracking.value'].sudo().search([('mail_message_id', '=', message.id)]):
                groups = tracking_value.field_groups
                if not groups or self.env.is_superuser() or self.user_has_groups(groups):
                    tracking.append((tracking_value.field_desc,
                                    tracking_value.get_old_display_value()[0],
                                    tracking_value.get_new_display_value()[0]))

        is_discussion = subtype_id == self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')

        return {
            'message': message,
            'signature': signature,
            'website_url': website_url,
            'company': company,
            'model_description': model_description,
            'record': self,
            'record_name': record_name,
            'tracking_values': tracking,
            'is_discussion': is_discussion,
            'subtype': message.subtype_id,
            'lang': lang,
        }