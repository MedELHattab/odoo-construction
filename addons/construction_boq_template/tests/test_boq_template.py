from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestBoqTemplate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.concrete = cls.env["construction.boq.category"].create({"name": "Concrete", "code": "T-03"})
        cls.finish = cls.env["construction.boq.category"].create({"name": "Finishes", "code": "T-09"})
        cls.template = cls.env["construction.boq.template"].create({
            "name": "Villa standard",
            "line_ids": [
                Command.create({"name": "Foundations", "quantity": 10, "unit_cost": 100, "category_id": cls.concrete.id}),
                Command.create({"name": "Painting", "quantity": 4, "unit_cost": 50, "category_id": cls.finish.id}),
            ],
        })
        cls.site = cls.env["construction.site"].create({"name": "Template Site"})

    def _apply(self, site=None, **vals):
        wizard = self.env["construction.boq.template.apply"].create({
            "site_id": (site or self.site).id, "template_id": self.template.id, **vals,
        })
        wizard.action_apply()

    def test_template_total(self):
        self.assertEqual(self.template.total, 1200.0)

    def test_apply_copies_lines_with_categories(self):
        self._apply()
        self.assertEqual(len(self.site.boq_line_ids), 2)
        self.assertEqual(self.site.boq_total, 1200.0)
        self.assertEqual(
            set(self.site.boq_line_ids.mapped("category_id")), {self.concrete, self.finish}
        )

    def test_factor_scales_quantities_not_prices(self):
        self._apply(factor=2)
        self.assertEqual(self.site.boq_total, 2400.0)
        self.assertEqual(sorted(self.site.boq_line_ids.mapped("unit_cost")), [50.0, 100.0])

    def test_apply_appends_by_default_and_can_replace(self):
        self._apply()
        self._apply()
        self.assertEqual(len(self.site.boq_line_ids), 4)
        self._apply(replace=True)
        self.assertEqual(len(self.site.boq_line_ids), 2)

    def test_invalid_factor_rejected(self):
        with self.assertRaises(UserError):
            self._apply(factor=0)

    def test_applying_does_not_change_the_template(self):
        self._apply()
        self.site.boq_line_ids[0].unit_cost = 999
        self.assertEqual(self.template.total, 1200.0)

    def test_save_site_boq_as_template(self):
        self._apply()
        wizard = self.env["construction.boq.template.save"].create({
            "site_id": self.site.id, "name": "Saved copy",
        })
        action = wizard.action_save()
        saved = self.env["construction.boq.template"].browse(action["res_id"])
        self.assertEqual(saved.total, 1200.0)
        self.assertEqual(len(saved.line_ids), 2)

    def test_cannot_save_empty_boq(self):
        wizard = self.env["construction.boq.template.save"].create({"site_id": self.site.id, "name": "Empty"})
        with self.assertRaises(UserError):
            wizard.action_save()

    def test_negative_template_values_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["construction.boq.template.line"].create(
                {"template_id": self.template.id, "name": "Bad", "quantity": -1}
            )

    def test_cost_code_unique_and_display_name(self):
        with self.assertRaises(Exception), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["construction.boq.category"].create({"name": "Dup", "code": "T-03"})
        self.assertEqual(self.concrete.display_name, "[T-03] Concrete")

    def test_roles_and_screens(self):
        viewer = self.env["res.users"].create({
            "name": "tpl viewer", "login": "tpl_viewer", "email": "v@example.com",
            "group_ids": [Command.set([self.env.ref("construction_site.group_construction_viewer").id])],
        })
        self.assertEqual(self.template.with_user(viewer).name, "Villa standard")
        with self.assertRaises(AccessError):
            self.template.with_user(viewer).write({"name": "x"})
        self.env["construction.boq.template"].get_views([(False, "list"), (False, "form")])
        self.env["construction.boq.line"].get_views([(False, "pivot"), (False, "list"), (False, "search")])
        self.env["construction.site"].get_views([(False, "form")])
