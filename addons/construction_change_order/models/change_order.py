from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ConstructionChangeOrder(models.Model):
    _name = "construction.change.order"
    _description = "Change Order"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(readonly=True, copy=False, default="New")
    title = fields.Char(required=True, tracking=True)
    site_id = fields.Many2one(
        "construction.site", string="Site", required=True, ondelete="restrict", index=True, tracking=True
    )
    company_id = fields.Many2one(related="site_id.company_id", store=True)
    currency_id = fields.Many2one(related="site_id.currency_id")
    date = fields.Date(required=True, default=fields.Date.context_today)
    reason = fields.Text(help="Why the extra work is needed and who requested it.")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Sent to client"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft", required=True, tracking=True,
    )
    increase_budget = fields.Boolean(
        string="Increase site budget", default=True,
        help="When approved, add the cost of this change order to the site budget.",
    )
    line_ids = fields.One2many("construction.change.order.line", "change_order_id", string="Lines", copy=True)
    total = fields.Monetary(compute="_compute_total", store=True, currency_field="currency_id")
    boq_line_ids = fields.One2many("construction.boq.line", "change_order_id", string="BoQ lines created")

    @api.depends("line_ids.subtotal")
    def _compute_total(self):
        for order in self:
            order.total = sum(order.line_ids.mapped("subtotal"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("construction.change.order") or "New"
        return super().create(vals_list)

    def write(self, vals):
        if self.filtered(lambda o: o.state == "approved") and set(vals) - {"note", "message_follower_ids"}:
            raise UserError(self.env._("An approved change order is locked."))
        return super().write(vals)

    def unlink(self):
        if any(order.state == "approved" for order in self):
            raise UserError(self.env._("An approved change order cannot be deleted."))
        return super().unlink()

    # -- workflow -------------------------------------------------------------------------
    def action_submit(self):
        for order in self:
            if order.state != "draft":
                raise UserError(self.env._("Only draft change orders can be sent."))
            if not order.line_ids:
                raise UserError(self.env._("Add at least one line before sending the change order."))
        self.write({"state": "submitted"})

    def action_approve(self):
        for order in self:
            if order.state not in ("draft", "submitted"):
                raise UserError(self.env._("Only draft or sent change orders can be approved."))
            if not order.line_ids:
                raise UserError(self.env._("Add at least one line before approving the change order."))
        for order in self:
            self.env["construction.boq.line"].create([
                {
                    "site_id": order.site_id.id,
                    "change_order_id": order.id,
                    "name": line.name,
                    "product_id": line.product_id.id,
                    "quantity": line.quantity,
                    "uom_id": line.uom_id.id,
                    "unit_cost": line.unit_cost,
                }
                for line in order.line_ids
            ])
            if order.increase_budget:
                order.site_id.budget += order.total
            order.state = "approved"
            order.site_id.message_post(body=self.env._(
                "Change order %(name)s approved: %(amount)s added to the bill of quantities.",
                name=order.name, amount=order.currency_id.format(order.total),
            ))

    def action_reject(self):
        for order in self:
            if order.state not in ("draft", "submitted"):
                raise UserError(self.env._("Only draft or sent change orders can be rejected."))
        self.write({"state": "rejected"})

    def action_reset(self):
        for order in self:
            if order.state != "rejected":
                raise UserError(self.env._("Only rejected change orders can be reopened."))
        self.write({"state": "draft"})


class ConstructionChangeOrderLine(models.Model):
    _name = "construction.change.order.line"
    _description = "Change Order Line"
    _order = "change_order_id, sequence, id"

    change_order_id = fields.Many2one("construction.change.order", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one("product.product", string="Product")
    name = fields.Char(string="Description", required=True)
    quantity = fields.Float(default=1.0, digits="Product Unit")
    uom_id = fields.Many2one(
        "uom.uom", string="Unit", required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit", raise_if_not_found=False),
    )
    currency_id = fields.Many2one(related="change_order_id.currency_id")
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
