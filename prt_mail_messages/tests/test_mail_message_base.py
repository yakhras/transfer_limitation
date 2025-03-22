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

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailMessageBase(TransactionCase):
    def setUp(self):
        super().setUp()
        group_user_id = self.env.ref("base.group_user").id
        group_conversation_own_id = self.env.ref(
            "prt_mail_messages.group_conversation_own"
        ).id

        self.test_user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Test User #2",
                    "login": "test_user2",
                    "email": "test@example.com",
                    "groups_id": [
                        (4, group_user_id),
                        (4, group_conversation_own_id),
                    ],  # noqa: E501
                }
            )
        )
        self.res_partner_ann = self.env["res.partner"].create(
            {
                "name": "Ann",
                "email": "ann@example.com",
            }
        )

        self.conversation_A = self.env["cetmix.conversation"].create(
            {
                "active": True,
                "name": "Conversation A",
                "partner_ids": [(4, self.test_user.partner_id.id)],
            }
        )

        self.domain_conversation_A = [
            ("model", "=", "cetmix.conversation"),
            ("res_id", "=", self.conversation_A.id),
            ("message_type", "!=", "notification"),
        ]

        for message_count in range(10):
            self.conversation_A.sudo().message_post(
                body=f"Message - {message_count}",
                message_type="email",
            )

        self.messages_available = (
            self.env["mail.message"]
            .with_user(self.test_user)
            .with_context(check_messages_access=False)
            .search(self.domain_conversation_A)
            .ids
        )

        self.message_available_count = len(self.messages_available)

    def test_mail_message_search1(self):
        """Test flow that check correct _search method work"""
        message_ids = (
            self.env["mail.message"]
            .with_context(check_messages_access=True)
            .with_user(self.test_user.id)
            ._search(
                self.domain_conversation_A,
                limit=self.message_available_count / 2,  # noqa: E501
            )  # noqa: E501
        )

        for message_id in message_ids:
            self.assertIn(message_id, self.messages_available)

        last_message_ids = (
            self.env["mail.message"]
            .with_context(check_messages_access=True, last_id=message_ids[-1])
            .with_user(self.test_user.id)
            ._search(
                self.domain_conversation_A,
                limit=self.message_available_count * 2,
                offset=len(message_ids),
            )
        )

        self.assertListEqual(self.messages_available, message_ids + last_message_ids)  # noqa: E501

    def test_mail_message_search2(self):
        """Test flow that check correct _search method work without limit"""
        message_ids = (
            self.env["mail.message"]
            .with_context(check_messages_access=True)
            .with_user(self.test_user.id)
            ._search(self.domain_conversation_A, limit=False)
        )
        self.assertListEqual(self.messages_available, message_ids)

    def test_mail_message_remove_messages_at_unlink_source_record(self):
        """Test flow that check unlink messages at unlink source record"""
        conversation = self.env["cetmix.conversation"].create(
            {"name": "Conversation Test"}
        )
        conversation_messages = self.env["mail.message"].create(
            [
                {
                    "author_id": self.res_partner_ann.id,
                    "body": "Conversation Message #1",
                    "partner_ids": [(4, self.env.user.partner_id.id)],
                    "res_id": conversation.id,
                    "model": conversation._name,
                },
                {
                    "author_id": self.res_partner_ann.id,
                    "body": "Conversation Message #2",
                    "partner_ids": [(4, self.env.user.partner_id.id)],
                    "res_id": conversation.id,
                    "model": conversation._name,
                },
            ]
        )
        message_ids = conversation_messages.ids
        message1 = conversation_messages[0]
        message1.unlink_pro()
        # Verify message is in trash/archived
        archived_message = (
            self.env["mail.message"].with_context(active_test=False).browse(message1.id)
        )
        self.assertTrue(
            archived_message.exists(), "Message should exist in archived state"
        )
        self.assertFalse(archived_message.active, "Message should be archived")
        conversation.unlink()
        messages = (
            self.env["mail.message"]
            .with_context(active_test=True)
            .search([("id", "in", message_ids)])
        )
        self.assertFalse(messages)
