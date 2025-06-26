# -*- coding: utf-8 -*-

from odoo import models

class ResPartnerSaleReport(models.TransientModel):
    _name = "res.partner.wizard"
    _description = "Ledger Report Wizard for Res Partner"


    def partner_ledger_report(self):
        active_id = self.env.context.get('active_id')
        self.env['res.partner'].sudo().browse(active_id).action_view_move_line_report()
        

    def currency_partner_ledger_report(self):
        self.env['res.partner'].action_view_move_line_report_currency()
