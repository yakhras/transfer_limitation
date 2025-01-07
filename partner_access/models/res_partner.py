# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    users_ids = fields.Many2many('res.users',string='Allow Sales Person')
    
    
    @api.model
    def create(self,vals):
        if not self.env.user.has_group('dev_partner_access.group_partner_access_salesperson'):
            raise ValidationError("You can not create partner !!!")
        partner_ids = super(res_partner,self).create(vals)
        for partner in partner_ids:
            if partner.message_follower_ids:
                for follower in partner.message_follower_ids:
                    follower.unlink()
        return partner_ids
            
    
    @api.model
    def default_get(self, fields_list):
        res = super(res_partner, self).default_get(fields_list)                
        res.update({
            'users_ids': [(6,0,[self.env.user.id])]
            })       
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
