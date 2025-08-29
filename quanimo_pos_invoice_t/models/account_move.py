# -*- coding: utf-8 -*-

from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id and self.partner_id.property_is_printed_invoice:
            result = {
                'einvoice_state': False,
                'spending_unit_vat': False,
                'einvoice_profile': False,
                'einvoice_postbox_id': False,
                'invoice_delivery_type': 'printed'
            }
            self.update(result)
            self._onchange_journal()
            return {
                'value': result
            }
        else:
            result = {
                'einvoice_state': 'draft',
                'spending_unit_vat': False,
                'einvoice_profile': False,
                'einvoice_postbox_id': False,
                'invoice_delivery_type': False
            }
            self.update(result)
            self._onchange_journal()
            return {
                'value': result
            }
            # return super(AccountMove, self).onchange_partner()

    @api.model
    def _get_default_delivery_type(self, partner_id=False, company_id=False, move_type=False):
        response = super(AccountMove, self)._get_default_delivery_type(partner_id, company_id, move_type)
        if move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']:
            if partner_id and partner_id.property_is_printed_invoice:
                return 'printed'
        return response
