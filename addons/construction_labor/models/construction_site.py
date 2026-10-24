from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    timesheet_ids = fields.One2many("account.analytic.line", "site_id", string="Timesheets")
    labor_hours = fields.Float(compute="_compute_labor", store=True)
    labor_cost = fields.Monetary(
        compute="_compute_labor", store=True, currency_field="currency_id",
        help="Hours worked on the site's project, valued at each employee's hourly cost.",
    )
    total_cost = fields.Monetary(
        compute="_compute_total_cost", store=True, currency_field="currency_id",
        help="Everything spent on the site: vendor bills, labor and any other cost source "
             "added by other modules (equipment, expenses).",
    )
    budget_after_total = fields.Monetary(
        compute="_compute_total_cost", store=True, currency_field="currency_id",
        help="Budget minus total cost. Negative means over budget.",
    )

    @api.depends("timesheet_ids.unit_amount", "timesheet_ids.amount")
    def _compute_labor(self):
        for site in self:
            lines = site.timesheet_ids
            site.labor_hours = sum(lines.mapped("unit_amount"))
            # timesheet amounts are negative costs
            site.labor_cost = -sum(lines.mapped("amount"))

    def _total_cost_amount(self):
        """Total spent on this site. Modules that add a cost source extend this
        method and must also redeclare ``_compute_total_cost`` with the full
        ``@api.depends`` list (Odoo does not merge depends across overrides)."""
        self.ensure_one()
        return self.actual_cost + self.labor_cost

    @api.depends("budget", "actual_cost", "labor_cost")
    def _compute_total_cost(self):
        for site in self:
            site.total_cost = site._total_cost_amount()
            site.budget_after_total = site.budget - site.total_cost

    def action_view_timesheets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Timesheets"),
            "res_model": "account.analytic.line",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
        }
