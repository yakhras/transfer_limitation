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

from odoo import api, fields, models


class CxModelReference(models.Model):
    _name = "cx.model.reference"
    _description = "Referable Models"
    _order = "sequence"

    _sql_constraints = [
        ("model_unique", "UNIQUE(ir_model_id)", "Model name must be unique!")
    ]

    sequence = fields.Integer(default=10)
    ir_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Name",
        domain=lambda self: [
            ("id", "not in", self.search([]).mapped("ir_model_id").ids),
            ("transient", "=", False),
        ],
        required=True,
        ondelete="cascade",
    )
    custom_name = fields.Char(string="Label", translate=True, required=True)
    object = fields.Char(related="ir_model_id.model", string="Object")

    @api.onchange("ir_model_id")
    def onchange_ir_model_id(self):
        if self.ir_model_id:
            self.custom_name = self.ir_model_id.name
