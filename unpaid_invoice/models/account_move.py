from odoo import models, fields, api
from datetime import date
import logging

class AccountMove(models.Model):
    _inherit = 'account.move'

    _logger = logging.getLogger(__name__)

    is_due_and_unpaid = fields.Boolean(
        compute='_compute_due_and_unpaid',
        store=True
    )

    @api.depends('invoice_date_due', 'payment_state')
    def _compute_due_and_unpaid(self):
        unpaid_invoice_model = self.env['unpaid.invoice']
        for move in self:
            # Check if due today and unpaid or partially paid
            move.is_due_and_unpaid = (
                move.invoice_date_due == date.today() and
                move.payment_state in ['not_paid', 'partial'] and
                move.move_type in ['out_invoice', 'out_refund']
            )

            # Trigger creation in unpaid.invoice if condition met
            if move.is_due_and_unpaid:
                existing_unpaid_invoice = unpaid_invoice_model.search([('invoice_id', '=', move.id)], limit=1)
                if not existing_unpaid_invoice:
                    unpaid_invoice_model.create({
                        'invoice_id': move.id,
                        'amount_due': move.amount_residual,
                        'due_date': move.invoice_date_due,
                        'partner_id': move.partner_id.id,
                        'team_id': move.team_id.id,
                        'currency_id': move.currency_id.id,
                    })



    def send_due_invoices_email(self):
        """Send an email template without linking it to a specific record."""
        try:
            # Define the email template
            template_id = self.env.ref('your_module_name.email_template_due_invoices', raise_if_not_found=False)
            if not template_id:
                self._logger.error("Email template 'email_template_due_invoices' not found.")
                return
            
            # Use the template's model, or set a dummy model if needed
            # Set context to bypass requiring a specific record
            mail = self.env['mail.mail'].create({
                'subject': template_id.subject,
                'body_html': template_id.body_html,
                'email_to': 'yaser.akhras@menagate.com.tr',  # Replace with your desired email address
                'email_from': 'yaser.akhras@menagate.com.tr'
            })
            mail.send()
            self._logger.info("Email sent successfully.")
        except Exception as e:
            self._logger.error(f"Failed to send email: {e}")

