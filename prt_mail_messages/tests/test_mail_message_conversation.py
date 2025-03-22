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

from datetime import timedelta

from odoo import fields
from odoo.tests import common


@common.tagged("post_install", "-at_install")
class TestMailMessageConversation(common.TransactionCase):
    """
    TEST 1 : Unlink all messages from conversation
        [Get conversation messages]
        - count messages is 2
        [Messages move to trash (unlink_pro)]
        - conversation active is False
        - conversation message #1 active is False
        - conversation message #1 delete uid is not empty
        - conversation message #1 delete date is not empty
        - conversation message #2 active is False
        - conversation message #2 delete uid is not empty
        - conversation message #2 delete date is not empty
        [Get conversation messages]
        [Message delete (unlink_pro)]
        - message #1 not found
        - message #2 not found

    TEST 2 : Get (undelete) message from trash
        [Get conversation messages]
        [messages moveto trash]
        - conversation # 1 active is False
        - conversation message #1 active is False
        - conversation message #1 delete uid is not empty
        - conversation message #1 delete date is not empty
        - conversation message #2 active is False
        - conversation message #2 delete uid is not empty
        - conversation message #2 delete date is not empty
        [Message undelete]
        - conversation #1 active is True
        - conversation message #1 active is True
        - conversation message #2 active is True

    TEST 3 : Delete message by cron
        [Set config delete trash days = 1]
        [compute date on three days ago]
        [Create mail message]
        [Start cron unlink function (_unlink_trash_message)]
        [Get message by field 'reply to']
        - message is not found

    TEST 4 : Unlink empty conversation
        [Set config delete trash days = 1]
        [Move to trash conversation message #1 and #2]
        [Unlink messages by cron from trash]
        - conversation not found
    """

    def setUp(self):
        super().setUp()
        ResPartner = self.env["res.partner"]
        self.Users = self.env["res.users"]
        self.CetmixConversation = self.env["cetmix.conversation"]
        self.MailMessage = self.env["mail.message"]

        self.res_users = self.Users.create(
            {
                "name": "Test User #1",
                "login": "test_user",
                "email": "testuser1@example.com",
                "groups_id": [(4, self.ref("base.group_user"))],
            }
        )

        self.cetmix_conversation_1 = self.CetmixConversation.create(
            {
                "active": True,
                "name": "Test Conversation #1",
                "partner_ids": [(4, self.res_users.partner_id.id)],
            }
        )

        self.mail_message_1 = self.MailMessage.with_user(self.env.user.id).create(
            {
                "res_id": self.cetmix_conversation_1.id,
                "model": self.CetmixConversation._name,
                "reply_to": "test.reply@example.com",
                "email_from": "test.from@example.com",
                "body": "Mail message Body #1",
            }
        )

        self.mail_message_2 = self.MailMessage.with_user(self.env.user.id).create(
            {
                "res_id": self.cetmix_conversation_1.id,
                "model": self.CetmixConversation._name,
                "reply_to": "test.reply@example.com",
                "email_from": "test.from@example.com",
                "body": "Mail message Body #2",
            }
        )

        self.res_partner_test = ResPartner.create(
            {
                "name": "Test Partner",
                "email": "test.partner@example.com",
            }
        )

    def _get_messages_by_conversation_id(self, conversation_id):
        return self.MailMessage.with_context(active_test=False).search(
            [
                ("res_id", "=", conversation_id),
                ("message_type", "!=", "notification"),
            ]
        )

    # -- TEST 1 : Unlink all messages from conversation
    def test_unlink_conversation_message(self):
        """Unlink all messages from conversation"""

        # Get conversation messages
        # Messages count: 2
        # Messages move to trash
        # Conversation active: False
        # Message #1 active: False
        # Message #1 Delete UID: False
        # Message #1 Delete Date: False
        # Message #2 active: False
        # Message #2 Delete UID: False
        # Message #2 Delete Date: False
        # Get conversation messages
        # Conversation messages delete
        # Messages #1 count: 0
        # Messages #2 count: 0
        messages = self._get_messages_by_conversation_id(self.cetmix_conversation_1.id)
        messages.unlink_pro()

        self.assertFalse(self.cetmix_conversation_1.active, msg="Active must be False")
        self.assertFalse(self.mail_message_1.active, msg="Active must be False")
        self.assertNotEqual(
            self.mail_message_1.delete_uid, False, msg="Delete UID must not be set"
        )
        self.assertNotEqual(
            self.mail_message_1.delete_date, False, msg="Delete Date must not be set"
        )
        self.assertFalse(self.mail_message_2.active, "Active must be False")
        self.assertNotEqual(
            self.mail_message_2.delete_uid, False, msg="Delete UID must not be set"
        )
        self.assertNotEqual(
            self.mail_message_2.delete_date, False, msg="Delete Date must not be set"
        )
        messages = self._get_messages_by_conversation_id(self.cetmix_conversation_1.id)
        messages.unlink_pro()
        mail_message_1_ids = self.MailMessage.search(
            [("id", "=", self.mail_message_1.id)]
        )
        self.assertEqual(
            len(mail_message_1_ids), 0, msg="Mail Messages #1 count must be equal 0"
        )
        mail_message_2_ids = self.MailMessage.search(
            [("id", "=", self.mail_message_2.id)]
        )
        self.assertEqual(
            len(mail_message_2_ids), 0, msg="Mail Messages #2 count must be equal 0"
        )

    # -- TEST 2 : Get (undelete) message from trash
    def test_undelete_conversation(self):
        """Get (undelete) message from trash"""

        # Get conversation messages
        # Messages move to trash
        # Conversation active: False
        # Message #1 active: False
        # Message #1 Delete UID: user.id
        # Message #1 Delete Date: date
        # Message #2 active: False
        # Message #2 Delete UID: user.id
        # Message #2 Delete Date: date
        # Conversation messages delete
        # Conversation active: True
        # Message #1 active: True
        # Message #2 active: True
        messages = self._get_messages_by_conversation_id(self.cetmix_conversation_1.id)
        messages.unlink_pro()
        self.assertFalse(self.cetmix_conversation_1.active, msg="Active must be False")
        self.assertFalse(self.mail_message_1.active, msg="Active must be False")
        self.assertNotEqual(
            self.mail_message_1.delete_uid,
            False,
            msg="Messages #1 Delete UID must be set",
        )
        self.assertNotEqual(
            self.mail_message_1.delete_date,
            False,
            msg="Message #1 Delete Date must be set",
        )
        self.assertFalse(self.mail_message_2.active, msg="Active must be False")
        self.assertNotEqual(
            self.mail_message_2.delete_uid,
            False,
            msg="Messages #2 Delete UID must be set",
        )
        self.assertNotEqual(
            self.mail_message_2.delete_date,
            False,
            msg="Message #2 Delete Date must be set",
        )
        messages.undelete()
        self.assertTrue(self.cetmix_conversation_1.active, msg="Active must be True")
        self.assertTrue(self.mail_message_1.active, msg="Active must be True")
        self.assertTrue(self.mail_message_2.active, msg="Active must be True")

    # -- TEST 3 : Delete message by cron
    def test_unlink_trash_message(self):
        """Delete message by cron"""

        # Set config delete trash days: 1
        # Compute date on three days ago
        # Create mail message
        # Start cron unlink function (_unlink_trash_message)
        # Get message by field 'reply to'
        # Messages count: 0
        self.env["ir.config_parameter"].sudo().set_param(
            "cetmix.messages_easy_empty_trash", 1
        )
        compute_datetime = fields.Datetime.now() - timedelta(days=3)

        self.MailMessage.sudo().create(
            {
                "reply_to": "test.expl@example.com",
                "email_from": "test.from@example.com",
                "active": False,
                "delete_uid": self.res_users.id,
                "delete_date": compute_datetime,
            }
        )

        self.MailMessage._unlink_trash_message()
        mail_message = self.MailMessage.sudo().search(
            [("reply_to", "=", "test.expl@example.com")]
        )
        self.assertEqual(len(mail_message), 0, msg="Messages count must be equal 0")

    # -- TEST 4 : Unlink empty conversation
    def test_unlink_all_conversation_message(self):
        """Unlink empty conversation"""

        # Set config delete trash days: 1
        # Move to trash conversation message: #1 and #2
        # Unlink messages by cron from trash
        # Conversations count: 0
        self.env["ir.config_parameter"].sudo().set_param(
            "cetmix.messages_easy_empty_trash", 1
        )
        self.mail_message_1.unlink_pro()
        self.mail_message_2.unlink_pro()
        self.MailMessage._unlink_trash_message(
            test_custom_datetime=fields.Datetime.now()
        )
        empty_conversation_1 = self.CetmixConversation.with_context(
            active_test=False
        ).search(
            [
                ("id", "=", self.cetmix_conversation_1.id),
            ]
        )
        self.assertEqual(
            len(empty_conversation_1), 0, msg="Conversations count must be equal 0"
        )

    # TEST - 5 : Get or create new partner by Email
    def test_get_or_create_partner(self):
        """Get or create new partner by Email"""
        CetmixConversation = self.env["cetmix.conversation"]
        email = "Test Partner <test.partner@example.com>"
        partner_id = CetmixConversation.get_or_create_partner(email)
        self.assertEqual(
            self.res_partner_test.id,
            partner_id,
            msg=f"Partner id must be equal {self.res_partner_test.id}",
        )
        empty_partner = self.env["res.partner"].search(
            [("email", "=ilike", "partner.example@example.com")], limit=1
        )
        self.assertEqual(
            empty_partner, self.env["res.partner"], msg="Recordset must be empty"
        )
        created_partner_id = CetmixConversation.get_or_create_partner(
            "Partner Example <partner.example@example.com>"
        )
        partner_id = (
            self.env["res.partner"]
            .search([("email", "=ilike", "partner.example@example.com")], limit=1)
            .id
        )
        self.assertEqual(
            partner_id,
            created_partner_id,
            msg=f"Partner id must br equal {created_partner_id}",
        )
