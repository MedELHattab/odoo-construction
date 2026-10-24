from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    equipment_usage_ids = fields.One2many(
        "construction.equipment.usage", "site_id", string="Equipment"
    )
    equipment_cost = fields.Monetary(
        compute="_compute_equipment_cost", store=True, currency_field="currency_id",
        help="Days on site multiplied by the daily rate, for all assigned equipment.",
    )

    @api.depends("equipment_usage_ids.cost")
    def _compute_equipment_cost(self):
        for site in self:
            site.equipment_cost = sum(site.equipment_usage_ids.mapped("cost"))

    def _total_cost_amount(self):
        return super()._total_cost_amount() + self.equipment_cost

    @api.depends("budget", "actual_cost", "labor_cost", "equipment_cost")
    def _compute_total_cost(self):
        super()._compute_total_cost()
