from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConstructionBoqTemplate(models.Model):
    _name = "construction.boq.template"
    _description = "Bill of Quantities Template"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many("construction.boq.template.line", "template_id", string="Lines", copy=True)
    total = fields.Monetary(compute="_compute_total", currency_field="currency_id")

    @api.depends("line_ids.subtotal")
    def _compute_total(self):
        for template in self:
            template.total = sum(template.line_ids.mapped("subtotal"))


class ConstructionBoqTemplateLine(models.Model):
    _name = "construction.boq.template.line"
    _description = "Bill of Quantities Template Line"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one("construction.boq.template", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one("construction.boq.category", string="Category")
    product_id = fields.Many2one("product.product", string="Product")
    name = fields.Char(string="Description", required=True)
    quantity = fields.Float(default=1.0, digits="Product Unit")
    uom_id = fields.Many2one(
        "uom.uom", string="Unit", required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit", raise_if_not_found=False),
    )
    currency_id = fields.Many2one(related="template_id.currency_id")
    unit_cost = fields.Monetary(currency_field="currency_id")
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True, currency_field="currency_id")

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
                raise ValidationError(self.env._("Quantity and unit cost cannot be negative."))
