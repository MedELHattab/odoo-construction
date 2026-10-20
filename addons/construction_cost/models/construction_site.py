from odoo import api, fields, models


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    bill_ids = fields.One2many(
        "account.move", "site_id", string="Vendor Bills",
        domain=[("move_type", "in", ("in_invoice", "in_refund"))],
    )
    bill_count = fields.Integer(compute="_compute_actual_cost")
    actual_cost = fields.Monetary(
        compute="_compute_actual_cost", store=True, currency_field="currency_id",
        help="Untaxed total of posted vendor bills minus refunds for this site.",
    )
    budget_after_actual = fields.Monetary(
        compute="_compute_actual_cost", store=True, currency_field="currency_id",
        help="Budget minus actual cost. Negative means over budget.",
    )

    @api.depends("budget", "bill_ids.state", "bill_ids.amount_untaxed_signed")
    def _compute_actual_cost(self):
        # sudo: project users may see site figures without accounting access rights
        moves = self.env["account.move"].sudo()
        bill_domain = [("site_id", "in", self.ids), ("move_type", "in", ("in_invoice", "in_refund"))]
        counts = dict(moves._read_group(bill_domain, ["site_id"], ["__count"]))
        posted = dict(moves._read_group(
            bill_domain + [("state", "=", "posted")], ["site_id"], ["amount_untaxed_signed:sum"],
        ))
        for site in self:
            site.bill_count = counts.get(site, 0)
            # vendor bills carry a negative signed amount in company currency
            site.actual_cost = -posted.get(site, 0.0)
            site.budget_after_actual = site.budget - site.actual_cost

    def action_view_bills(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Vendor Bills"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id), ("move_type", "in", ("in_invoice", "in_refund"))],
            "context": {"default_site_id": self.id, "default_move_type": "in_invoice"},
        }
