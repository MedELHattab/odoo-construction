from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    sign_request_ids = fields.One2many("sign.oca.request", "site_id", string="Signature Requests")
    sign_request_count = fields.Integer(compute="_compute_sign_request_count")

    @api.depends("sign_request_ids")
    def _compute_sign_request_count(self):
        counts = dict(self.env["sign.oca.request"]._read_group(
            [("site_id", "in", self.ids)], ["site_id"], ["__count"]
        ))
        for site in self:
            site.sign_request_count = counts.get(site, 0)

    def action_send_for_signature(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Send for Signature"),
            "res_model": "sign.oca.template.generate",
            "view_mode": "form",
            "target": "new",
            "context": {"default_site_id": self.id},
        }

    def action_view_sign_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Signature Requests"),
            "res_model": "sign.oca.request",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
            "context": {"default_site_id": self.id},
        }
