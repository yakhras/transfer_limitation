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

    @api.model
    def init(self):
        company_id = self.env.company.id
        if company_id == 1:
            return self.company_1()
        elif company_id == 5:
            return self.company_5()
        else:
            raise ValueError("Unsupported company ID: {}".format(company_id))



    def company_5(self):
        self.env.cr.execute("""DROP MATERIALIZED VIEW IF EXISTS stock_product_flow_report CASCADE""")
        self.env.cr.execute("""
            CREATE MATERIALIZED VIEW stock_product_flow_report AS (

                WITH move_lines_union AS (

                    -- Internal → Internal: create both 'out' and 'in' rows
                    SELECT
                        sml.id * 2 AS id,
                        sml.id AS move_line_id,
                        sml.product_id,
                        sml.date,
                        sml.location_id,
                        sml.location_dest_id,
                        sw_out.id AS warehouse_id,
                        sml.qty_done,
                        -sml.qty_done AS signed_qty_done,
                        CASE
                            WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
                            WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
                            WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
                            WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
                            WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
                            ELSE sm.name
                        END AS operation,
                        'out' AS direction
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                    LEFT JOIN stock_location sl ON sml.location_id = sl.id
                    LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
                    LEFT JOIN stock_warehouse sw_out ON sw_out.lot_stock_id = sml.location_id
                    WHERE
                        sml.company_id = 5
                        AND sm.state = 'done'
                        AND sl.usage = 'internal' AND sld.usage = 'internal'

                    UNION ALL

                    SELECT
                        sml.id * 2 + 1 AS id,
                        sml.id AS move_line_id,
                        sml.product_id,
                        sml.date,
                        sml.location_id,
                        sml.location_dest_id,
                        sw_in.id AS warehouse_id,
                        sml.qty_done,
                        sml.qty_done AS signed_qty_done,
                        CASE
                            WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
                            WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
                            WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
                            WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
                            WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
                            ELSE sm.name
                        END AS operation,
                        'in' AS direction
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                    LEFT JOIN stock_location sl ON sml.location_id = sl.id
                    LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
                    LEFT JOIN stock_warehouse sw_in ON sw_in.lot_stock_id = sml.location_dest_id
                    WHERE
                        sml.company_id = 5
                        AND sm.state = 'done'
                        AND sl.usage = 'internal' AND sld.usage = 'internal'

                    UNION ALL

                    -- External ↔ Internal: single row only
                    SELECT
                        sml.id * 10 AS id,
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
                        CASE
                            WHEN sl.usage = 'internal' THEN -sml.qty_done
                            WHEN sld.usage = 'internal' THEN sml.qty_done
                            ELSE 0
                        END AS signed_qty_done,
                        CASE
                            WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
                            WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
                            WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
                            WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
                            WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
                            ELSE sm.name
                        END AS operation,
                        CASE
                            WHEN sl.usage = 'internal' THEN 'out'
                            WHEN sld.usage = 'internal' THEN 'in'
                            ELSE NULL
                        END AS direction
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                    LEFT JOIN stock_location sl ON sml.location_id = sl.id
                    LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
                    LEFT JOIN stock_warehouse sw_out ON sw_out.lot_stock_id = sl.id
                    LEFT JOIN stock_warehouse sw_in ON sw_in.lot_stock_id = sld.id
                    WHERE
                        sml.company_id = 5
                        AND sm.state = 'done'
                        AND NOT (sl.usage = 'internal' AND sld.usage = 'internal')
                )

                -- Final SELECT: apply stock balance
                SELECT
                    *,
                    SUM(signed_qty_done) OVER (
                        PARTITION BY product_id, warehouse_id
                        ORDER BY date,
                                CASE WHEN direction = 'in' THEN 0 ELSE 1 END,
                                id
                    ) AS stock_balance
                FROM move_lines_union

            )
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_balance_by_product_warehouse
            ON stock_product_flow_report (product_id, warehouse_id, date)
        """)
    
    


    def company_1(self):
        self.env.cr.execute("""DROP MATERIALIZED VIEW IF EXISTS stock_product_flow_report CASCADE""")
        self.env.cr.execute("""
            CREATE MATERIALIZED VIEW stock_product_flow_report AS (

                WITH move_lines_union AS (

                    -- Internal → Internal: create both 'out' and 'in' rows
                    SELECT
                        sml.id * 2 AS id,
                        sml.id AS move_line_id,
                        sml.product_id,
                        sml.date,
                        sml.location_id,
                        sml.location_dest_id,
                        sw_out.id AS warehouse_id,
                        sml.qty_done,
                        -sml.qty_done AS signed_qty_done,
                        CASE
                            WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
                            WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
                            WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
                            WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
                            WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
                            ELSE sm.name
                        END AS operation,
                        'out' AS direction
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                    LEFT JOIN stock_location sl ON sml.location_id = sl.id
                    LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
                    LEFT JOIN stock_warehouse sw_out ON sw_out.lot_stock_id = sml.location_id
                    WHERE
                        sml.company_id = 1
                        AND sm.state = 'done'
                        AND sl.usage = 'internal' AND sld.usage = 'internal'

                    UNION ALL

                    SELECT
                        sml.id * 2 + 1 AS id,
                        sml.id AS move_line_id,
                        sml.product_id,
                        sml.date,
                        sml.location_id,
                        sml.location_dest_id,
                        sw_in.id AS warehouse_id,
                        sml.qty_done,
                        sml.qty_done AS signed_qty_done,
                        CASE
                            WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
                            WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
                            WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
                            WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
                            WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
                            ELSE sm.name
                        END AS operation,
                        'in' AS direction
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                    LEFT JOIN stock_location sl ON sml.location_id = sl.id
                    LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
                    LEFT JOIN stock_warehouse sw_in ON sw_in.lot_stock_id = sml.location_dest_id
                    WHERE
                        sml.company_id = 1
                        AND sm.state = 'done'
                        AND sl.usage = 'internal' AND sld.usage = 'internal'

                    UNION ALL

                    -- External ↔ Internal: single row only
                    SELECT
                        sml.id * 10 AS id,
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
                        CASE
                            WHEN sl.usage = 'internal' THEN -sml.qty_done
                            WHEN sld.usage = 'internal' THEN sml.qty_done
                            ELSE 0
                        END AS signed_qty_done,
                        CASE
                            WHEN sl.usage = 'supplier' AND sld.usage = 'internal' THEN 'Buy'
                            WHEN sl.usage = 'internal' AND sld.usage = 'customer' THEN 'Sell'
                            WHEN sl.usage = 'internal' AND sld.usage = 'inventory' THEN 'Scrap Out'
                            WHEN sl.usage = 'inventory' AND sld.usage = 'internal' THEN 'Scrap In'
                            WHEN sl.usage = 'customer' AND sld.usage = 'internal' THEN 'Customer Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'supplier' THEN 'Vendor Return'
                            WHEN sl.usage = 'internal' AND sld.usage = 'internal' THEN 'Transfer'
                            ELSE sm.name
                        END AS operation,
                        CASE
                            WHEN sl.usage = 'internal' THEN 'out'
                            WHEN sld.usage = 'internal' THEN 'in'
                            ELSE NULL
                        END AS direction
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                    LEFT JOIN stock_location sl ON sml.location_id = sl.id
                    LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
                    LEFT JOIN stock_warehouse sw_out ON sw_out.lot_stock_id = sl.id
                    LEFT JOIN stock_warehouse sw_in ON sw_in.lot_stock_id = sld.id
                    WHERE
                        sml.company_id = 1
                        AND sm.state = 'done'
                        AND NOT (sl.usage = 'internal' AND sld.usage = 'internal')
                )

                -- Final SELECT: apply stock balance
                SELECT
                    *,
                    SUM(signed_qty_done) OVER (
                        PARTITION BY product_id, warehouse_id
                        ORDER BY date,
                                CASE WHEN direction = 'in' THEN 0 ELSE 1 END,
                                id
                    ) AS stock_balance
                FROM move_lines_union

            )
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_balance_by_product_warehouse
            ON stock_product_flow_report (product_id, warehouse_id, date)
        """)
    
    