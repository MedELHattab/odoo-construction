from odoo import api, fields, models

COMMITTED_STATES = ("purchase", "done")


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    purchase_order_ids = fields.One2many("purchase.order", "site_id", string="Purchase Orders")
    purchase_order_count = fields.Integer(compute="_compute_purchase_figures")
    committed_cost = fields.Monetary(
        compute="_compute_purchase_figures", currency_field="currency_id",
        help="Untaxed total of confirmed purchase orders for this site.",
    )
    budget_after_commitments = fields.Monetary(
        compute="_compute_purchase_figures", currency_field="currency_id",
        help="Budget minus committed purchase cost. Negative means over budget.",
    )

    @api.depends("budget", "purchase_order_ids.state", "purchase_order_ids.amount_untaxed")
    def _compute_purchase_figures(self):
        # sudo: project users may see site figures without purchase access rights
        orders = self.env["purchase.order"].sudo()
        counts = dict(orders._read_group(
            [("site_id", "in", self.ids)], ["site_id"], ["__count"]
        ))
        committed = dict(orders._read_group(
            [("site_id", "in", self.ids), ("state", "in", COMMITTED_STATES)],
            ["site_id"], ["amount_untaxed:sum"],
        ))
        for site in self:
            site.purchase_order_count = counts.get(site, 0)
            site.committed_cost = committed.get(site, 0.0)
            site.budget_after_commitments = site.budget - site.committed_cost

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Purchase Orders"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
            "context": {"default_site_id": self.id},
        }
