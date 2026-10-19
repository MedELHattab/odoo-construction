from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConstructionBoqLine(models.Model):
    _inherit = "construction.boq.line"

    progress = fields.Float(string="Progress (%)", default=0.0)
    earned_value = fields.Monetary(
        compute="_compute_earned_value", store=True, currency_field="currency_id",
        help="Planned cost of the work completed so far (subtotal x progress).",
    )

    @api.depends("subtotal", "progress")
    def _compute_earned_value(self):
        for line in self:
            line.earned_value = line.subtotal * line.progress / 100.0

    @api.constrains("progress")
    def _check_progress(self):
        for line in self:
            if not 0.0 <= line.progress <= 100.0:
                raise ValidationError(self.env._("Progress must be between 0 and 100."))
