from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConstructionBoqLine(models.Model):
    _name = "construction.boq.line"
    _description = "Bill of Quantities Line"
    _order = "site_id, sequence, id"

    site_id = fields.Many2one(
        "construction.site", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Description", required=True)
    product_id = fields.Many2one("product.product", string="Product")
    quantity = fields.Float(default=1.0, digits="Product Unit")
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit", raise_if_not_found=False),
    )
    unit_cost = fields.Monetary(currency_field="currency_id")
    subtotal = fields.Monetary(
        compute="_compute_subtotal", store=True, currency_field="currency_id"
    )
    currency_id = fields.Many2one(related="site_id.currency_id", store=True)
    company_id = fields.Many2one(related="site_id.company_id", store=True)

    @api.depends("quantity", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_cost

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.name or self.product_id.display_name
            self.uom_id = self.product_id.uom_id
            self.unit_cost = self.product_id.standard_price

    @api.constrains("quantity", "unit_cost")
    def _check_positive(self):
        for line in self:
            if line.quantity < 0 or line.unit_cost < 0:
                raise ValidationError(
                    self.env._("Quantity and unit cost cannot be negative.")
                )
