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
class TestMessageNotification(TransactionCase):
    """
    TEST 1 : Notify partners on incoming message
        - Set True config parameter 'mail_incoming_smart_notify'
        - Processing incoming message
        - Get sent mail message
        - Mail messages count: 2
        - Mail messages #1 recipients: Partner "Demo Notification Type Email"
        - Mail messages #2 recipients count: 2
        - Mail messages #2 recipients: Bob and Mark
    """

    def setUp(self):
        super().setUp()
        ResPartner = self.env["res.partner"]
        ResUsers = self.env["res.users"].with_context(mail_create_nolog=True)

        self.res_users_internal_user_email = ResUsers.create(
            {
                "name": "Demo Notification Type Email",
                "login": "demo_email",
                "email": "demo.email@example.com",
                "groups_id": [(4, self.ref("base.group_user"))],
                "notification_type": "email",
            }
        )

        self.res_users_internal_user_odoo = ResUsers.create(
            {
                "name": "Demo Notification Type Odoo",
                "login": "demo_odoo",
                "email": "demo.odoo@exmaple.com",
                "groups_id": [(4, self.ref("base.group_user"))],
                "notification_type": "inbox",
            }
        )

        self.res_partner_kate = ResPartner.create(
            {
                "name": "Kate",
                "email": "kate@example.com",
            }
        )
        self.res_partner_ann = ResPartner.create(
            {
                "name": "Ann",
                "email": "ann@example.com",
            }
        )
        self.res_partner_bob = ResPartner.create(
            {
                "name": "Bob",
                "email": "bob@example.com",
            }
        )
        self.res_partner_mark = ResPartner.create(
            {
                "name": "Mark",
                "email": "mark@example.com",
            }
        )

        partner_ids = [
            self.res_partner_kate.id,
            self.res_partner_ann.id,
            self.res_partner_bob.id,
            self.res_partner_mark.id,
            self.res_users_internal_user_email.partner_id.id,
            self.res_users_internal_user_odoo.partner_id.id,
        ]

        self.res_partner_target_record = ResPartner.create(
            {
                "name": "Target",
                "email": "target@example.com",
            }
        )
        self.res_partner_target_record.message_subscribe(partner_ids, [])

        self.message_dict = {
            "message_type": "email",
            "message_id": "<CAFkrrMwZJvtNe6kEM538Xu99TmCn=BgwaLMRMPi+otCSO4G6BQ@mail.example.com>",  # noqa
            "subject": "Test Subject",
            "from": "Mark <mark@example.com>",
            "to": "{} <{}>, {} <{}>".format(
                self.res_partner_kate.name,
                self.res_partner_kate.email,
                self.res_partner_ann.name,
                self.res_partner_ann.email,
            ),
            "cc": "",
            "email_from": "Mark <mark@exmaple.com>",
            "partner_ids": [self.res_partner_kate.id, self.res_partner_ann.id],
            "date": "2022-06-23 16:52:15",
            "internal": False,
            "body": "",
            "attachments": [],
            "author_id": False,
        }

        # Monkey patch to keep sent mails for further check
        def unlink_replacement(self):
            return

        self.env["mail.mail"]._patch_method("unlink", unlink_replacement)

    # -- TEST 1 : Notify partners on incoming message
    def test_message_route_process(self):
        """Notify partners on incoming message"""

        # Set True config parameter 'mail_incoming_smart_notify'
        # Processing incoming message
        # Get sent mail message
        # Mail messages count: 2
        # Mail messages #1 recipients: Partner "Demo Notification Type Email"
        # Mail messages #2 recipients count: 2
        # Mail messages #2 recipients: Bob and Mark
        IrConfig = self.env["ir.config_parameter"].sudo()
        key = "cetmix.mail_incoming_smart_notify"

        IrConfig.set_param(key, True)
        self.assertTrue(IrConfig.get_param(key), msg="Result must be True")

        target = self.res_partner_target_record
        user_id = self.env.user.id
        route = (target._name, target.id, None, user_id, None)
        self.env["mail.thread"]._message_route_process("", self.message_dict, [route])
        mail_ids = self.env["mail.mail"].search(
            [
                ("res_id", "=", target.id),
                ("model", "=", target._name),
            ]
        )
        self.assertEqual(len(mail_ids), 2, msg="Mail Messages count must be equal 2")

        internal_partner_mail = mail_ids.filtered(
            lambda mail: len(mail.recipient_ids) == 1
        )

        self.assertEqual(
            internal_partner_mail.recipient_ids,
            self.res_users_internal_user_email.partner_id,
            msg="Mail recipient must be equal only "
            "internal partner (notification type == Email)",
        )

        partner_mail = mail_ids.filtered(
            lambda mail: mail.id != internal_partner_mail.id
        )

        self.assertEqual(
            len(partner_mail.recipient_ids), 2, msg="Recipients count must be equal 2"
        )

        self.assertNotIn(
            self.res_users_internal_user_email.partner_id.id,
            partner_mail.recipient_ids.ids,
            msg="Message recipients must contain internal partner (odoo)",
        )
        self.assertIn(
            self.res_partner_bob.id,
            partner_mail.recipient_ids.ids,
            msg="Message recipients must contain partner Bob",
        )
        self.assertIn(
            self.res_partner_mark.id,
            partner_mail.recipient_ids.ids,
            msg="Message recipients must contain partner Mark",
        )
