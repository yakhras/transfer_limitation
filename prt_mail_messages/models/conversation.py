###################################################################################
#
#    Copyright (C) 2020 Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

from datetime import datetime
from email.utils import getaddresses

import pytz

from odoo import _, api, fields, models
from odoo.tools import html2plaintext

from .common import DEFAULT_MESSAGE_PREVIEW_LENGTH, IMAGE_PLACEHOLDER, MONTHS

# Used to render html field in TreeView
TREE_TEMPLATE = (
    '<table style="width: 100%%; border: none;" title="Conversation">'
    "<tbody>"
    "<tr>"
    '<td style="width: 1%%;"><img class="rounded-circle" '
    'style="height: auto; width: 64px; padding:10px;"'
    ' src="data:image/png;base64, %s" alt="Avatar" '
    'title="%s" width="100" border="0" /></td>'
    '<td style="width: 99%%;">'
    '<table style="width: 100%%; border: none;">'
    "<tbody>"
    "<tr>"
    '<td id="author"><strong>%s</strong> &nbsp; '
    '<span id="subject">%s</span></td>'
    '<td id="date" style="text-align: right;" title="%s">%s</td>'
    "</tr>"
    "<tr>"
    '<td><p id="notifications" style="font-size: x-small;">'
    "<strong>%s</strong></p></td>"
    '<td id="participants" style="text-align: right;">%s</td>'
    "</tr>"
    "</tbody>"
    "</table>"
    "%s"
    "</td>"
    "</tr>"
    "</tbody>"
    "</table>"
)


# -- Sanitize name. In case name contains @. Use to keep html working
def sanitize_name(name):
    return name.split("@")[0] if "@" in name else name


