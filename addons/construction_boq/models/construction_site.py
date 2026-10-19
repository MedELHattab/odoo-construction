from odoo import api, fields, models
from odoo.exceptions import UserError


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    boq_line_ids = fields.One2many("construction.boq.line", "site_id", string="BoQ Lines")
    boq_total = fields.Monetary(
        string="BoQ Total", compute="_compute_boq_total", store=True,
        currency_field="currency_id",
    )
    budget_variance = fields.Monetary(
        string="Budget Remaining", compute="_compute_boq_total", store=True,
        currency_field="currency_id",
        help="Budget minus bill of quantities total. Negative means over budget.",
    )
    markup = fields.Float(
        string="Markup (%)", help="Margin applied to cost when creating a quotation."
    )
    sale_order_id = fields.Many2one("sale.order", string="Quotation", copy=False, readonly=True)

    @api.depends("boq_line_ids.subtotal", "budget")
    def _compute_boq_total(self):
        for site in self:
            site.boq_total = sum(site.boq_line_ids.mapped("subtotal"))
            site.budget_variance = site.budget - site.boq_total

    def action_create_quotation(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(self.env._("Set a client on the site before creating a quotation."))
        if not self.boq_line_ids:
            raise UserError(self.env._("Add bill of quantities lines first."))
        if self.sale_order_id:
            raise UserError(self.env._("A quotation already exists for this site."))
        factor = 1 + self.markup / 100.0
        lines = []
        for line in self.boq_line_ids:
            vals = {
                "name": line.name,
                "product_uom_qty": line.quantity,
                "product_uom_id": line.uom_id.id,
                "price_unit": line.unit_cost * factor,
            }
            if line.product_id:
                vals["product_id"] = line.product_id.id
            lines.append((0, 0, vals))
        self.sale_order_id = self.env["sale.order"].create(
            {
                "partner_id": self.partner_id.id,
                "origin": self.code,
                "company_id": self.company_id.id,
                "order_line": lines,
            }
        )
        return self.action_open_quotation()

    def action_open_quotation(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "view_mode": "form",
        }
