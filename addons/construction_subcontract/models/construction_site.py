from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    subcontract_ids = fields.One2many("construction.subcontract", "site_id", string="Subcontracts")
    subcontract_count = fields.Integer(compute="_compute_subcontract_figures")
    subcontract_value = fields.Monetary(
        compute="_compute_subcontract_figures", store=True, currency_field="currency_id",
        help="Value of the subcontracts in progress or completed on this site.",
    )
    subcontract_retention_held = fields.Monetary(
        compute="_compute_subcontract_figures", store=True, currency_field="currency_id",
        help="Retention withheld from subcontractors and not yet released.",
    )

    @api.depends(
        "subcontract_ids.state", "subcontract_ids.contract_amount", "subcontract_ids.retention_held",
    )
    def _compute_subcontract_figures(self):
        for site in self:
            live = site.subcontract_ids.filtered(lambda c: c.state in ("active", "completed"))
            site.subcontract_count = len(site.subcontract_ids.filtered(lambda c: c.state != "cancelled"))
            site.subcontract_value = sum(live.mapped("contract_amount"))
            site.subcontract_retention_held = sum(live.mapped("retention_held"))

    def action_view_subcontracts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Subcontracts"),
            "res_model": "construction.subcontract",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
            "context": {"default_site_id": self.id},
        }