################
# Conversation #
################
class Conversation(models.Model):
    _name = "cetmix.conversation"
    _description = "Conversation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "last_message_post desc, id desc"

    # -- User is a participant by default. Override in case any custom logic is needed
    def _default_participants(self):
        return [(4, self.env.user.partner_id.id)]

    active = fields.Boolean(default=True)
    name = fields.Char(string="Subject", required=True, tracking=True)
    author_id = fields.Many2one(
        string="Author",
        comodel_name="res.partner",
        ondelete="set null",
        default=lambda self: self.env.user.partner_id.id,
    )
    partner_ids = fields.Many2many(
        string="Participants", comodel_name="res.partner", default=_default_participants
    )
    last_message_post = fields.Datetime(string="Last Message")
    last_message_by = fields.Many2one(comodel_name="res.partner", ondelete="set null")
    is_participant = fields.Boolean(
        string="I participate", compute="_compute_is_participant"
    )

    subject_display = fields.Html(compute="_compute_subject_display", compute_sudo=True)
    message_count = fields.Integer(compute="_compute_message_count", compute_sudo=True)
    message_needaction_count = fields.Integer(
        compute="_compute_message_count", compute_sudo=True
    )

    # -- Name get. Currently using it only for Move Wizard!
    def name_get(self):
        if not self._context.get("message_move_wiz", False):
            return super().name_get()
        return [(rec.id, f"{rec.name} - {rec.author_id.name}") for rec in self]

    # -- Count messages. All messages except for notifications are counted
    @api.depends("message_ids")
    def _compute_message_count(self):
        for rec in self:
            message_ids = rec.message_ids.filtered(
                lambda msg: msg.message_type != "notification"
            )
            message_needaction = message_ids.filtered(lambda msg: msg.needaction)
            rec.update(
                {
                    "message_count": len(message_ids),
                    "message_needaction_count": len(message_needaction),
                }
            )

    # -- Get HTML view for Tree View
    @api.depends("name")
    def _compute_subject_display(self):
        # Get preview length. Will use it for message body preview
        ICPSudo = self.env["ir.config_parameter"].sudo()
        body_preview_length = int(
            ICPSudo.get_param(
                "cetmix.messages_easy_text_preview", DEFAULT_MESSAGE_PREVIEW_LENGTH
            )
        )

        # Get current timezone
        tz = self.env.user.tz
        local_tz = pytz.timezone(tz) if tz else pytz.utc
        # Get current time
        now = datetime.now(local_tz)

        # Compose subject
        for rec in self.with_context(bin_size=False):
            # Get message date with timezone
            if rec.last_message_post:
                message_date = pytz.utc.localize(rec.last_message_post).astimezone(
                    local_tz
                )
                # Compose displayed date/time
                days_diff = (now.date() - message_date.date()).days
                if days_diff == 0:
                    date_display = datetime.strftime(message_date, "%H:%M")
                elif days_diff == 1:
                    date_display = "{} {}".format(
                        _("Yesterday"),
                        datetime.strftime(message_date, "%H:%M"),
                    )
                elif now.year == message_date.year:
                    date_display = "{} {}".format(
                        str(message_date.day),
                        _(MONTHS.get(message_date.month)),
                    )
                else:
                    date_display = str(message_date.date())
            else:
                date_display = ""

            # Compose messages count
            message_count = rec.message_count
            # Total messages
            if message_count == 0:
                message_count_text = _("No messages")
            else:
                message_count_text = "{} {}".format(
                    str(message_count),
                    _("message") if message_count == 1 else _("messages"),
                )
                # New messages
                message_needaction_count = rec.message_needaction_count
                if message_needaction_count > 0:
                    message_count_text = "{}, {} {}".format(
                        message_count_text,
                        str(message_needaction_count),
                        _("new"),
                    )

            # Participants
            participant_text = ""
            for participant in rec.partner_ids:
                participant_text = "{} {}".format(
                    participant_text,
                    '<img class="rounded-circle"'
                    ' style="width:24px;max-height:24px;margin:2px;"'
                    ' title="{}" src="data:image/png;base64, {}"/>'.format(
                        sanitize_name(participant.name),
                        participant.image_128.decode("utf-8")
                        if participant.image_128
                        else IMAGE_PLACEHOLDER,
                    ),
                )
            # Compose preview body
            plain_body = ""
            for message in rec.message_ids:
                if message.message_type != "notification":
                    message_body = html2plaintext(message.body)
                    if len(message_body) > body_preview_length:
                        message_body = "%s..." % message_body[:body_preview_length]
                    plain_body = (
                        '<img class="rounded-circle"'
                        ' style="width:16px;max-height:16px;margin:2px;"'
                        ' title="{}" src="data:image/png;base64, {}"/>'
                        ' <span id="text-preview"'
                        ' style="color:#808080;vertical-align:middle;">{}</p>'.format(
                            sanitize_name(message.author_id.name)
                            if message.author_id
                            else "",
                            message.author_avatar.decode("utf-8")
                            if message.author_avatar
                            else IMAGE_PLACEHOLDER,
                            message_body,
                        )
                    )
                    break

            rec.subject_display = TREE_TEMPLATE % (
                rec.author_id.image_128.decode("utf-8")
                if rec.author_id and rec.author_id.image_128
                else IMAGE_PLACEHOLDER,
                sanitize_name(rec.author_id.name) if rec.author_id else "",
                rec.author_id.name if rec.author_id else "",
                rec.name if rec.name else "",
                str(message_date.replace(tzinfo=None)) if rec.last_message_post else "",
                date_display,
                message_count_text,
                participant_text,
                plain_body,
            )

    # -- Move messages
    def move(self):
        self.ensure_one()

        return {
            "name": _("Move messages"),
            "views": [[False, "form"]],
            "res_model": "prt.message.move.wiz",
            "type": "ir.actions.act_window",
            "target": "new",
        }

    # -- Is participant?
    def _compute_is_participant(self):
        my_id = self.env.user.partner_id.id
        for rec in self:
            rec.is_participant = my_id in rec.partner_ids.ids

    # -- Join conversation
    def join(self):
        self.update({"partner_ids": [(4, self.env.user.partner_id.id)]})

    # -- Leave conversation
    def leave(self):
        self.update({"partner_ids": [(3, self.env.user.partner_id.id)]})

    # -- Create
    @api.model
    def create(self, vals):
        # Set current user as author if not defined.
        # Use current date as firs message post
        if not vals.get("author_id", False):
            vals.update({"author_id": self.env.user.partner_id.id})
        res = super(Conversation, self.sudo()).create(vals)
        # Subscribe participants
        res.message_subscribe(partner_ids=res.partner_ids.ids)
        return res

    # -- Write
    # Use 'skip_followers_test=True' in context
    # to skip checking for followers/participants
    def write(self, vals):
        res = super().write(vals)
        only_conversation = self._context.get("only_conversation", False)
        active = vals.get("active")
        if active and not only_conversation:
            for rec in self:
                rec.archive_conversion_message(active)
        if self._context.get("skip_followers_test", False):
            return res
        # Check if participants changed
        for rec in self:
            msg_partner_ids = rec.message_partner_ids.ids
            partner_ids = rec.partner_ids.ids
            # New followers added?
            followers_add = list(
                filter(lambda p: p not in msg_partner_ids, partner_ids)
            )
            if len(followers_add) > 0:
                rec.message_subscribe(partner_ids=followers_add)

            # Existing followers removed?
            followers_remove = list(
                filter(lambda p: p not in partner_ids, msg_partner_ids)
            )
            if len(followers_remove) > 0:
                rec.message_unsubscribe(partner_ids=followers_remove)

        return res

    def archive_conversion_message(self, active_state):
        """Set archive state for related mail messages"""
        msg = self.env["mail.message"].search(
            [
                ("active", "=", not active_state),
                ("model", "=", self._name),
                ("res_id", "=", self.id),
                ("message_type", "!=", "notification"),
            ]
        )
        msg_vals = {"active": active_state}
        if active_state:
            msg_vals.update(delete_uid=False, delete_date=False)
        msg.write(msg_vals)

    # -- Archive/unarchive conversation
    def archive(self):
        for rec in self:
            rec.active = not rec.active

    # -- Search for partners by email.
    @api.model
    def partner_by_email(self, email_addresses):
        """
        Override this method to implement custom search
         (e.g. if using prt_phone_numbers module)
        :param list email_addresses: List of email addresses
        :return: res.partner obj if found.
        Please pay attention to the fact that only
         the first (newest) partner found is returned!
        """
        # Use loop with '=ilike' to resolve MyEmail@GMail.com cases
        for address in email_addresses:
            partner = self.env["res.partner"].search(
                [("email", "=ilike", address)], limit=1, order="id desc"
            )
            if partner:
                return partner
        return False

    @api.model
    def create_new_partner(self, partner_name, email_address):
        """
        Create new partner
        :param str partner_name: partner name from email
        :param str email_address: email address
        :rtype: int
        :return: partner id
        """
        category = self.env.ref("prt_mail_messages.cetmix_conversations_partner_cat")
        return (
            self.env["res.partner"]
            .create(
                {
                    "name": partner_name
                    if partner_name and len(partner_name) > 0
                    else email_address.split("@")[0],
                    "email": email_address,
                    "category_id": [(4, category.id)] if category else False,
                }
            )
            .id
        )

    @api.model
    def get_or_create_partner(self, email):
        """
        Get or create partner id
        :param str email: email address
        :rtype: int
        :return: partner id
        """
        partner_name, email_address = getaddresses([email])[0]
        partner = self.partner_by_email([email_address])
        if partner:
            return partner.id
        return self.create_new_partner(partner_name, email_address)

    @api.model
    def prepare_partner_ids(self, email_list):
        """
        Prepare set of partner ids
        :param list email_list: list of email addresses
        :rtype: set
        :return: set of partner ids
        """
        return (
            {self.get_or_create_partner(email) for email in email_list.split(",")}
            if len(email_list) > 0
            else set()
        )

    # -- Parse incoming email
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        custom_values = {} if custom_values is None else custom_values
        partner_ids = set()

        # 1. Check for author. If does not exist create new partner.
        author_id = msg_dict.get("author_id")
        if not author_id:
            email_from = msg_dict.get("email_from", False)
            author_id = self.get_or_create_partner(email_from)
            # Update message author
            msg_dict.update({"author_id": author_id})

        # Append author to participants (partners)
        partner_ids.add(author_id)

        # To
        partner_ids |= self.prepare_partner_ids(msg_dict.get("to", False))
        # Cc
        partner_ids |= self.prepare_partner_ids(msg_dict.get("cc", False))

        # Update custom values
        custom_values.update(
            {
                "name": msg_dict.get("subject", "").strip(),
                "author_id": author_id,
                "partner_ids": [(4, pid) for pid in partner_ids],
            }
        )
        return super(
            Conversation, self.with_context(mail_create_nolog=True)
        ).message_new(msg_dict, custom_values)
