from odoo import api, fields, models
from odoo.exceptions import UserError


class ConstructionPunchItem(models.Model):
    """A defect or unfinished detail to fix before the site is handed over."""
    _name = "construction.punch.item"
    _description = "Construction Punch List Item"
    _inherit = ["mail.thread"]
    _order = "state, priority desc, deadline, id"

    name = fields.Char(string="Defect", required=True, tracking=True)
    site_id = fields.Many2one(
        "construction.site", string="Site", required=True, ondelete="cascade",
        index=True, tracking=True,
    )
    company_id = fields.Many2one(related="site_id.company_id", store=True)
    location = fields.Char(help="Where on site, e.g. Building A, 2nd floor, kitchen.")
    description = fields.Text()
    partner_id = fields.Many2one("res.partner", string="Responsible company", tracking=True)
    user_id = fields.Many2one("res.users", string="Follow-up by", default=lambda self: self.env.user)
    deadline = fields.Date(tracking=True)
    priority = fields.Selection(
        [("0", "Normal"), ("1", "Important"), ("2", "Urgent")], default="0"
    )
    state = fields.Selection(
        [("open", "Open"), ("done", "Fixed"), ("verified", "Verified")],
        default="open", required=True, tracking=True,
    )
    inspection_id = fields.Many2one(
        "construction.inspection", string="Found in inspection", ondelete="set null"
    )
    is_late = fields.Boolean(compute="_compute_is_late")
    attachment_ids = fields.Many2many("ir.attachment", string="Photos")

    @api.depends("state", "deadline")
    def _compute_is_late(self):
        today = fields.Date.context_today(self)
        for item in self:
            item.is_late = bool(item.state == "open" and item.deadline and item.deadline < today)

    def action_done(self):
        self.write({"state": "done"})

    def action_verify(self):
        if any(item.state != "done" for item in self):
            raise UserError(self.env._("Only fixed items can be verified."))
        self.write({"state": "verified"})

    def action_reopen(self):
        self.write({"state": "open"})
