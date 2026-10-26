from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class ConstructionSubcontract(models.Model):
    _name = "construction.subcontract"
    _description = "Subcontract"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char(readonly=True, copy=False, default="New")
    title = fields.Char(string="Scope of work", required=True, tracking=True)
    site_id = fields.Many2one(
        "construction.site", string="Site", required=True, ondelete="restrict", index=True, tracking=True
    )
    partner_id = fields.Many2one("res.partner", string="Subcontractor", required=True, tracking=True)
    company_id = fields.Many2one(related="site_id.company_id", store=True)
    currency_id = fields.Many2one(related="site_id.currency_id")
    date_start = fields.Date(string="Start date")
    description = fields.Text(string="Terms and conditions")
    state = fields.Selection(
        [("draft", "Draft"), ("active", "In progress"), ("completed", "Completed"), ("cancelled", "Cancelled")],
        default="draft", required=True, tracking=True,
    )
    contract_amount = fields.Monetary(currency_field="currency_id", tracking=True)
    retention_percent = fields.Float(
        string="Retention (%)", tracking=True,
        help="Share of each certified amount withheld until the subcontractor completes the work.",
    )
    payment_ids = fields.One2many("construction.subcontract.payment", "subcontract_id", string="Payment certificates")
    certified_amount = fields.Monetary(
        compute="_compute_totals", store=True, currency_field="currency_id",
        help="Work certified and billed so far (gross, before retention).",
    )
    retention_released = fields.Monetary(currency_field="currency_id", readonly=True, copy=False)
    retention_held = fields.Monetary(
        compute="_compute_totals", store=True, currency_field="currency_id",
        help="Retention withheld on billed certificates and not yet released.",
    )
    balance = fields.Monetary(
        compute="_compute_totals", store=True, currency_field="currency_id",
        help="Contract amount not yet certified.",
    )

    @api.depends(
        "contract_amount", "retention_released", "payment_ids.state",
        "payment_ids.gross_amount", "payment_ids.retention_amount",
    )
    def _compute_totals(self):
        for contract in self:
            billed = contract.payment_ids.filtered(lambda p: p.state == "billed")
            contract.certified_amount = sum(billed.mapped("gross_amount"))
            contract.retention_held = sum(billed.mapped("retention_amount")) - contract.retention_released
            contract.balance = contract.contract_amount - contract.certified_amount

    @api.constrains("contract_amount", "retention_percent")
    def _check_values(self):
        for contract in self:
            if contract.contract_amount < 0:
                raise ValidationError(self.env._("The contract amount cannot be negative."))
            if not 0.0 <= contract.retention_percent <= 100.0:
                raise ValidationError(self.env._("Retention must be between 0 and 100 percent."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("construction.subcontract") or "New"
        return super().create(vals_list)

    def unlink(self):
        if any(contract.state not in ("draft", "cancelled") for contract in self):
            raise UserError(self.env._("Only draft or cancelled subcontracts can be deleted."))
        return super().unlink()

    # -- workflow -------------------------------------------------------------------------
    def action_activate(self):
        for contract in self:
            if contract.state != "draft":
                raise UserError(self.env._("Only draft subcontracts can be started."))
            if contract.contract_amount <= 0:
                raise UserError(self.env._("Set the contract amount before starting the subcontract."))
        self.write({"state": "active"})

    def action_complete(self):
        for contract in self:
            if contract.state != "active":
                raise UserError(self.env._("Only subcontracts in progress can be completed."))
            if contract.payment_ids.filtered(lambda p: p.state == "draft"):
                raise UserError(self.env._("Bill or cancel the draft payment certificates first."))
        self.write({"state": "completed"})

    def action_cancel(self):
        for contract in self:
            if contract.state not in ("draft", "active"):
                raise UserError(self.env._("This subcontract cannot be cancelled."))
            if contract.payment_ids.filtered(lambda p: p.state == "billed"):
                raise UserError(self.env._("A subcontract with billed certificates cannot be cancelled."))
        self.write({"state": "cancelled"})

    def action_release_retention(self):
        """Record that the withheld retention is now due. The payment itself is made on the vendor bills."""
        for contract in self:
            if contract.state != "completed":
                raise UserError(self.env._("Retention can only be released once the subcontract is completed."))
            if contract.retention_held <= 0:
                raise UserError(self.env._("There is no retention to release."))
        for contract in self:
            amount = contract.retention_held
            contract.retention_released += amount
            contract.message_post(body=self.env._(
                "Retention of %s released. Pay it against the vendor bills of this subcontract.",
                contract.currency_id.format(amount),
            ))

    def action_new_payment(self):
        self.ensure_one()
        payment = self.env["construction.subcontract.payment"].create({"subcontract_id": self.id})
        return {
            "type": "ir.actions.act_window", "res_model": "construction.subcontract.payment",
            "res_id": payment.id, "view_mode": "form",
        }


class ConstructionSubcontractPayment(models.Model):
    _name = "construction.subcontract.payment"
    _description = "Subcontract Payment Certificate"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(readonly=True, copy=False, default="New")
    subcontract_id = fields.Many2one(
        "construction.subcontract", string="Subcontract", required=True, ondelete="restrict", index=True
    )
    site_id = fields.Many2one(related="subcontract_id.site_id", store=True)
    partner_id = fields.Many2one(related="subcontract_id.partner_id", string="Subcontractor")
    company_id = fields.Many2one(related="subcontract_id.company_id", store=True)
    currency_id = fields.Many2one(related="subcontract_id.currency_id")
    date = fields.Date(required=True, default=fields.Date.context_today)
    description = fields.Char(string="Work certified")
    state = fields.Selection(
        [("draft", "Draft"), ("billed", "Billed"), ("cancelled", "Cancelled")],
        default="draft", required=True, tracking=True,
    )
    gross_amount = fields.Monetary(string="Certified amount", currency_field="currency_id", tracking=True)
    retention_percent = fields.Float(string="Retention (%)")
    retention_amount = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    net_amount = fields.Monetary(
        compute="_compute_amounts", store=True, currency_field="currency_id",
        help="Amount to pay now: certified amount minus retention.",
    )
    bill_id = fields.Many2one("account.move", string="Vendor bill", readonly=True, copy=False)

    @api.depends("gross_amount", "retention_percent")
    def _compute_amounts(self):
        for payment in self:
            retention = payment.gross_amount * payment.retention_percent / 100.0
            if payment.currency_id:
                retention = payment.currency_id.round(retention)
            payment.retention_amount = retention
            payment.net_amount = payment.gross_amount - retention

    @api.constrains("gross_amount", "retention_percent")
    def _check_values(self):
        for payment in self:
            if payment.gross_amount < 0:
                raise ValidationError(self.env._("The certified amount cannot be negative."))
            if not 0.0 <= payment.retention_percent <= 100.0:
                raise ValidationError(self.env._("Retention must be between 0 and 100 percent."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("construction.subcontract.payment") or "New"
            if "retention_percent" not in vals and vals.get("subcontract_id"):
                vals["retention_percent"] = self.env["construction.subcontract"].browse(
                    vals["subcontract_id"]
                ).retention_percent
        return super().create(vals_list)

    def unlink(self):
        if any(payment.state == "billed" for payment in self):
            raise UserError(self.env._("A billed certificate cannot be deleted. Credit the vendor bill instead."))
        return super().unlink()

    def action_bill(self):
        """Create the vendor bill for the full certified amount. The retention is only a
        reminder on the bill: the cost is incurred in full, the cash is paid later."""
        if not self.env.user.has_group("account.group_account_invoice"):
            raise AccessError(self.env._("You need invoicing rights to create a vendor bill."))
        for payment in self:
            contract = payment.subcontract_id
            if payment.state != "draft":
                raise UserError(self.env._("Only draft certificates can be billed."))
            if contract.state != "active":
                raise UserError(self.env._("The subcontract must be in progress to bill a certificate."))
            if payment.gross_amount <= 0:
                raise UserError(self.env._("Enter the certified amount before billing."))
            if contract.certified_amount + payment.gross_amount > contract.contract_amount:
                raise UserError(self.env._(
                    "This certificate would bring the total certified to %(total)s, above the contract "
                    "amount of %(contract)s.",
                    total=contract.currency_id.format(contract.certified_amount + payment.gross_amount),
                    contract=contract.currency_id.format(contract.contract_amount),
                ))
            bill = self.env["account.move"].create({
                "move_type": "in_invoice",
                "partner_id": contract.partner_id.id,
                "invoice_date": payment.date,
                "ref": payment.name,
                "invoice_origin": contract.name,
                "site_id": contract.site_id.id,
                "company_id": contract.company_id.id,
                "narration": self.env._(
                    "Subcontract %(contract)s. Retention of %(percent)s%% (%(amount)s) is withheld: "
                    "pay %(net)s now.",
                    contract=contract.name, percent=payment.retention_percent,
                    amount=payment.currency_id.format(payment.retention_amount),
                    net=payment.currency_id.format(payment.net_amount),
                ),
                "invoice_line_ids": [Command.create({
                    "name": payment.description or contract.title,
                    "quantity": 1, "price_unit": payment.gross_amount,
                })],
            })
            payment.write({"bill_id": bill.id, "state": "billed"})

    def action_cancel(self):
        if any(payment.state != "draft" for payment in self):
            raise UserError(self.env._("Only draft certificates can be cancelled."))
        self.write({"state": "cancelled"})

    def action_open_bill(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "res_model": "account.move",
            "res_id": self.bill_id.id, "view_mode": "form",
        }
