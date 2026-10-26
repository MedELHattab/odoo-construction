from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class ConstructionProgressStatement(models.Model):
    _name = "construction.progress.statement"
    _description = "Progress Statement (interim client invoice)"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(readonly=True, copy=False, default="New")
    site_id = fields.Many2one(
        "construction.site", string="Site", required=True, ondelete="restrict",
        index=True, tracking=True,
    )
    company_id = fields.Many2one(related="site_id.company_id", store=True)
    currency_id = fields.Many2one(related="site_id.currency_id")
    partner_id = fields.Many2one(related="site_id.partner_id", string="Client")
    kind = fields.Selection(
        [("progress", "Progress"), ("retention", "Retention release")],
        default="progress", required=True,
    )
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("invoiced", "Invoiced"), ("cancelled", "Cancelled")],
        default="draft", required=True, tracking=True,
    )
    retention_percent = fields.Float(string="Retention (%)")
    line_ids = fields.One2many("construction.progress.statement.line", "statement_id", string="Lines")
    gross_amount = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    retention_amount = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    net_amount = fields.Monetary(
        compute="_compute_amounts", store=True, currency_field="currency_id",
        help="Amount invoiced to the client: gross minus the retention held back.",
    )
    release_amount = fields.Monetary(
        currency_field="currency_id", readonly=True,
        help="For a retention release: the amount of held-back retention being invoiced.",
    )
    invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True, copy=False)
    note = fields.Text()

    @api.depends("line_ids.amount", "retention_percent", "kind", "release_amount", "currency_id")
    def _compute_amounts(self):
        for statement in self:
            rounding = statement.currency_id or statement.site_id.currency_id
            if statement.kind == "retention":
                statement.gross_amount = statement.release_amount
                statement.retention_amount = 0.0
                statement.net_amount = statement.release_amount
                continue
            gross = sum(statement.line_ids.mapped("amount"))
            retention = gross * statement.retention_percent / 100.0
            if rounding:
                gross, retention = rounding.round(gross), rounding.round(retention)
            statement.gross_amount = gross
            statement.retention_amount = retention
            statement.net_amount = gross - retention

    @api.constrains("site_id", "state")
    def _check_single_draft(self):
        for statement in self.filtered(lambda s: s.state == "draft"):
            others = self.search_count([
                ("site_id", "=", statement.site_id.id), ("state", "=", "draft"),
                ("id", "!=", statement.id),
            ])
            if others:
                raise ValidationError(self.env._(
                    "Only one draft progress statement per site is allowed. Invoice or cancel the "
                    "existing draft first."
                ))

    @api.constrains("retention_percent")
    def _check_retention(self):
        for statement in self:
            if not 0.0 <= statement.retention_percent <= 100.0:
                raise ValidationError(self.env._("Retention must be between 0 and 100 percent."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("construction.progress.statement") or "New"
        return super().create(vals_list)

    def unlink(self):
        if any(statement.state == "invoiced" for statement in self):
            raise UserError(self.env._("An invoiced statement cannot be deleted. Credit the invoice instead."))
        return super().unlink()

    # -- workflow -------------------------------------------------------------------------
    def _check_can_invoice(self):
        if not self.env.user.has_group("account.group_account_invoice"):
            raise AccessError(self.env._("You need invoicing rights to issue a client invoice."))
        for statement in self:
            if statement.state != "draft":
                raise UserError(self.env._("Only draft statements can be invoiced."))
            if not statement.partner_id:
                raise UserError(self.env._("Set a client on the site before invoicing."))
            if statement.net_amount <= 0:
                raise UserError(self.env._("There is nothing to invoice on this statement."))

    def action_confirm(self):
        """Create the customer invoice for this statement."""
        self._check_can_invoice()
        for statement in self:
            invoice = self.env["account.move"].create(statement._prepare_invoice_vals())
            statement.write({"invoice_id": invoice.id, "state": "invoiced"})
        return self.action_open_invoice() if len(self) == 1 else True

    def _prepare_invoice_vals(self):
        self.ensure_one()
        lines = []
        if self.kind == "retention":
            lines.append(Command.create({
                "name": self.env._("Retention release - %s", self.site_id.display_name),
                "quantity": 1, "price_unit": self.release_amount,
            }))
        else:
            for line in self.line_ids.filtered(lambda l: l.amount):
                lines.append(Command.create({
                    "name": self.env._(
                        "%(item)s (%(previous).0f%% to %(current).0f%%)",
                        item=line.name, previous=line.previous_progress, current=line.current_progress,
                    ),
                    "quantity": 1, "price_unit": line.amount,
                }))
            if self.retention_amount:
                lines.append(Command.create({
                    "name": self.env._("Retention held back (%s%%)", self.retention_percent),
                    "quantity": 1, "price_unit": -self.retention_amount,
                }))
        return {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": self.date,
            "invoice_origin": self.name,
            "site_id": self.site_id.id,
            "company_id": self.company_id.id,
            "invoice_line_ids": lines,
        }

    def action_cancel(self):
        if any(statement.state != "draft" for statement in self):
            raise UserError(self.env._("Only draft statements can be cancelled."))
        self.write({"state": "cancelled"})

    def _action_open(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "construction.progress.statement",
            "res_id": self.id,
            "view_mode": "form",
        }

    def action_open_invoice(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
        }


class ConstructionProgressStatementLine(models.Model):
    _name = "construction.progress.statement.line"
    _description = "Progress Statement Line"
    _order = "statement_id, sequence, id"

    statement_id = fields.Many2one(
        "construction.progress.statement", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)
    boq_line_id = fields.Many2one(
        "construction.boq.line", string="BoQ line", required=True, ondelete="restrict"
    )
    name = fields.Char(string="Description", required=True)
    currency_id = fields.Many2one(related="statement_id.currency_id")
    contract_value = fields.Monetary(
        currency_field="currency_id", readonly=True,
        help="Selling value of the line when the statement was created (cost plus site markup).",
    )
    previous_progress = fields.Float(string="Previously billed (%)", readonly=True)
    current_progress = fields.Float(string="Billed to date (%)")
    period_progress = fields.Float(string="This period (%)", compute="_compute_amount", store=True)
    amount = fields.Monetary(
        string="This period", compute="_compute_amount", store=True, currency_field="currency_id"
    )

    @api.depends("current_progress", "previous_progress", "contract_value")
    def _compute_amount(self):
        for line in self:
            line.period_progress = line.current_progress - line.previous_progress
            amount = line.contract_value * line.period_progress / 100.0
            line.amount = line.currency_id.round(amount) if line.currency_id else amount

    @api.constrains("current_progress", "previous_progress")
    def _check_progress(self):
        for line in self:
            if line.current_progress > 100.0 or line.current_progress < line.previous_progress - 1e-9:
                raise ValidationError(self.env._(
                    "'%(item)s': progress billed to date must be between the previously billed "
                    "percentage (%(previous).1f%%) and 100%%.",
                    item=line.name, previous=line.previous_progress,
                ))
