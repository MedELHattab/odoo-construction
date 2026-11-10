from odoo import fields, models, tools


class ConstructionMaterial(models.Model):
    """One row per goods line on a confirmed purchase order linked to a site."""
    _name = "construction.material"
    _description = "Construction Material Tracking"
    _auto = False
    _order = "expected_date, id"

    site_id = fields.Many2one("construction.site", string="Site", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    order_id = fields.Many2one("purchase.order", string="Purchase Order", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Supplier", readonly=True)
    product_id = fields.Many2one("product.product", string="Material", readonly=True)
    uom_id = fields.Many2one("uom.uom", string="Unit", readonly=True)
    expected_date = fields.Datetime(readonly=True)
    ordered_qty = fields.Float(string="Ordered", readonly=True)
    received_qty = fields.Float(string="Received", readonly=True)
    outstanding_qty = fields.Float(string="Still to deliver", readonly=True)
    billed_qty = fields.Float(string="Billed", readonly=True)
    ordered_amount = fields.Monetary(string="Ordered value", readonly=True)
    received_amount = fields.Monetary(string="Received value", readonly=True)
    outstanding_amount = fields.Monetary(string="Value still to deliver", readonly=True)
    is_late = fields.Boolean(string="Late delivery", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT l.id, po.site_id, po.company_id, po.id AS order_id, po.partner_id,
                       l.product_id, l.product_uom_id AS uom_id, l.date_planned AS expected_date,
                       l.product_qty AS ordered_qty,
                       l.qty_received AS received_qty,
                       GREATEST(l.product_qty - l.qty_received, 0) AS outstanding_qty,
                       l.qty_invoiced AS billed_qty,
                       l.price_subtotal AS ordered_amount,
                       LEAST(l.qty_received, l.product_qty) * l.price_unit * (1 - COALESCE(l.discount, 0) / 100.0)
                           AS received_amount,
                       GREATEST(l.product_qty - l.qty_received, 0) * l.price_unit
                           * (1 - COALESCE(l.discount, 0) / 100.0) AS outstanding_amount,
                       (l.qty_received < l.product_qty AND l.date_planned < now() AT TIME ZONE 'UTC') AS is_late
                  FROM purchase_order_line l
                  JOIN purchase_order po ON po.id = l.order_id
                  JOIN product_product pp ON pp.id = l.product_id
                  JOIN product_template pt ON pt.id = pp.product_tmpl_id
                 WHERE po.site_id IS NOT NULL AND po.state IN ('purchase', 'done')
                   AND l.display_type IS NULL AND pt.type = 'consu'
            )
        """)
