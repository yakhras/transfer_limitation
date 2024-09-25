# -*- coding: utf-8 -*-

from odoo import fields, models, api
from lxml import etree


        
class ResPartner(models.Model):
    _inherit = 'res.partner'   # Inherit the model

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ResPartner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            root = etree.fromstring(res['arch'])
            root.set('edit', 'true')
            res['arch'] = etree.tostring(root)
        else:
            pass
        return res
    

class AccountMove(models.Model):
    _inherit = 'account.move'   # Inherit the model

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountMove, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            root = etree.fromstring(res['arch'])
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)
        else:
            pass
        return res
    

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'   # Inherit the model

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountMoveLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            root = etree.fromstring(res['arch'])
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)
        else:
            pass
        return res
