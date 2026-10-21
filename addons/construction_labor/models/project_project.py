from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    site_ids = fields.One2many("construction.site", "project_id", string="Construction Sites")
