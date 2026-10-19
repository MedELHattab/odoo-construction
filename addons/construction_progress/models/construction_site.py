from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    earned_value = fields.Monetary(
        compute="_compute_progress", store=True, currency_field="currency_id",
        help="Planned cost of the work completed so far.",
    )
    progress_percent = fields.Float(
        string="Progress (%)", compute="_compute_progress", store=True,
        help="Completed share of the bill of quantities, weighted by cost.",
    )
    cost_variance = fields.Monetary(
        compute="_compute_cost_variance", currency_field="currency_id",
        help="Earned value minus actual cost. Negative means you have spent more than the work done is worth.",
    )

    @api.depends("boq_line_ids.earned_value", "boq_total")
    def _compute_progress(self):
        for site in self:
            site.earned_value = sum(site.boq_line_ids.mapped("earned_value"))
            site.progress_percent = (
                site.earned_value / site.boq_total * 100.0 if site.boq_total else 0.0
            )

    @api.depends("earned_value", "actual_cost")
    def _compute_cost_variance(self):
        for site in self:
            site.cost_variance = site.earned_value - site.actual_cost
