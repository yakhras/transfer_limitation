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

from odoo.tests import TransactionCase


class TestCxModelReference(TransactionCase):
    """
    TEST 1 : Check 'custom_name' field value
    TEST 2 : Check selection value
    """

    def setUp(self):
        super().setUp()
        self.group_conversation_own_id = self.ref(
            "prt_mail_messages.group_conversation_own"
        )
        self.res_users_model_id = self.ref("base.model_res_users")
        self.test_user = self.env["res.users"].create(
            {
                "name": "Test User #1",
                "login": "test_user",
                "email": "testuser1@example.com",
                "groups_id": [(4, self.ref("base.group_user"))],
            }
        )
        self.cx_model_reference_partner = self.env.ref(
            "prt_mail_messages.cx_model_reference_res_partner"
        )

    # -- TEST 1 : Check 'custom_name' field value
    def test_onchange_ir_model_id_record(self):
        """
        Check 'custom_name' field value
        at change 'ir_model_id' field
        """
        expected_value = "Contact"
        self.assertEqual(
            self.cx_model_reference_partner.custom_name,
            expected_value,
            msg=f"Custom name must be equal to '{expected_value}'",
        )

        self.cx_model_reference_partner.onchange_ir_model_id()

        expected_value = self.env.ref("base.model_res_partner").name
        self.assertEqual(
            self.cx_model_reference_partner.custom_name,
            expected_value,
            msg=f"Custom name must be equal to '{expected_value}'",
        )

        self.cx_model_reference_partner.write({"ir_model_id": self.res_users_model_id})
        self.cx_model_reference_partner.onchange_ir_model_id()

        expected_value = self.env.ref("base.model_res_users").name
        self.assertEqual(
            self.cx_model_reference_partner.custom_name,
            expected_value,
            msg=f"Custom name must be equal to '{expected_value}'",
        )

    # -- TEST 2 : Check selection value
    def test_referenceable_models(self):
        """Check selection value by user"""
        PrtMessageMoveWiz = self.env["prt.message.move.wiz"]

        referable_models_selected = PrtMessageMoveWiz.with_user(
            self.env.user.id
        )._referenceable_models()

        self.assertEqual(
            len(referable_models_selected),
            2,
            msg="Selection item count must be equal to 2",
        )
        res_partner_obj, res_partner_custom_name = referable_models_selected[0]
        (
            cetmix_conversation_obj,
            cetmix_conversation_custom_name,
        ) = referable_models_selected[1]

        self.assertEqual(
            res_partner_obj,
            "res.partner",
            msg="Object name must be equal to 'res.partner'",
        )
        self.assertEqual(
            res_partner_custom_name,
            "Contact",
            msg="Custom name must be equal to 'Contact'",
        )
        self.assertEqual(
            cetmix_conversation_obj,
            "cetmix.conversation",
            msg="Object name must be equal to 'cetmix.conversation'",
        )
        self.assertEqual(
            cetmix_conversation_custom_name,
            "Conversation",
            msg="Custom name must be equal to 'Conversation'",
        )
        referable_models_selected = PrtMessageMoveWiz.with_user(
            self.test_user.id
        )._referenceable_models()

        self.assertEqual(
            len(referable_models_selected),
            1,
            msg="Selection item count must be equal to 1",
        )
        res_partner_obj, res_partner_custom_name = referable_models_selected[0]
        self.assertEqual(
            res_partner_obj,
            "res.partner",
            msg="Object must be equal to 'res.partner'",
        )
        self.assertEqual(
            res_partner_custom_name,
            "Contact",
            msg="Custom name must be equal to 'Contact'",
        )

        self.test_user.write({"groups_id": [(4, self.group_conversation_own_id)]})
        referable_models_selected = PrtMessageMoveWiz.with_user(
            self.test_user
        )._referenceable_models()
        self.assertEqual(
            len(referable_models_selected),
            2,
            msg="Selection item count must be equal to 2",
        )
        res_partner_obj, res_partner_custom_name = referable_models_selected[0]
        (
            cetmix_conversation_obj,
            cetmix_conversation_custom_name,
        ) = referable_models_selected[1]

        self.assertEqual(
            res_partner_obj,
            "res.partner",
            msg="Object name must be equal to 'res.partner'",
        )
        self.assertEqual(
            res_partner_custom_name,
            "Contact",
            msg="Custom name must be equal to 'Contact'",
        )
        self.assertEqual(
            cetmix_conversation_obj,
            "cetmix.conversation",
            msg="Object name must be equal to 'cetmix.conversation'",
        )
        self.assertEqual(
            cetmix_conversation_custom_name,
            "Conversation",
            msg="Custom name must be equal to 'Conversation'",
        )
