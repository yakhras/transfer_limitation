# In: models/partner_statement_report.py
from odoo import api, models

class PartnerStatementReport(models.AbstractModel):
    _name = 'report.partner_balance_t.partner_statement_template'
    _description = 'Partner Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Generate report data for partner statement"""
        partners = self.env['res.partner'].browse(docids)
        
        # Process each partner (usually just one)
        statements_data = []
        for partner in partners:
            # Create temporary partner statement instance
            partner_statement = self.env['partner.statement'].create({
                'partner_id': partner.id
            })
            
            # Get complete statement data
            statement_data = partner_statement.get_complete_partner_statement()
            statements_data.append(statement_data)
            
            # Clean up temporary record
            partner_statement.unlink()
        
        return {
            'doc_ids': docids,
            'doc_model': 'res.partner',
            'docs': partners,
            'statement_data': statements_data[0] if statements_data else {},
            'company': self.env.company,
            'time': __import__('time'),
            'datetime': __import__('datetime'),
        }
    