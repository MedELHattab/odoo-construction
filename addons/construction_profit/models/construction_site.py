from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    collected_amount = fields.Monetary(
        compute="_compute_cash", currency_field="currency_id",
        help="Cash received from the client on progress and retention invoices.",
    )
    receivable_amount = fields.Monetary(
        compute="_compute_cash", currency_field="currency_id",
        help="Posted client invoices that are not paid yet.",
    )
    cash_position = fields.Monetary(
        compute="_compute_cash", currency_field="currency_id",
        help="Cash received from the client minus the total cost so far.",
    )
    forecast_cost = fields.Monetary(
        compute="_compute_forecast", currency_field="currency_id",
        help="Estimated total cost at completion. Cost so far is extrapolated by the cost of the work done "
             "(planned cost divided by earned value, times the cost so far).",
    )
    forecast_margin = fields.Monetary(
        compute="_compute_forecast", currency_field="currency_id",
        help="Contract value minus the forecast cost at completion.",
    )
    forecast_margin_percent = fields.Float(
        string="Forecast margin (%)", compute="_compute_forecast",
        help="Forecast margin as a share of the contract value.",
    )

    @api.depends(
        "statement_ids.state", "statement_ids.invoice_id.state",
        "statement_ids.invoice_id.amount_total", "statement_ids.invoice_id.amount_residual", "total_cost",
    )
    def _compute_cash(self):
        for site in self:
            invoices = site.statement_ids.filtered(lambda s: s.state == "invoiced").invoice_id.filtered(
                lambda m: m.state == "posted"
            )
            site.receivable_amount = sum(invoices.mapped("amount_residual"))
            site.collected_amount = sum(invoices.mapped("amount_total")) - site.receivable_amount
            site.cash_position = site.collected_amount - site.total_cost

    @api.depends("total_cost", "earned_value", "boq_total", "budget", "contract_value")
    def _compute_forecast(self):
        for site in self:
            planned = site.boq_total or site.budget
            if site.total_cost > 0 and site.earned_value > 0:
                forecast = planned * site.total_cost / site.earned_value
            else:
                # Without progress there is nothing to extrapolate from.
                forecast = max(planned, site.total_cost)
            site.forecast_cost = forecast
            site.forecast_margin = site.contract_value - forecast
            site.forecast_margin_percent = (
                site.forecast_margin / site.contract_value * 100.0 if site.contract_value else 0.0
            )
