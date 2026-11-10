from odoo import fields, models, tools


class ConstructionPortfolio(models.Model):
    """One row per active site with its key figures and open risks, for portfolio-level analysis."""
    _name = "construction.portfolio"
    _description = "Construction Portfolio"
    _auto = False
    _order = "site_id"

    site_id = fields.Many2one("construction.site", string="Site", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    partner_id = fields.Many2one("res.partner", string="Client", readonly=True)
    manager_id = fields.Many2one("res.users", string="Site manager", readonly=True)
    state = fields.Selection(
        [("draft", "Planning"), ("in_progress", "In Progress"), ("on_hold", "On Hold"),
         ("done", "Done"), ("cancelled", "Cancelled")], readonly=True,
    )
    budget = fields.Monetary(readonly=True)
    committed_cost = fields.Monetary(readonly=True)
    total_cost = fields.Monetary(readonly=True)
    billed_amount = fields.Monetary(readonly=True)
    retention_held = fields.Monetary(readonly=True)
    margin_to_date = fields.Monetary(readonly=True)
    earned_value = fields.Monetary(readonly=True)
    progress_percent = fields.Float(string="Progress (%)", readonly=True, aggregator="avg")
    over_budget = fields.Integer(string="Sites over budget", readonly=True)
    late_sites = fields.Integer(string="Sites past end date", readonly=True)
    open_punch = fields.Integer(string="Open punch items", readonly=True)
    overdue_punch = fields.Integer(string="Overdue punch items", readonly=True)
    failed_inspections = fields.Integer(string="Failed inspections", readonly=True)
    site_count = fields.Integer(string="Sites", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT s.id AS id, s.id AS site_id, s.company_id, s.partner_id, s.manager_id, s.state,
                       s.budget, s.committed_cost, s.total_cost, s.billed_amount, s.retention_held,
                       s.margin_to_date, s.earned_value, s.progress_percent,
                       CASE WHEN s.budget > 0 AND s.total_cost > s.budget THEN 1 ELSE 0 END AS over_budget,
                       CASE WHEN s.state = 'in_progress' AND s.date_end < CURRENT_DATE THEN 1 ELSE 0 END AS late_sites,
                       (SELECT count(*) FROM construction_punch_item p
                         WHERE p.site_id = s.id AND p.state != 'verified') AS open_punch,
                       (SELECT count(*) FROM construction_punch_item p
                         WHERE p.site_id = s.id AND p.state = 'open' AND p.deadline < CURRENT_DATE) AS overdue_punch,
                       (SELECT count(*) FROM construction_inspection i
                         WHERE i.site_id = s.id AND i.state = 'done' AND i.result = 'fail') AS failed_inspections,
                       1 AS site_count
                  FROM construction_site s
                 WHERE s.active
            )
        """)
