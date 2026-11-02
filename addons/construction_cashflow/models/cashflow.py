from odoo import fields, models, tools


class ConstructionCashflow(models.Model):
    """One row per open client invoice, open vendor bill, or retention still held, dated when the money is due."""
    _name = "construction.cashflow"
    _description = "Cash Flow Forecast"
    _auto = False
    _order = "date, id"

    site_id = fields.Many2one("construction.site", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    partner_id = fields.Many2one("res.partner", readonly=True)
    move_id = fields.Many2one("account.move", string="Invoice or Bill", readonly=True)
    date = fields.Date(string="Due Date", readonly=True)
    kind = fields.Selection(
        [("receipt", "Client invoice"), ("payment", "Vendor bill"), ("retention", "Retention release")],
        string="Type", readonly=True,
    )
    inflow = fields.Monetary(string="Money In", readonly=True)
    outflow = fields.Monetary(string="Money Out", readonly=True)
    net = fields.Monetary(string="Net", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT row_number() OVER (ORDER BY date, kind, move_id) AS id, rows.*
                FROM (
                    SELECT st.site_id, am.company_id, am.partner_id, am.id AS move_id,
                           COALESCE(am.invoice_date_due, am.invoice_date, am.date) AS date,
                           'receipt' AS kind,
                           ABS(am.amount_residual_signed) AS inflow, 0 AS outflow,
                           ABS(am.amount_residual_signed) AS net
                      FROM construction_progress_statement st
                      JOIN account_move am ON am.id = st.invoice_id
                     WHERE st.state = 'invoiced' AND am.state = 'posted' AND am.amount_residual_signed != 0
                    UNION ALL
                    SELECT am.site_id, am.company_id, am.partner_id, am.id,
                           COALESCE(am.invoice_date_due, am.invoice_date, am.date),
                           'payment', 0, ABS(am.amount_residual_signed), -ABS(am.amount_residual_signed)
                      FROM account_move am
                     WHERE am.move_type = 'in_invoice' AND am.state = 'posted'
                       AND am.site_id IS NOT NULL AND am.amount_residual_signed != 0
                    UNION ALL
                    SELECT s.id, s.company_id, s.partner_id, NULL, s.date_end,
                           'retention', s.retention_held, 0, s.retention_held
                      FROM construction_site s
                     WHERE s.active AND s.retention_held > 0 AND s.date_end IS NOT NULL
                ) rows
            )
        """)
