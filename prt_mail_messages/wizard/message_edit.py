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

from odoo import api, fields, models


#################
# Edit message #
#################
class MessageEdit(models.TransientModel):
    _name = "cx.message.edit.wiz"
    _description = "Edit Message or Note"

    def _get_message(self):
        if "message_edit_id" in self._context:
            message_id = self._context["message_edit_id"]
        else:
            active_ids = self._context.get("active_ids", False)
            if active_ids:
                message_id = active_ids[0]
            else:
                return False

        # To check direct context value
        if not message_id:
            return False
        return self.env["mail.message"].browse(message_id)

    message_id = fields.Many2one(
        string="Message", comodel_name="mail.message", default=_get_message
    )
    body = fields.Html()
    can_edit = fields.Boolean(compute="_compute_can_edit")

    # -- Get message body
    @api.onchange("message_id")
    def message_change(self):
        self.body = self.message_id.body if self.message_id else False

    # -- Can edit message?
    @api.depends("message_id", "message_id.author_id", "message_id.subtype_id")
    def _compute_can_edit(self):
        for rec in self:
            rec.can_edit = rec.message_id._message_can_edit()

    # -- Save message
    def save(self):
        # To be 10000% sure!)
        if self.message_id and self.can_edit:
            self.message_id.write(
                {
                    "body": self.body,
                    "cx_edit_uid": self.env.user.id,
                    "cx_edit_date": datetime.now(),
                }
            )
