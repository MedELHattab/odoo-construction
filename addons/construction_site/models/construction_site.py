from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConstructionSite(models.Model):
    _name = "construction.site"
    _description = "Construction Site"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, id desc"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(readonly=True, copy=False, default="New")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    partner_id = fields.Many2one("res.partner", string="Client", tracking=True)
    manager_id = fields.Many2one(
        "res.users", string="Site Manager", default=lambda self: self.env.user,
        tracking=True,
    )
    address = fields.Text()
    date_start = fields.Date(string="Start Date", tracking=True)
    date_end = fields.Date(string="Planned End Date", tracking=True)
    budget = fields.Monetary(currency_field="currency_id", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Planned"),
            ("in_progress", "In Progress"),
            ("on_hold", "On Hold"),
            ("done", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    project_id = fields.Many2one("project.project", string="Project", copy=False)
    task_count = fields.Integer(related="project_id.task_count")
    notes = fields.Html()

    _code_company_uniq = models.Constraint(
        "unique(code, company_id)", "The site code must be unique per company."
    )

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for site in self:
            if site.date_start and site.date_end and site.date_end < site.date_start:
                raise ValidationError(
                    self.env._("The planned end date cannot be before the start date.")
                )

    @api.constrains("budget")
    def _check_budget(self):
        for site in self:
            if site.budget < 0:
                raise ValidationError(self.env._("The budget cannot be negative."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "New") == "New":
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code("construction.site") or "New"
                )
        sites = super().create(vals_list)
        for site in sites.filtered(lambda s: not s.project_id):
            site.project_id = self.env["project.project"].create(
                {
                    "name": f"{site.code} - {site.name}",
                    "partner_id": site.partner_id.id,
                    "user_id": site.manager_id.id,
                    "company_id": site.company_id.id,
                }
            )
        return sites

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_hold(self):
        self.write({"state": "on_hold"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open_project(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "res_id": self.project_id.id,
            "view_mode": "form",
        }
