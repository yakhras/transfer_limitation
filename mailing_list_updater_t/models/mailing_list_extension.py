# -*- coding: utf-8 -*-

from odoo import models, api


class MailingListExtension(models.Model):
    """
    Extension of the mailing.list model to add updater functionality
    """
    _inherit = 'mailing.list'
    
    
    def action_open_updater(self):
        """
        Open the mailing list updater for this specific mailing list
        Called from the smart button on the mailing list form view
        """
        self.ensure_one()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'mailing_list_updater',
            'name': f'Update Contacts - {self.name}',
            'target': 'current',
            'context': {
                'default_mailing_list_id': self.id,
                'mailing_list_name': self.name,
                'active_id': self.id,
                'active_model': 'mailing.list',
            },
            'res_id': False,
        }