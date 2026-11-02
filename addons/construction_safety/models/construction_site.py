from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    punch_ids = fields.One2many("construction.punch.item", "site_id", string="Punch List")
    inspection_ids = fields.One2many("construction.inspection", "site_id", string="Inspections")
    punch_open_count = fields.Integer(compute="_compute_safety_figures")
    inspection_count = fields.Integer(compute="_compute_safety_figures")
    failed_inspection_count = fields.Integer(compute="_compute_safety_figures")

    @api.depends("punch_ids.state", "inspection_ids.result", "inspection_ids.state")
    def _compute_safety_figures(self):
        for site in self:
            site.punch_open_count = len(site.punch_ids.filtered(lambda p: p.state != "verified"))
            site.inspection_count = len(site.inspection_ids)
            site.failed_inspection_count = len(
                site.inspection_ids.filtered(lambda i: i.state == "done" and i.result == "fail")
            )

    def action_view_punch_items(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Punch List"),
            "res_model": "construction.punch.item",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
            "context": {"default_site_id": self.id},
        }

    def action_view_inspections(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Inspections"),
            "res_model": "construction.inspection",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
            "context": {"default_site_id": self.id},
        }
