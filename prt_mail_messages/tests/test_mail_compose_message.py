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

from odoo.tests import Form, TransactionCase


class TestMailComposeMessage(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "Partner",
                "email": "partner@example.com",
            }
        )

        self.message = self.env["mail.message"].create(
            {
                "model": "res.partner",
                "res_id": self.partner.id,
                "body": "Message #1",
                "author_id": self.partner.id,
            }
        )

    # -- TEST 1 : Check default signature location
    def test_default_signature_location(self):
        """Check default signature location"""
        MailCompose = self.env["mail.compose.message"]
        ICPSudo = self.env["ir.config_parameter"].sudo()

        ICPSudo.set_param("cetmix.message_signature_location", "a")
        self.assertEqual(
            MailCompose._default_signature_location(),
            "a",
            msg="Default signature location must be equal to 'a' (Message bottom)",
        )
        ICPSudo.set_param("cetmix.message_signature_location", "b")
        self.assertEqual(
            MailCompose._default_signature_location(),
            "b",
            msg="Default signature location must be equal to 'a' (Before quote)",
        )
        ICPSudo.set_param("cetmix.message_signature_location", "n")
        self.assertEqual(
            MailCompose._default_signature_location(),
            "n",
            msg="Default signature location must be equal to 'n' (No signature)",
        )

    def test_compose_wizard_mode(self):
        """Check recipients by wizard_mode value"""
        with Form(
            self.env["mail.compose.message"].with_context(
                **self.message.with_context(wizard_mode="quote").reply_prep_context()
            )
        ) as form:
            self.assertEqual(
                form._values.get("wizard_mode"),
                "quote",
                msg="Wizard mode must be equal to 'quote'",
            )
            partner_ids = form._values.get("partner_ids")[0][2][0]
            self.assertEqual(
                self.partner.id,
                partner_ids,
                msg=f"Recipients must be equal to partner ID #{self.partner.id}",
            )

        with Form(
            self.env["mail.compose.message"].with_context(
                **self.message.with_context(wizard_mode="forward").reply_prep_context()
            )
        ) as form:
            self.assertEqual(
                form._values.get("wizard_mode"),
                "forward",
                msg="Wizard Mode must be equal to 'forward'",
            )
            partner_ids = form._values.get("partner_ids")[0][2]
            self.assertFalse(partner_ids, msg="Recipients must be empty")
