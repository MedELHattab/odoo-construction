from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    budget_used_percent = fields.Float(
        string="Budget used (%)", compute="_compute_dashboard_figures", store=True,
        help="Total cost (bills, labor, equipment, expenses) as a share of the budget.",
    )
    margin_to_date = fields.Monetary(
        compute="_compute_dashboard_figures", store=True, currency_field="currency_id",
        help="Work invoiced to the client so far (before retention) minus the total cost so far.",
    )

    @api.depends("total_cost", "budget", "billed_amount")
    def _compute_dashboard_figures(self):
        for site in self:
            site.budget_used_percent = site.total_cost / site.budget * 100.0 if site.budget else 0.0
            site.margin_to_date = site.billed_amount - site.total_cost
