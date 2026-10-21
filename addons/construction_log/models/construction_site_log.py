from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConstructionSiteLog(models.Model):
    _name = "construction.site.log"
    _description = "Construction Site Daily Log"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    site_id = fields.Many2one(
        "construction.site", string="Site", required=True, ondelete="cascade",
        index=True, tracking=True,
    )
    company_id = fields.Many2one(related="site_id.company_id", store=True)
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    author_id = fields.Many2one(
        "res.users", string="Author", default=lambda self: self.env.user, readonly=True
    )
    weather = fields.Selection(
        [
            ("sunny", "Sunny"),
            ("cloudy", "Cloudy"),
            ("rain", "Rain"),
            ("wind", "Strong wind"),
            ("storm", "Storm"),
            ("heat", "Extreme heat"),
            ("cold", "Cold / frost"),
        ],
        default="sunny",
    )
    workers_count = fields.Integer(string="Workers on site")
    work_done = fields.Text(string="Work done", required=True)
    issues = fields.Text(string="Issues / delays")
    safety_incident = fields.Boolean(string="Safety incident", tracking=True)
    incident_details = fields.Text()
    attachment_ids = fields.Many2many(
        "ir.attachment", string="Photos & documents",
        help="Site photos, delivery notes or any supporting document.",
    )

    _site_date_uniq = models.Constraint(
        "unique(site_id, date)", "There is already a log for this site on that date."
    )

    @api.constrains("safety_incident", "incident_details")
    def _check_incident_details(self):
        for log in self:
            if log.safety_incident and not (log.incident_details or "").strip():
                raise ValidationError(
                    self.env._("Describe the safety incident before saving the log.")
                )

    @api.constrains("workers_count")
    def _check_workers(self):
        for log in self:
            if log.workers_count < 0:
                raise ValidationError(self.env._("The number of workers cannot be negative."))
