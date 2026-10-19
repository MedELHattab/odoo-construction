from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    site_id = fields.Many2one(
        "construction.site", string="Construction Site", index=True, tracking=True,
        check_company=True,
    )
