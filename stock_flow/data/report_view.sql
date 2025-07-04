DROP VIEW IF EXISTS stock_move_line_report;
CREATE VIEW stock_move_line_report AS (
    SELECT
        sml.id as id,
        sml.id as move_line_id,
        sml.product_id,
        sml.date,
        sml.location_id,
        sml.location_dest_id,
        CASE 
            WHEN src.usage = 'internal' THEN sw_from.id
            ELSE sw_to.id
        END as warehouse_id,
        sml.qty_done,
        CASE 
            WHEN src.usage = 'internal' AND dest.usage != 'internal' THEN -sml.qty_done
            ELSE sml.qty_done
        END as signed_qty_done,
        CASE 
            WHEN src.usage = 'supplier' AND dest.usage = 'internal' THEN 'Buy → ' || dest.name
            WHEN src.usage = 'internal' AND dest.usage = 'customer' THEN 'Sell → ' || src.name
            WHEN src.usage = 'internal' AND dest.usage = 'internal' THEN 'Transfer → ' || dest.name
            WHEN src.usage = 'inventory' AND dest.usage = 'internal' THEN 'Adjustment → ' || dest.name
            WHEN src.usage = 'internal' AND dest.usage = 'inventory' THEN 'Scrap → ' || src.name
            ELSE ''
        END as operation,
        CASE 
            WHEN src.usage = 'internal' AND dest.usage != 'internal' THEN 'out'
            WHEN dest.usage = 'internal' AND src.usage != 'internal' THEN 'in'
            ELSE NULL
        END as direction
    FROM stock_move_line sml
    LEFT JOIN stock_location src ON sml.location_id = src.id
    LEFT JOIN stock_location dest ON sml.location_dest_id = dest.id
    LEFT JOIN stock_warehouse sw_from ON src.id = sw_from.lot_stock_id
    LEFT JOIN stock_warehouse sw_to ON dest.id = sw_to.lot_stock_id
    WHERE sml.state = 'done'
);
