from odoo import models

class Users(models.Model):
    _inherit = 'res.users'

    def get_partner_ids(self):
        partner_ids = set()

        # Fetch the current user using self.env.user
        current_user = self.env.user

        # Add the bot user's partner ID
        bot_user = self.env['res.users'].sudo().browse(1)
        if not bot_user.active and bot_user.partner_id:
            partner_ids.add(bot_user.partner_id.id)

        # Fetch employees managed by the current user
        employees = self.env['hr.employee'].search([('parent_id.user_id', '=', current_user.id)]).mapped('user_id')
        for emp in employees:
            employee_partners = self.env['res.partner'].search([('user_id', 'in', emp.ids)])
        # manager_users = employees.mapped('user_id')


        # Retrieve partner IDs of the managed employees
        # direct_partners = self.env['res.partner'].search([('user_id', 'in', manager_users.ids)])
        # partner_ids.update(direct_partners)
            partner_ids.update(employee_partners)

        # Add partner IDs of active internal users
        internal_users = self.env['res.users'].search([
            ('active', '=', True),
            ('groups_id', 'in', self.env.ref('base.group_user').id)
        ]).mapped('partner_id.id')
        partner_ids.update(internal_users)

        # Convert the set to a list
        partner_ids = list(partner_ids)

            
        return partner_ids


