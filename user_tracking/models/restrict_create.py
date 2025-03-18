from odoo import models, api

class IrUIView(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def _apply_ir_rules(self, *args, **kwargs):
        """Override method to disable 'Create' for specific users in tree views."""
        res = super()._apply_ir_rules(*args, **kwargs)
        
        restricted_user_id = 17  # Replace with the user ID you want to restrict

        if self.env.user.id == restricted_user_id and self.type == "tree":
            self.write({'create': False})  # Disables the "Create" button in tree views
        return res
