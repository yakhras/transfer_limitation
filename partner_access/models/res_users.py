from odoo import models

class Users(models.Model):
    _inherit = 'res.users'

    def get_partner_ids(self):
        partner_ids = set()

        # Add the bot user's partner ID
        bot_user = self.env['res.users'].sudo().browse(1)
        if not bot_user.active and bot_user.partner_id:
            partner_ids.add(bot_user.partner_id.id)

        # Add partner IDs for users managed by the current user
        manager_users = self.env['hr.employee'].search([('parent_id.user_id', '=', self.id)]).mapped('user_id.partner_id.id')
        partner_ids.update(manager_users)

        # Add partner IDs of active internal users
        internal_users = self.env['res.users'].search([
            ('active', '=', True),
            ('groups_id', 'in', self.env.ref('base.group_user').id)
        ]).mapped('partner_id.id')
        partner_ids.update(internal_users)

        # Convert the set to a list
        partner_ids = list(partner_ids)

            
        return partner_ids
