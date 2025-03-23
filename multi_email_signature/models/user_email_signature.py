# -*- coding: utf-8 -*-

import ast
import base64
import logging
import threading

from markupsafe import Markup

from odoo import _, api, fields, models, tools, Command, registry, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import email_re

from odoo.tools.misc import clean_context, split_every
_logger = logging.getLogger(__name__)


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
            # new_context = dict(self.env.context)
            # new_context['signature'] = self.email_signature_id.id  # Example value, adjust as needed
            
            # # Assign the new value to the result field
            # self = self.with_context(signature=self.email_signature_id.id)

    def get_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        self.ensure_one()
        results = dict.fromkeys(res_ids, False)
        rendered_values = {}
        mass_mail_mode = self.composition_mode == 'mass_mail'

        # render all template-based value at once
        if mass_mail_mode and self.model:
            rendered_values = self.render_message(res_ids)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and not self.reply_to_force_new:
            records = self.env[self.model].browse(res_ids)
            reply_to_value = records._notify_get_reply_to(default=False)
            # when having no specific reply-to, fetch rendered email_from value
            for res_id, reply_to in reply_to_value.items():
                if not reply_to:
                    reply_to_value[res_id] = rendered_values.get(res_id, {}).get('email_from', False)

        for res_id in res_ids:
            # static wizard (mail.message) values
            mail_values = {
                'subject': self.subject,
                'body': self.body or '',
                'parent_id': self.parent_id and self.parent_id.id,
                'partner_ids': [partner.id for partner in self.partner_ids],
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'author_id': self.author_id.id,
                'signature_id': self.email_signature_id.id,
                'email_from': self.email_from,
                'record_name': self.record_name,
                'reply_to_force_new': self.reply_to_force_new,
                'mail_server_id': self.mail_server_id.id,
                'mail_activity_type_id': self.mail_activity_type_id.id,
            }

            # mass mailing: rendering override wizard static values
            if mass_mail_mode and self.model:
                record = self.env[self.model].browse(res_id)
                mail_values['headers'] = record._notify_email_headers()
                # keep a copy unless specifically requested, reset record name (avoid browsing records)
                mail_values.update(is_notification=not self.auto_delete_message, model=self.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if self.auto_delete or self.template_id.auto_delete:
                    mail_values['auto_delete'] = True
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not self.reply_to_force_new:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if self.reply_to_force_new and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [Command.link(id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.env['ir.attachment'].browse(attach_id).copy({'res_model': self._name, 'res_id': self.id})
                    attachment_ids.append(new_attach_id.id)
                attachment_ids.reverse()
                mail_values['attachment_ids'] = self.env['mail.thread'].with_context(attached_to=record)._message_post_process_attachments(
                    mail_values.pop('attachments', []),
                    attachment_ids,
                    {'model': 'mail.message', 'res_id': 0}
                )['attachment_ids']

            results[res_id] = mail_values

        results = self._process_state(results)
        return results


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'


    
    @api.model
    def _notify_prepare_template_context(self, message, msg_vals, model_description=False, mail_auto_delete=True):
        # compute send user and its related signature
        
        result = self.env['res.users.email.signature'].search([('user_id', '=', self.env.user.id)], limit=1)
        result.result = msg_vals
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