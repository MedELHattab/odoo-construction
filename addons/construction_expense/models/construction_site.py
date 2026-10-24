from odoo import api, fields, models

# Expenses only count once approved: drafts, submissions and refusals are not spending yet.
COUNTED_EXPENSE_STATES = ("approved", "posted", "in_payment", "paid")


class ConstructionSite(models.Model):
    _inherit = "construction.site"

    expense_ids = fields.One2many("hr.expense", "site_id", string="Expenses")
    expense_count = fields.Integer(compute="_compute_expense_cost")
    expense_cost = fields.Monetary(
        compute="_compute_expense_cost", store=True, currency_field="currency_id",
        help="Approved employee expenses charged to this site, in company currency.",
    )

    @api.depends("expense_ids.state", "expense_ids.total_amount")
    def _compute_expense_cost(self):
        for site in self:
            # sudo: site managers may see the figure without expense access rights
            expenses = site.expense_ids.sudo()
            counted = expenses.filtered(lambda e: e.state in COUNTED_EXPENSE_STATES)
            site.expense_count = len(expenses)
            site.expense_cost = sum(counted.mapped("total_amount"))

    def _total_cost_amount(self):
        return super()._total_cost_amount() + self.expense_cost

    @api.depends("budget", "actual_cost", "labor_cost", "equipment_cost", "expense_cost")
    def _compute_total_cost(self):
        super()._compute_total_cost()

    def action_view_expenses(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Expenses"),
            "res_model": "hr.expense",
            "view_mode": "list,form",
            "domain": [("site_id", "=", self.id)],
            "context": {"default_site_id": self.id},
        }
