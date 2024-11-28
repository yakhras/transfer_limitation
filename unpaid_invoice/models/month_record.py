from odoo import models, fields

class MonthRecord(models.Model):
    _name = 'month.record'
    _description = 'Month Record'

    name = fields.Char('Month Name', required=True)
    november_total = fields.Monetary(string="January Total", compute="_compute_month_totals", currency_field='currency_id')
    december_total = fields.Monetary(string="February Total", compute="_compute_month_totals", currency_field='currency_id')
    today_total = fields.Monetary(string="March Total", compute="_compute_month_totals", currency_field='currency_id')
    # Add fields for other months similarly...

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    
    def _compute_month_totals(self):
        month_to_date_map = {
            'November': ('2024-11-01', '2024-11-30'),
            'December': ('2024-12-01', '2024-12-31'),
            # Add date ranges for other months...
        }

        for record in self:
            for month, date_range in month_to_date_map.items():
                domain = [
                    ('invoice_date_due', '>=', date_range[0]),
                    ('invoice_date_due', '<=', date_range[1]),
                    ('state', '=', 'posted'),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('payment_state', 'in', ['not_paid', 'partial']),
                    ('line_ids.account_id.code', '=', '120001'),
                    ('amount_residual_signed', '!=', 0),
                ]
                invoices = self.env['account.move'].search(domain)
                total = sum(invoices.mapped('amount_residual_signed'))

                # Assign totals to the corresponding fields
                if month == 'November':
                    record.november_total = total
                elif month == 'December':
                    record.december_total = total
                # Add conditions for other months...