from odoo import models



class ResUsers(models.Model):
    _inherit = 'res.users'

    def _bot_internal_partner(self):
        """Retrieve partner IDs of the bot user and active internal users."""
        partner_ids = set()

        # Add the bot user's partner ID
        bot_user = self.env['res.users'].sudo().browse(1)
        if not bot_user.active and bot_user.partner_id:
            partner_ids.add(bot_user.partner_id.id)

        # Add partner IDs of active internal users
        internal_users = self.env['res.users'].search([
            ('active', '=', True),
            ('groups_id', 'in', self.env.ref('base.group_user').id)
        ]).mapped('partner_id.id')
        partner_ids.update(internal_users)

        return list(partner_ids)

    def _get_sales_team_partner(self):
        """Retrieve partner IDs from bot user, internal users, and sales teams."""
        partner_ids = set(self._bot_internal_partner())

        # Fetch sales teams managed by the current user
        sales_teams = self.env['crm.team'].search([('user_id', '=', self.env.user.id)])
        for team in sales_teams:
            team_members = team.member_ids
            team_partners = self.env['res.partner'].search([('user_id', 'in', team_members.ids)])
            partner_ids.update(team_partners)

        return list(partner_ids)

    def _get_employee_partner(self):
        """Retrieve partner IDs from bot user, internal users, sales teams, and managed employees."""
        partner_ids = set(self._bot_internal_partner())

        # Fetch employees managed by the current user
        employees = self.env['hr.employee'].search([('coach_id.user_id', '=', self.env.user.id)]).mapped('user_id').ids
        
        # Retrieve partner IDs of the managed employees
        direct_partners = self.env['res.partner'].search([('user_id', 'in', employees)])
        partner_ids.update(direct_partners.ids)

        return list(partner_ids)



