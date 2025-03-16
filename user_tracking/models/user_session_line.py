# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import UserError





class UserSessionline(models.Model):
    _name = 'user.session.line'
    _description = 'User Session Line'

    rec_name = fields.Char()
    model = fields.Char()
    date = fields.Datetime()
    session_id = fields.Many2one('user.session', string="Session", required=True, ondelete='cascade')
    res_id = fields.Integer(string="Related Record ID")


    def action_open_related_record(self):
        """ Opens the related record in its form view """
        if self.model and self.res_id:
            return {
                'type': 'ir.actions.act_window',
                'name': self.rec_name,
                'res_model': self.model,
                'res_id': self.res_id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError("No related record found.")
        
