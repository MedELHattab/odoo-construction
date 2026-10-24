from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConstructionEquipment(models.Model):
    _name = "construction.equipment"
    _description = "Construction Equipment"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(string="Fleet number", tracking=True)
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [
            ("excavator", "Excavator / loader"),
            ("crane", "Crane / lifting"),
            ("truck", "Truck / transport"),
            ("mixer", "Concrete / mixer"),
            ("scaffolding", "Scaffolding / formwork"),
            ("tool", "Power tools"),
            ("other", "Other"),
        ],
        default="other",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    daily_rate = fields.Monetary(
        string="Daily rate", currency_field="currency_id", tracking=True,
        help="Default cost per day charged to a site. Can be changed per assignment.",
    )
    state = fields.Selection(
        [("available", "Available"), ("maintenance", "In maintenance")],
        default="available", required=True, tracking=True,
    )
    notes = fields.Text()
    usage_ids = fields.One2many("construction.equipment.usage", "equipment_id", string="Assignments")

    _code_company_uniq = models.Constraint(
        "unique(code, company_id)", "The fleet number must be unique per company."
    )

    @api.constrains("daily_rate")
    def _check_rate(self):
        for equipment in self:
            if equipment.daily_rate < 0:
                raise ValidationError(self.env._("The daily rate cannot be negative."))


class ConstructionEquipmentUsage(models.Model):
    _name = "construction.equipment.usage"
    _description = "Equipment Assignment to a Site"
    _order = "date_from desc, id desc"

    site_id = fields.Many2one(
        "construction.site", string="Site", required=True, ondelete="cascade", index=True
    )
    equipment_id = fields.Many2one(
        "construction.equipment", string="Equipment", required=True,
        ondelete="restrict", index=True,
    )
    company_id = fields.Many2one(related="site_id.company_id", store=True)
    currency_id = fields.Many2one(related="site_id.currency_id")
    date_from = fields.Date(string="From", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="To", required=True, default=fields.Date.context_today)
    days = fields.Integer(compute="_compute_days", store=True)
    daily_rate = fields.Monetary(currency_field="currency_id")
    cost = fields.Monetary(compute="_compute_cost", store=True, currency_field="currency_id")

    @api.onchange("equipment_id")
    def _onchange_equipment_id(self):
        if self.equipment_id:
            self.daily_rate = self.equipment_id.daily_rate

    @api.depends("date_from", "date_to")
    def _compute_days(self):
        for usage in self:
            if usage.date_from and usage.date_to and usage.date_to >= usage.date_from:
                usage.days = (usage.date_to - usage.date_from).days + 1
            else:
                usage.days = 0

    @api.depends("days", "daily_rate")
    def _compute_cost(self):
        for usage in self:
            usage.cost = usage.days * usage.daily_rate

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "daily_rate" not in vals and vals.get("equipment_id"):
                vals["daily_rate"] = self.env["construction.equipment"].browse(
                    vals["equipment_id"]
                ).daily_rate
        return super().create(vals_list)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for usage in self:
            if usage.date_to < usage.date_from:
                raise ValidationError(self.env._("'To' cannot be before 'From'."))

    @api.constrains("daily_rate")
    def _check_rate(self):
        for usage in self:
            if usage.daily_rate < 0:
                raise ValidationError(self.env._("The daily rate cannot be negative."))

    @api.constrains("equipment_id", "date_from", "date_to")
    def _check_no_overlap(self):
        for usage in self:
            clash = self.search([
                ("id", "!=", usage.id),
                ("equipment_id", "=", usage.equipment_id.id),
                ("date_from", "<=", usage.date_to),
                ("date_to", ">=", usage.date_from),
            ], limit=1)
            if clash:
                raise ValidationError(self.env._(
                    "%(equipment)s is already assigned to %(site)s from %(start)s to %(end)s.",
                    equipment=usage.equipment_id.display_name,
                    site=clash.site_id.display_name,
                    start=clash.date_from,
                    end=clash.date_to,
                ))
