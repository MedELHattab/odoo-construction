from odoo import fields, models


class ConstructionBoqLine(models.Model):
    _inherit = "construction.boq.line"

    category_id = fields.Many2one("construction.boq.category", string="Category", index=True)
