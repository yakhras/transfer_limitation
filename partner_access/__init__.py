# -*- coding: utf-8 -*-

from . import models
from odoo.api import Environment, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    rule = env.ref('base.res_partner_rule_private_employee', raise_if_not_found=False)
    rules = rule or env['ir.rule']
    rules.write({'active': True})
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

