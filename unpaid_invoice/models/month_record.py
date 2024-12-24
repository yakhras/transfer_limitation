from odoo import models, fields, _
from datetime import date, timedelta


class MonthRecord(models.Model):
    _name = 'month.record'
    _description = 'Month Record'

    name = fields.Char('Month Name', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    today_total = fields.Float(compute="_compute_totals")
    week_total = fields.Float(compute="_compute_totals")
    month_total = fields.Float(compute="_compute_totals")
    other_total = fields.Float(compute="_compute_totals")

    today_immediate = fields.Float(string="Today Immediate", compute="_compute_totals")
    today_transfer = fields.Float(string="Today Transfer", compute="_compute_totals")
    today_check = fields.Float(string="Today Check", compute="_compute_totals")

    this_week_immediate = fields.Float(string="This Week Immediate", compute="_compute_totals")
    this_week_transfer = fields.Float(string="This Week Transfer", compute="_compute_totals")
    this_week_check = fields.Float(string="This Week Check", compute="_compute_totals")

    this_month_immediate = fields.Float(string="This Month Immediate", compute="_compute_totals")
    this_month_transfer = fields.Float(string="This Month Transfer", compute="_compute_totals")
    this_month_check = fields.Float(string="This Month Check", compute="_compute_totals")

    other_immediate = fields.Float(string="Other Immediate", compute="_compute_totals")
    other_transfer = fields.Float(string="Other Transfer", compute="_compute_totals")
    other_check = fields.Float(string="Other Check", compute="_compute_totals")
 

    def _compute_totals(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday() + 2)  # Last Saturday
        week_end = week_start + timedelta(days=6)  # Next Friday
        month_start = today.replace(day=1)
        month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        other_start = today.replace(month=1, day=1)
        other_end = (today.replace(day=1) - timedelta(days=1))

        for record in self:
            record.today_total = self._calculate_total(today, today, None)
            record.week_total = self._calculate_total(week_start, week_end, None)
            record.month_total = self._calculate_total(month_start, month_end, None)
            record.other_total = self._calculate_total(other_start, other_end, None)

            record.today_immediate = self._calculate_total(today, today, 'Immediate')
            record.today_transfer = self._calculate_total(today, today, 'Transfer')
            record.today_check = self._calculate_total(today, today, 'Check')

            record.this_week_immediate = self._calculate_total(week_start, week_end, 'Immediate')
            record.this_week_transfer = self._calculate_total(week_start, week_end, 'Transfer')
            record.this_week_check = self._calculate_total(week_start, week_end, 'Check')

            record.this_month_immediate = self._calculate_total(month_start, month_end, 'Immediate')
            record.this_month_transfer = self._calculate_total(month_start, month_end, 'Transfer')
            record.this_month_check = self._calculate_total(month_start, month_end, 'Check')

            record.other_immediate = self._calculate_total(other_start, other_end, 'Immediate')
            record.other_transfer = self._calculate_total(other_start, other_end, 'Transfer')
            record.other_check = self._calculate_total(other_start, other_end, 'Check')


    def _calculate_total(self, start_date, end_date, term):
        domain = [('invoice_date_due', ">=", start_date),
                  ('invoice_date_due', "<=", end_date),
                ('state', "=", 'posted'),
                ('move_type', "in", ['out_invoice', 'out_refund']),
                ('payment_state', "in", ['not_paid', 'partial']),
                ('line_ids.account_id.code',"=",120001),
                ('amount_residual_signed',"!=",0),
                ]
        if term:
            domain.append(('invoice_payment_term_id.name', "ilike", term))
        res = sum(self.env['account.move'].search(domain).mapped('amount_residual_signed'))
        return res
    

    # def action_saturday_to_friday(self):
    #     today = date.today()
    #     week_start = today - timedelta(days=today.weekday() + 2)  # Previous Saturday
    #     week_end = week_start + timedelta(days=6)  # Following Friday

    #     return {
    #         "name": _("Unpaid Invoice This Week"),
    #         "type": "ir.actions.act_window",
    #         "res_model": "account.move",
    #         "view_mode": "tree",
    #         "view_id": self.env.ref("unpaid_invoice.view_account_move_custom_list").id,
    #         "target": "current",
    #         "domain":[
    #             ('invoice_date_due', '>=', week_start.strftime('%Y-%m-%d')),
    #             ('invoice_date_due', '<=', week_end.strftime('%Y-%m-%d')),
    #             ('state', '=', 'posted'),
    #             ('move_type', 'in', ['out_invoice', 'out_refund']),
    #             ('payment_state', 'in', ['not_paid', 'partial']),
    #             ('line_ids.account_id.code',"=",120001),
    #             ('amount_residual_signed',"!=",0),
    #         ],
    #         "context": {
    #                 'default_move_type':'out_invoice',
    #                 'move_type':'out_invoice',
    #                 'journal_type': 'sale',
    #                 'group_by': ['invoice_user_id','partner_id'],
    #             },
    #         "search_view_id": self.env.ref("account.view_out_invoice_tree").id,
    #     }


    # def action_this_month(self):
    #     today = date.today()
    #     month_start = today.replace(day=1)
    #     month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)

    #     return {
    #         "name": _("Unpaid Invoice This Month"),
    #         "type": "ir.actions.act_window",
    #         "res_model": "account.move",
    #         "view_mode": "tree",
    #         "view_id": self.env.ref("unpaid_invoice.view_account_move_custom_list").id,
    #         "target": "current",
    #         "domain":[
    #             ('invoice_date_due', '>=', month_start.strftime('%Y-%m-%d')),
    #             ('invoice_date_due', '<=', month_end.strftime('%Y-%m-%d')),
    #             ('state', '=', 'posted'),
    #             ('move_type', 'in', ['out_invoice', 'out_refund']),
    #             ('payment_state', 'in', ['not_paid', 'partial']),
    #             ('line_ids.account_id.code',"=",120001),
    #             ('amount_residual_signed',"!=",0),
    #         ],
    #         "context": {
    #                 'default_move_type':'out_invoice',
    #                 'move_type':'out_invoice',
    #                 'journal_type': 'sale',
    #                 'group_by': ['invoice_user_id','partner_id'],
    #             },
    #         "search_view_id": self.env.ref("account.view_out_invoice_tree").id,
    #     }
    
    
    # def action_today(self):
    #     today = date.today()

    #     return {
    #         "name": _("Unpaid Invoice Today"),
    #         "type": "ir.actions.act_window",
    #         "res_model": "account.move",
    #         "view_mode": "tree",
    #         "view_id": self.env.ref("unpaid_invoice.view_account_move_custom_list").id,
    #         "target": "current",
    #         "domain":[
    #             ('invoice_date_due', '=', today.strftime('%Y-%m-%d')),
    #             ('state', '=', 'posted'),
    #             ('move_type', 'in', ['out_invoice', 'out_refund']),
    #             ('payment_state', 'in', ['not_paid', 'partial']),
    #             ('line_ids.account_id.code',"=",120001),
    #             ('amount_residual_signed',"!=",0),
    #         ],
    #         "context": {
    #                 'default_move_type':'out_invoice',
    #                 'move_type':'out_invoice',
    #                 'journal_type': 'sale',
    #                 'group_by': ['invoice_user_id','partner_id'],
    #             },
    #         "search_view_id": self.env.ref("account.view_out_invoice_tree").id,
    #     }
    

    # def action_other(self):
    #     today = date.today()
    #     other_start = today.replace(month=1, day=1)
    #     other_end = (today.replace(day=1) - timedelta(days=1))

    #     return {
    #         "name": _("Unpaid Invoice This Month"),
    #         "type": "ir.actions.act_window",
    #         "res_model": "account.move",
    #         "view_mode": "tree",
    #         "view_id": self.env.ref("unpaid_invoice.view_account_move_custom_list").id,
    #         "target": "current",
    #         "domain":[
    #             ('invoice_date_due', '>=', other_start),
    #             ('invoice_date_due', '<=', other_end),
    #             ('state', '=', 'posted'),
    #             ('move_type', 'in', ['out_invoice', 'out_refund']),
    #             ('payment_state', 'in', ['not_paid', 'partial']),
    #             ('line_ids.account_id.code',"=",120001),
    #             ('amount_residual_signed',"!=",0),
    #         ],
    #         "context": {
    #                 'default_move_type':'out_invoice',
    #                 'move_type':'out_invoice',
    #                 'journal_type': 'sale',
    #                 'group_by': ['invoice_user_id','partner_id'],
    #             },
    #         "search_view_id": self.env.ref("account.view_out_invoice_tree").id,
    #     }


    def _get_action_domain(self, date_start, date_end):
        """Helper method to construct domain for unpaid invoices."""
        return [
            ('invoice_date_due', '>=', date_start),
            ('invoice_date_due', '<=', date_end),
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('line_ids.account_id.code', "=", 120001),
            ('amount_residual_signed', "!=", 0),
        ]

    def _get_action_context(self):
        """Helper method to construct context."""
        return {
            'default_move_type': 'out_invoice',
            'move_type': 'out_invoice',
            'journal_type': 'sale',
            'group_by': ['invoice_user_id', 'partner_id'],
        }

    def _prepare_action(self, name, date_start, date_end):
        """Helper method to prepare action dictionary."""
        return {
            "name": name,
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree",
            "view_id": self.env.ref("unpaid_invoice.view_account_move_custom_list").id,
            "target": "current",
            "domain": self._get_action_domain(date_start, date_end),
            "context": self._get_action_context(),
            "search_view_id": self.env.ref("account.view_out_invoice_tree").id,
        }

    def action_saturday_to_friday(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday() + 2)  # Previous Saturday
        week_end = week_start + timedelta(days=6)  # Following Friday
        return self._prepare_action(
            _("Unpaid Invoice This Week"),
            week_start.strftime('%Y-%m-%d'),
            week_end.strftime('%Y-%m-%d'),
        )

    def action_this_month(self):
        today = date.today()
        month_start = today.replace(day=1)
        month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        return self._prepare_action(
            _("Unpaid Invoice This Month"),
            month_start.strftime('%Y-%m-%d'),
            month_end.strftime('%Y-%m-%d'),
        )

    def action_today(self):
        today = date.today().strftime('%Y-%m-%d')
        return self._prepare_action(
            _("Unpaid Invoice Today"),
            today,
            today,
        )

    def action_other(self):
        today = date.today()
        other_start = today.replace(month=1, day=1).strftime('%Y-%m-%d')  # Start of the year
        other_end = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')  # End of previous month
        return self._prepare_action(
            _("Unpaid Invoice Other"),
            other_start,
            other_end,
        )
