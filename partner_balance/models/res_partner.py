from odoo import api, models



class ResPartner(models.Model):
    _inherit = "res.partner"

    def create(self, vals_list):
        partners = super().create(vals_list)
        # Create corresponding partner.balance records
        balances = [{
            'partner_id': partner.id,
            'balance': 0.0,  # Default balance, adjust as necessary
            'currency_id': partner.currency_id.id,  # Ensure currency is handled
        } for partner in partners]
        self.env['partner.balance'].create(balances)
        return partners

    def write(self, vals):
    # Track changes to balance-related fields
        res = super().write(vals)
        if 'name' in vals or 'currency_id' in vals:
            for partner in self:
                balance = self.env['partner.balance'].search([('partner_id', '=', partner.id)], limit=1)
                if balance:
                    balance.write({
                        'partner_id': partner.id,  # Use the actual partner ID
                        'currency_id': vals.get('currency_id', balance.currency_id.id),  # Update currency if changed
                    })
        return res

    def unlink(self):
        # Remove corresponding partner.balance records
        self.env['partner.balance'].search([('partner_id', 'in', self.ids)]).unlink()
        return super().unlink()
