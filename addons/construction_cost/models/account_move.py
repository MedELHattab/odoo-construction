from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    site_id = fields.Many2one(
        "construction.site", string="Construction Site", index=True, copy=False,
        check_company=True,
    )
