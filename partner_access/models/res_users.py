from odoo import models

class Users(models.Model):
    _inherit = 'res.users'

    def get_partner_ids(self):
        partner_ids = []

        # Add the bot user's partner ID
        bot_user_id = self.env['res.users'].search([('id', '=', 1), ('active', '=', False)], limit=1)
        if bot_user_id and bot_user_id.partner_id:
            partner_ids.append(bot_user_id.partner_id.id)

        # Add partner IDs of sales team members if the user is a team leader
        sales_teams = self.env['crm.team'].search([('user_id', '=', self.id)])
        for team in sales_teams:
            team_members = team.member_ids
            team_partners = self.env['res.partner'].search([('user_id', 'in', team_members.ids)])
            partner_ids += team_members.mapped('partner_id.id') + team_partners.ids

        # Add partner IDs of active internal users
        internal_users = self.env['res.users'].search([
            ('active', '=', True),
            ('groups_id', 'in', self.env.ref('base.group_user').id)
        ])
        partner_ids += internal_users.mapped('partner_id.id')

            
        return partner_ids
