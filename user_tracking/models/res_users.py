# -*- coding: utf-8 -*-

from odoo import models, api




class ResUsers(models.Model):
    _inherit = 'res.users'

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        uid = super(ResUsers, cls).authenticate(db, login, password, user_agent_env)
        if uid:
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, uid, {})
                user = env['res.users'].browse(uid)
                session = env['user.session'].create({'user_id': user.id, 'login_date': user.login_date})
                # session.context = user

        return uid
    