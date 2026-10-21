from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    log_ids = fields.One2many("construction.site.log", "site_id", string="Daily Logs")
    log_count = fields.Integer(compute="_compute_log_figures")
    incident_count = fields.Integer(compute="_compute_log_figures")
    last_log_date = fields.Date(compute="_compute_log_figures")

    @api.depends("log_ids.date", "log_ids.safety_incident")
    def _compute_log_figures(self):
        for site in self:
            logs = site.log_ids
            site.log_count = len(logs)
            site.incident_count = len(logs.filtered("safety_incident"))
            site.last_log_date = max(logs.mapped("date")) if logs else False

    def action_view_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Daily Logs"),
            "res_model": "construction.site.log",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
            "context": {"default_site_id": self.id},
        }
