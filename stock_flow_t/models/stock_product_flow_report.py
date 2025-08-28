# # -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockProductFlowReport(models.Model):
    _name = 'stock.product.flow.report'
    _description = 'Stock Move Line Report'
    _auto = False
    _rec_name = 'move_line_id'
    _order = 'date asc'

    move_line_id = fields.Many2one('stock.move.line', string="Original Move Line")
    product_id = fields.Many2one('product.product', string="Product")
    date = fields.Datetime(string="Date")
    location_id = fields.Many2one('stock.location', string="Source Location")
    location_dest_id = fields.Many2one('stock.location', string="Destination Location")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    qty_done = fields.Float(string="Qty Done")
    signed_qty_done = fields.Float(string="Signed Qty")
    operation = fields.Char(string="Operation")
    direction = fields.Selection([('in', 'In'), ('out', 'Out')], string="Direction")
    stock_balance = fields.Float(string="Stock Balance", readonly=True, group_operator=False)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)







    @api.model
    def init(self):
        """Initialize the stock product flow report materialized view."""
        self._drop_existing_view()
        self._create_materialized_view()
        self._create_indexes()

    def _get_company_filter_condition_out(self):
        """Get basic data integrity checks for outbound queries."""
        return """
            AND sw_out.company_id IS NOT NULL
        """

    def _get_company_filter_condition_in(self):
        """Get basic data integrity checks for inbound queries."""
        return """
            AND sw_in.company_id IS NOT NULL
        """

    def _get_company_filter_condition_external(self):
        """Get basic data integrity checks for external queries."""
        return """
            AND (
                (sl.usage = 'internal' AND sw_out.company_id IS NOT NULL) OR
                (sld.usage = 'internal' AND sw_in.company_id IS NOT NULL) OR
                (sl.usage != 'internal' AND sld.usage != 'internal')
            )
        """

    def _drop_existing_view(self):
        """Drop the existing materialized view if it exists."""
        self.env.cr.execute("""
            DROP MATERIALIZED VIEW IF EXISTS stock_product_flow_report CASCADE
        """)

    def _create_materialized_view(self):
        """Create the main materialized view with all stock movements."""
        query = f"""
            CREATE MATERIALIZED VIEW stock_product_flow_report AS (
                WITH move_lines_union AS (
                    {self._get_internal_to_internal_out_query()}
                    UNION ALL
                    {self._get_internal_to_internal_in_query()}
                    UNION ALL
                    {self._get_external_to_internal_query()}
                )
                {self._get_final_select_with_balance()}
            )
        """
        self.env.cr.execute(query)

    def _get_internal_to_internal_out_query(self):
        """Get the query for internal to internal transfers (outbound side)."""
        return """
            SELECT
                sml.id * 1000 AS id,
                sml.id AS move_line_id,
                sml.product_id,
                sml.date,
                sml.location_id,
                sml.location_dest_id,
                sw_out.id AS warehouse_id,
                sw_out.company_id AS company_id,
                sml.qty_done,
                -sml.qty_done AS signed_qty_done,
                {operation_case} AS operation,
                'out' AS direction
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            LEFT JOIN stock_location sl ON sml.location_id = sl.id
            LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
            LEFT JOIN stock_location l_out ON sml.location_id = l_out.id
            LEFT JOIN stock_warehouse sw_out ON
                sw_out.view_location_id = l_out.id OR
                l_out.parent_path LIKE CONCAT('%/', sw_out.view_location_id::text, '/%')
            WHERE
                sm.state = 'done'
                AND sl.usage = 'internal' AND sld.usage = 'internal'
                AND sw_out.company_id IS NOT NULL
                {company_filter}
        """.format(
            operation_case=self._get_operation_case_statement(),
            company_filter=self._get_company_filter_condition_out()
        )

    def _get_internal_to_internal_in_query(self):
        """Get the query for internal to internal transfers (inbound side)."""
        return """
            SELECT
                sml.id * 1000 + 1 AS id,
                sml.id AS move_line_id,
                sml.product_id,
                sml.date,
                sml.location_id,
                sml.location_dest_id,
                sw_in.id AS warehouse_id,
                sw_in.company_id AS company_id,
                sml.qty_done,
                sml.qty_done AS signed_qty_done,
                {operation_case} AS operation,
                'in' AS direction
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            LEFT JOIN stock_location sl ON sml.location_id = sl.id
            LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
            LEFT JOIN stock_location l_in ON sml.location_dest_id = l_in.id
            LEFT JOIN stock_warehouse sw_in ON
                sw_in.view_location_id = l_in.id OR
                l_in.parent_path LIKE CONCAT('%/', sw_in.view_location_id::text, '/%')
            WHERE
                sm.state = 'done'
                AND sl.usage = 'internal' AND sld.usage = 'internal'
                AND sw_in.company_id IS NOT NULL
                {company_filter}
        """.format(
            operation_case=self._get_operation_case_statement(),
            company_filter=self._get_company_filter_condition_in()
        )

    def _get_external_to_internal_query(self):
        """Get the query for external to internal transfers."""
        return """
            SELECT
                sml.id * 1000 + 2 AS id,
                sml.id AS move_line_id,
                sml.product_id,
                sml.date,
                sml.location_id,
                sml.location_dest_id,
                CASE
                    WHEN sl.usage = 'internal' THEN sw_out.id
                    WHEN sld.usage = 'internal' THEN sw_in.id
                    ELSE NULL
                END AS warehouse_id,
                CASE
                    WHEN sl.usage = 'internal' THEN sw_out.company_id
                    WHEN sld.usage = 'internal' THEN sw_in.company_id
                    ELSE NULL
                END AS company_id,
                sml.qty_done,
                {signed_qty_case} AS signed_qty_done,
                {operation_case} AS operation,
                {direction_case} AS direction
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            LEFT JOIN stock_location sl ON sml.location_id = sl.id
            LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
            LEFT JOIN stock_location l_out ON sml.location_id = l_out.id
            LEFT JOIN stock_location l_in ON sml.location_dest_id = l_in.id
            LEFT JOIN stock_warehouse sw_out ON
                sw_out.view_location_id = l_out.id OR
                l_out.parent_path LIKE CONCAT('%/', sw_out.view_location_id::text, '/%')
            LEFT JOIN stock_warehouse sw_in ON
                sw_in.view_location_id = l_in.id OR
                l_in.parent_path LIKE CONCAT('%/', sw_in.view_location_id::text, '/%')
            WHERE
                sm.state = 'done'
                AND NOT (sl.usage = 'internal' AND sld.usage = 'internal')
                AND (
                    (sl.usage = 'internal' AND sw_out.company_id IS NOT NULL) OR
                    (sld.usage = 'internal' AND sw_in.company_id IS NOT NULL) OR
                    (sl.usage != 'internal' AND sld.usage != 'internal')
                )
                {company_filter}
        """.format(
            signed_qty_case=self._get_signed_qty_case_statement(),
            operation_case=self._get_operation_case_statement(),
            direction_case=self._get_direction_case_statement(),
            company_filter=self._get_company_filter_condition_external()
        )

    def _get_operation_case_statement(self):
        """Get the CASE statement for determining operation type."""
        return """
            CASE
                WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
                WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
                WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap & Adjustment Out'
                WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap & Adjustment In'
                WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
                WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
                WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
                WHEN sl.usage = 'internal' AND sld.usage = 'production' THEN 'Manufacturing Consumption'
                WHEN sl.usage = 'production' AND sld.usage = 'internal' THEN 'Manufacturing Production'
                WHEN sl.usage = 'supplier' AND sld.usage = 'customer' THEN 'Transit'
                WHEN sl.usage = 'customer' AND sld.usage = 'supplier' THEN 'Transit Return'
                ELSE sm.name
            END
        """

    def _get_signed_qty_case_statement(self):
        """Get the CASE statement for signed quantity calculation."""
        return """
            CASE
                WHEN sl.usage = 'internal' THEN -sml.qty_done
                WHEN sld.usage = 'internal' THEN sml.qty_done
                WHEN sl.usage = 'supplier' AND sld.usage = 'customer' THEN -sml.qty_done
                WHEN sl.usage = 'customer' AND sld.usage = 'supplier' THEN sml.qty_done
                WHEN sl.usage = 'internal' AND sld.usage = 'production' THEN -sml.qty_done
                WHEN sl.usage = 'production' AND sld.usage = 'internal' THEN sml.qty_done
                ELSE 0
            END
        """

    def _get_direction_case_statement(self):
        """Get the CASE statement for direction determination."""
        return """
            CASE
                WHEN sl.usage = 'internal' THEN 'out'
                WHEN sld.usage = 'internal' THEN 'in'
                WHEN sl.usage = 'supplier' AND sld.usage = 'customer' THEN 'out'
                WHEN sl.usage = 'customer' AND sld.usage = 'supplier' THEN 'in'
                WHEN sl.usage = 'internal' AND sld.usage = 'production' THEN 'out'
                WHEN sl.usage = 'production' AND sld.usage = 'internal' THEN 'in'
                ELSE NULL
            END
        """

    def _get_final_select_with_balance(self):
        """Get the final SELECT statement with stock balance calculation."""
        return """
            SELECT
                *,
                SUM(signed_qty_done) OVER (
                    PARTITION BY product_id, warehouse_id, company_id
                    ORDER BY date,
                            CASE WHEN direction = 'in' THEN 0 ELSE 1 END,
                            id
                ) AS stock_balance
            FROM move_lines_union
        """

    def _create_indexes(self):
        """Create indexes for the materialized view."""
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_balance_by_product_warehouse_company
            ON stock_product_flow_report (product_id, warehouse_id, company_id, date)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_balance_by_company
            ON stock_product_flow_report (company_id)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_balance_by_date_company
            ON stock_product_flow_report (date, company_id)
        """)

    @api.model
    def get_stock_report_for_company(self, company_id):
        """Get stock report filtered by company."""
        self.env.cr.execute("""
            SELECT * FROM stock_product_flow_report 
            WHERE company_id = %s
            ORDER BY date DESC, id DESC
        """, (company_id,))
        return self.env.cr.dictfetchall()

    @api.model
    def refresh_materialized_view(self):
        """Refresh the materialized view to update data."""
        self.env.cr.execute("""
            REFRESH MATERIALIZED VIEW stock_product_flow_report
        """)

    @api.model
    def rebuild_materialized_view(self):
        """Completely rebuild the materialized view."""
        self.init()

    