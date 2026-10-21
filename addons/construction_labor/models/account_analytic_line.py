from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    site_id = fields.Many2one(
        "construction.site", string="Construction Site",
        compute="_compute_site_id", store=True, index=True,
    )

    @api.depends("project_id.site_ids")
    def _compute_site_id(self):
        for line in self:
            line.site_id = line.project_id.site_ids[:1]
