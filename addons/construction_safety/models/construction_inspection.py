from odoo import api, fields, models
from odoo.exceptions import UserError


class ConstructionInspection(models.Model):
    """A checklist walk-through of the site (safety, quality, pre-pour...)."""
    _name = "construction.inspection"
    _description = "Construction Site Inspection"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(string="Inspection", required=True, tracking=True)
    site_id = fields.Many2one(
        "construction.site", string="Site", required=True, ondelete="cascade",
        index=True, tracking=True,
    )
    company_id = fields.Many2one(related="site_id.company_id", store=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    inspector_id = fields.Many2one("res.users", string="Inspector", default=lambda self: self.env.user)
    category = fields.Selection(
        [("safety", "Safety"), ("quality", "Quality"), ("other", "Other")],
        default="safety", required=True,
    )
    state = fields.Selection(
        [("draft", "In progress"), ("done", "Completed")], default="draft", tracking=True
    )
    line_ids = fields.One2many(
        "construction.inspection.line", "inspection_id", string="Checklist", copy=True
    )
    punch_ids = fields.One2many("construction.punch.item", "inspection_id", string="Punch items")
    fail_count = fields.Integer(compute="_compute_result", store=True)
    result = fields.Selection(
        [("pass", "Passed"), ("fail", "Failed")], compute="_compute_result", store=True
    )

    @api.depends("line_ids.result")
    def _compute_result(self):
        for insp in self:
            insp.fail_count = len(insp.line_ids.filtered(lambda l: l.result == "fail"))
            insp.result = "fail" if insp.fail_count else "pass"

    def action_complete(self):
        for insp in self:
            if not insp.line_ids:
                raise UserError(self.env._("Add at least one checklist item first."))
            if insp.line_ids.filtered(lambda l: not l.result):
                raise UserError(self.env._("Answer every checklist item before completing."))
        self.write({"state": "done"})

    def action_reopen(self):
        self.write({"state": "draft"})

    def action_create_punch_items(self):
        """One punch item per failed line that does not have one yet."""
        Punch = self.env["construction.punch.item"]
        for insp in self:
            for line in insp.line_ids.filtered(lambda l: l.result == "fail" and not l.punch_id):
                line.punch_id = Punch.create({
                    "name": line.name,
                    "description": line.note,
                    "site_id": insp.site_id.id,
                    "inspection_id": insp.id,
                    "priority": "1",
                })


class ConstructionInspectionLine(models.Model):
    _name = "construction.inspection.line"
    _description = "Construction Inspection Checklist Item"
    _order = "sequence, id"

    inspection_id = fields.Many2one("construction.inspection", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Check", required=True)
    result = fields.Selection([("pass", "OK"), ("fail", "Not OK"), ("na", "N/A")])
    note = fields.Char()
    punch_id = fields.Many2one(
        "construction.punch.item", string="Punch item", copy=False, ondelete="set null"
    )
