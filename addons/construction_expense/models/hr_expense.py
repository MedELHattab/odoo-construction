from odoo import fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    site_id = fields.Many2one(
        "construction.site", string="Construction Site", index=True, copy=False,
        check_company=True,
    )
