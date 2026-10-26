from odoo import fields, models


class ConstructionBoqLine(models.Model):
    _inherit = "construction.boq.line"

    change_order_id = fields.Many2one(
        "construction.change.order", string="Change order", readonly=True, copy=False,
        ondelete="restrict", index=True,
    )
