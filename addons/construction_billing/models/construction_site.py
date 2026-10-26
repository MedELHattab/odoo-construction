from odoo import api, fields, models
from odoo.exceptions import UserError


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    retention_percent = fields.Float(
        string="Retention (%)", tracking=True,
        help="Share of each progress invoice held back until the end of the works.",
    )
    statement_ids = fields.One2many("construction.progress.statement", "site_id", string="Progress Statements")
    statement_count = fields.Integer(compute="_compute_statement_count")
    billed_amount = fields.Monetary(
        compute="_compute_billing", store=True, currency_field="currency_id",
        help="Gross value of the work invoiced to the client so far (before retention).",
    )
    contract_value = fields.Monetary(
        compute="_compute_contract_value", currency_field="currency_id",
        help="Total selling value of the bill of quantities (cost plus markup).",
    )
    billed_percent = fields.Float(compute="_compute_billing", store=True, string="Billed (%)")
    retention_held = fields.Monetary(
        compute="_compute_billing", store=True, currency_field="currency_id",
        help="Retention withheld on invoiced statements and not yet released.",
    )

    @api.depends("statement_ids")
    def _compute_statement_count(self):
        counts = dict(self.env["construction.progress.statement"]._read_group(
            [("site_id", "in", self.ids), ("state", "!=", "cancelled")], ["site_id"], ["__count"]
        ))
        for site in self:
            site.statement_count = counts.get(site, 0)

    @api.depends("boq_total", "markup")
    def _compute_contract_value(self):
        for site in self:
            site.contract_value = site.boq_total * (1 + site.markup / 100.0)

    @api.depends(
        "statement_ids.state", "statement_ids.kind", "statement_ids.gross_amount",
        "statement_ids.retention_amount", "statement_ids.release_amount", "boq_total", "markup",
    )
    def _compute_billing(self):
        for site in self:
            invoiced = site.statement_ids.filtered(lambda s: s.state == "invoiced")
            progress = invoiced.filtered(lambda s: s.kind == "progress")
            releases = invoiced.filtered(lambda s: s.kind == "retention")
            site.billed_amount = sum(progress.mapped("gross_amount"))
            site.retention_held = sum(progress.mapped("retention_amount")) - sum(releases.mapped("release_amount"))
            total = site.boq_total * (1 + site.markup / 100.0)
            site.billed_percent = site.billed_amount / total * 100.0 if total else 0.0

    # -- actions --------------------------------------------------------------------------
    def action_new_progress_statement(self):
        self.ensure_one()
        if not self.boq_line_ids:
            raise UserError(self.env._("Add bill of quantities lines first."))
        factor = 1 + self.markup / 100.0
        Statement = self.env["construction.progress.statement"]
        Line = self.env["construction.progress.statement.line"]
        billed = self._billed_progress_by_line()
        statement = Statement.create({
            "site_id": self.id, "retention_percent": self.retention_percent, "kind": "progress",
        })
        Line.create([
            {
                "statement_id": statement.id,
                "boq_line_id": line.id,
                "sequence": line.sequence,
                "name": line.name,
                "contract_value": line.subtotal * factor,
                "previous_progress": billed.get(line.id, 0.0),
                # propose what the work progress says, never less than what was already billed
                "current_progress": max(line.progress, billed.get(line.id, 0.0)),
            }
            for line in self.boq_line_ids
        ])
        return statement._action_open()

    def _billed_progress_by_line(self):
        """Highest percentage already invoiced for each BoQ line."""
        lines = self.env["construction.progress.statement.line"].search([
            ("statement_id.site_id", "=", self.id),
            ("statement_id.state", "=", "invoiced"),
            ("statement_id.kind", "=", "progress"),
        ])
        billed = {}
        for line in lines:
            billed[line.boq_line_id.id] = max(billed.get(line.boq_line_id.id, 0.0), line.current_progress)
        return billed

    def action_release_retention(self):
        self.ensure_one()
        if self.retention_held <= 0:
            raise UserError(self.env._("There is no retention to release on this site."))
        statement = self.env["construction.progress.statement"].create({
            "site_id": self.id, "kind": "retention", "release_amount": self.retention_held,
        })
        return statement._action_open()

    def action_view_statements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Progress Statements"),
            "res_model": "construction.progress.statement",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
            "context": {"default_site_id": self.id},
        }
