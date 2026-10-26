from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    change_order_ids = fields.One2many("construction.change.order", "site_id", string="Change Orders")
    change_order_count = fields.Integer(compute="_compute_change_orders")
    approved_change_total = fields.Monetary(
        compute="_compute_change_orders", store=True, currency_field="currency_id",
        help="Cost of all approved change orders on this site.",
    )

    @api.depends("change_order_ids.state", "change_order_ids.total")
    def _compute_change_orders(self):
        for site in self:
            orders = site.change_order_ids
            site.change_order_count = len(orders)
            site.approved_change_total = sum(orders.filtered(lambda o: o.state == "approved").mapped("total"))

    def action_view_change_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Change Orders"),
            "res_model": "construction.change.order",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
            "context": {"default_site_id": self.id},
        }
