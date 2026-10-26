from odoo import fields, models
from odoo.exceptions import UserError


class ConstructionBoqTemplateApply(models.TransientModel):
    _name = "construction.boq.template.apply"
    _description = "Apply a BoQ Template to a Site"

    site_id = fields.Many2one(
        "construction.site", required=True, default=lambda self: self.env.context.get("default_site_id")
    )
    template_id = fields.Many2one("construction.boq.template", required=True)
    factor = fields.Float(
        string="Quantity multiplier", default=1.0,
        help="Scale all template quantities, for example 2 for twice the size.",
    )
    replace = fields.Boolean(string="Replace existing lines")

    def action_apply(self):
        self.ensure_one()
        if self.factor <= 0:
            raise UserError(self.env._("The quantity multiplier must be greater than zero."))
        if self.replace:
            self.site_id.boq_line_ids.unlink()
        self.env["construction.boq.line"].create([
            {
                "site_id": self.site_id.id,
                "sequence": line.sequence,
                "category_id": line.category_id.id,
                "product_id": line.product_id.id,
                "name": line.name,
                "quantity": line.quantity * self.factor,
                "uom_id": line.uom_id.id,
                "unit_cost": line.unit_cost,
            }
            for line in self.template_id.line_ids
        ])
        return {"type": "ir.actions.act_window_close"}


class ConstructionBoqTemplateSave(models.TransientModel):
    _name = "construction.boq.template.save"
    _description = "Save a Site's BoQ as a Template"

    site_id = fields.Many2one(
        "construction.site", required=True, default=lambda self: self.env.context.get("default_site_id")
    )
    name = fields.Char(string="Template name", required=True)

    def action_save(self):
        self.ensure_one()
        if not self.site_id.boq_line_ids:
            raise UserError(self.env._("The site has no bill of quantities lines to save."))
        template = self.env["construction.boq.template"].create({
            "name": self.name,
            "line_ids": [
                (0, 0, {
                    "sequence": line.sequence,
                    "category_id": line.category_id.id,
                    "product_id": line.product_id.id,
                    "name": line.name,
                    "quantity": line.quantity,
                    "uom_id": line.uom_id.id,
                    "unit_cost": line.unit_cost,
                })
                for line in self.site_id.boq_line_ids
            ],
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "construction.boq.template",
            "res_id": template.id,
            "view_mode": "form",
        }
