from odoo import fields, models


class ConstructionBoqCategory(models.Model):
    _name = "construction.boq.category"
    _description = "BoQ Cost Category"
    _order = "sequence, code, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(help="Short cost code, for example 03-CON.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint("unique(code)", "The cost code must be unique.")

    def _compute_display_name(self):
        for category in self:
            category.display_name = f"[{category.code}] {category.name}" if category.code else category.name
