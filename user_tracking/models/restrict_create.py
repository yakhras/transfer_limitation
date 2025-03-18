from odoo import models, api

# class IrUIView(models.Model):
#     _inherit = "ir.ui.view"

#     @api.model
#     def _apply_ir_rules(self, *args, **kwargs):
#         """Override method to disable 'Create' for specific users in tree views."""
#         res = super()._apply_ir_rules(*args, **kwargs)
        
#         restricted_user_id = 17  # Replace with the user ID you want to restrict

#         if self.env.user.id == restricted_user_id and self.type == "tree":
#             self.write({'create': False})  # Disables the "Create" button in tree views
#         return res




class RestrictCreateView(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def fields_view_get(self, view_id=None, view_type="form", toolbar=False, submenu=False):
        """Override to disable 'Create' in tree views for a specific user."""
        res = super().fields_view_get(view_id, view_type, toolbar, submenu)

        restricted_user_id = 17  # Change this to the user ID to restrict

        if self.env.user.id == restricted_user_id and view_type == "tree":
            # Modify the XML to set create="0"
            doc = self.env["ir.qweb"]._render_xml(res["arch"])
            for tree in doc.findall(".//tree"):
                tree.set("create", "0")
            res["arch"] = self.env["ir.qweb"]._to_string(doc)

        return res
