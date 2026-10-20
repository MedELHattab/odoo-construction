from odoo import api, fields, models


class SignOcaRequest(models.Model):
    _inherit = "sign.oca.request"

    site_id = fields.Many2one("construction.site", string="Construction Site", index=True)


class SignOcaTemplateGenerate(models.TransientModel):
    _inherit = "sign.oca.template.generate"

    site_id = fields.Many2one("construction.site", string="Construction Site")

    @api.onchange("template_id")
    def _onchange_template_id(self):
        roles = self.template_id.item_ids.role_id
        self.signer_ids = [(5, 0, 0)] + [(0, 0, {"role_id": role.id}) for role in roles]

    def _generate_vals(self):
        vals = super()._generate_vals()
        if self.site_id:
            vals["site_id"] = self.site_id.id
        return vals
