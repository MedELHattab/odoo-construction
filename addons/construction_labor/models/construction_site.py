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
        compute="_compute_labor", store=True, currency_field="currency_id",
        help="Actual cost (vendor bills) plus labor cost.",
    )
    budget_after_total = fields.Monetary(
        compute="_compute_labor", store=True, currency_field="currency_id",
        help="Budget minus actual cost minus labor cost. Negative means over budget.",
    )

    @api.depends(
        "budget", "actual_cost",
        "timesheet_ids.unit_amount", "timesheet_ids.amount",
    )
    def _compute_labor(self):
        for site in self:
            lines = site.timesheet_ids
            site.labor_hours = sum(lines.mapped("unit_amount"))
            # timesheet amounts are negative costs
            site.labor_cost = -sum(lines.mapped("amount"))
            site.total_cost = site.actual_cost + site.labor_cost
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
