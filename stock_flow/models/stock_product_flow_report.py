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
    stock_balance = fields.Float(string="Stock Balance", readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)



    
    
    # @api.model
    # def init(self):
    #     self.env.cr.execute("""DROP MATERIALIZED VIEW IF EXISTS stock_product_flow_report CASCADE""")
    #     self.env.cr.execute("""
    #         CREATE MATERIALIZED VIEW stock_product_flow_report AS (

    #             WITH move_lines_union AS (

    #                 -- Internal → Internal: create both 'out' and 'in' rows
    #                 SELECT
    #                     sml.id * 1000 AS id,
    #                     sml.id AS move_line_id,
    #                     sml.product_id,
    #                     sml.date,
    #                     sml.location_id,
    #                     sml.location_dest_id,
    #                     sw_out.id AS warehouse_id,
    #                     sml.qty_done,
    #                     -sml.qty_done AS signed_qty_done,
    #                     CASE
    #                         WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
    #                         WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
    #                         WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
    #                         WHEN sl.usage = 'supplier' AND sld.usage = 'customer' THEN 'Transit'
    #                         WHEN sl.usage = 'customer' AND sld.usage = 'supplier' THEN 'Transit Return'
    #                         ELSE sm.name
    #                     END AS operation,
    #                     'out' AS direction
    #                 FROM stock_move_line sml
    #                 JOIN stock_move sm ON sm.id = sml.move_id
    #                 LEFT JOIN stock_location sl ON sml.location_id = sl.id
    #                 LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
    #                 LEFT JOIN stock_location l_out ON sml.location_id = l_out.id
    #                 LEFT JOIN stock_warehouse sw_out ON
    #                     sw_out.view_location_id = l_out.id OR
    #                     l_out.parent_path LIKE CONCAT('%/', sw_out.view_location_id::text, '/%')
    #                 WHERE
    #                     sm.state = 'done'
    #                     AND sl.usage = 'internal' AND sld.usage = 'internal'

    #                 UNION ALL

    #                 SELECT
    #                     sml.id * 1000 + 1 AS id,
    #                     sml.id AS move_line_id,
    #                     sml.product_id,
    #                     sml.date,
    #                     sml.location_id,
    #                     sml.location_dest_id,
    #                     sw_in.id AS warehouse_id,
    #                     sml.qty_done,
    #                     sml.qty_done AS signed_qty_done,
    #                     CASE
    #                         WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
    #                         WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
    #                         WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
    #                         WHEN sl.usage = 'supplier' AND sld.usage = 'customer' THEN 'Transit'
    #                         WHEN sl.usage = 'customer' AND sld.usage = 'supplier' THEN 'Transit Return'
    #                         ELSE sm.name
    #                     END AS operation,
    #                     'in' AS direction
    #                 FROM stock_move_line sml
    #                 JOIN stock_move sm ON sm.id = sml.move_id
    #                 LEFT JOIN stock_location sl ON sml.location_id = sl.id
    #                 LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
    #                 LEFT JOIN stock_location l_in ON sml.location_dest_id = l_in.id
    #                 LEFT JOIN stock_warehouse sw_in ON
    #                     sw_in.view_location_id = l_in.id OR
    #                     l_in.parent_path LIKE CONCAT('%/', sw_in.view_location_id::text, '/%')
    #                 WHERE
    #                     sm.state = 'done'
    #                     AND sl.usage = 'internal' AND sld.usage = 'internal'

    #                 UNION ALL

    #                 -- External ↔ Internal: single row only
    #                 SELECT
    #                     sml.id * 1000 + 2 AS id,
    #                     sml.id AS move_line_id,
    #                     sml.product_id,
    #                     sml.date,
    #                     sml.location_id,
    #                     sml.location_dest_id,
    #                     CASE
    #                         WHEN sl.usage = 'internal' THEN sw_out.id
    #                         WHEN sld.usage = 'internal' THEN sw_in.id
    #                         ELSE NULL
    #                     END AS warehouse_id,
    #                     sml.qty_done,
    #                     CASE
    #                         WHEN sl.usage = 'internal' THEN -sml.qty_done
    #                         WHEN sld.usage = 'internal' THEN sml.qty_done
    #                         WHEN sl.usage = 'supplier' AND sld.usage = 'customer' THEN -sml.qty_done
    #                         WHEN sl.usage = 'customer' AND sld.usage = 'supplier' THEN sml.qty_done
    #                         ELSE 0
    #                     END AS signed_qty_done,
    #                     CASE
    #                         WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
    #                         WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
    #                         WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
    #                         WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
    #                         WHEN sl.usage = 'supplier' AND sld.usage = 'customer' THEN 'Transit'
    #                         WHEN sl.usage = 'customer' AND sld.usage = 'supplier' THEN 'Transit Return'
    #                         ELSE sm.name
    #                     END AS operation,
    #                     CASE
    #                         WHEN sl.usage = 'internal' THEN 'out'
    #                         WHEN sld.usage = 'internal' THEN 'in'
    #                         WHEN sl.usage = 'supplier' AND sld.usage = 'customer' THEN 'out'
    #                         WHEN sl.usage = 'customer' AND sld.usage = 'supplier' THEN 'in'
    #                         ELSE NULL
    #                     END AS direction
    #                 FROM stock_move_line sml
    #                 JOIN stock_move sm ON sm.id = sml.move_id
    #                 LEFT JOIN stock_location sl ON sml.location_id = sl.id
    #                 LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
    #                 LEFT JOIN stock_location l_out ON sml.location_id = l_out.id
    #                 LEFT JOIN stock_location l_in ON sml.location_dest_id = l_in.id
    #                 LEFT JOIN stock_warehouse sw_out ON
    #                     sw_out.view_location_id = l_out.id OR
    #                     l_out.parent_path LIKE CONCAT('%/', sw_out.view_location_id::text, '/%')
    #                 LEFT JOIN stock_warehouse sw_in ON
    #                     sw_in.view_location_id = l_in.id OR
    #                     l_in.parent_path LIKE CONCAT('%/', sw_in.view_location_id::text, '/%')
    #                 WHERE
    #                     sm.state = 'done'
    #                     AND NOT (sl.usage = 'internal' AND sld.usage = 'internal')
    #             )

    #             -- Final SELECT: apply stock balance
    #             SELECT
    #                 *,
    #                 SUM(signed_qty_done) OVER (
    #                     PARTITION BY product_id, warehouse_id
    #                     ORDER BY date,
    #                             CASE WHEN direction = 'in' THEN 0 ELSE 1 END,
    #                             id
    #                 ) AS stock_balance
    #             FROM move_lines_union

    #         )
    #     """)
    #     self.env.cr.execute("""
    #         CREATE INDEX IF NOT EXISTS idx_stock_balance_by_product_warehouse
    #         ON stock_product_flow_report (product_id, warehouse_id, date)
    #     """)


    @api.model
    def init(self):
        """Initialize the stock product flow report materialized view."""
        self._drop_existing_view()
        self._create_materialized_view()
        self._create_indexes()

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
        """.format(operation_case=self._get_operation_case_statement())

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
        """.format(operation_case=self._get_operation_case_statement())

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
        """.format(
            signed_qty_case=self._get_signed_qty_case_statement(),
            operation_case=self._get_operation_case_statement(),
            direction_case=self._get_direction_case_statement()
        )

    def _get_operation_case_statement(self):
        """Get the CASE statement for determining operation type."""
        return """
            CASE
                WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
                WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
                WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
                WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
                WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
                WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
                WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
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
                ELSE NULL
            END
        """

    def _get_final_select_with_balance(self):
        """Get the final SELECT statement with stock balance calculation."""
        return """
            SELECT
                *,
                SUM(signed_qty_done) OVER (
                    PARTITION BY product_id, warehouse_id
                    ORDER BY date,
                            CASE WHEN direction = 'in' THEN 0 ELSE 1 END,
                            id
                ) AS stock_balance
            FROM move_lines_union
        """

    def _create_indexes(self):
        """Create indexes for the materialized view."""
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_balance_by_product_warehouse
            ON stock_product_flow_report (product_id, warehouse_id, date)
        """)

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





