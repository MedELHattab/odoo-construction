from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env["res.partner"].create({"name": "Dash client"})
        cls.site = cls.env["construction.site"].create({
            "name": "Dash Site", "partner_id": cls.client.id, "budget": 2000, "markup": 25,
        })
        cls.env["construction.boq.line"].create({
            "site_id": cls.site.id, "name": "Works", "quantity": 1, "unit_cost": 1000, "progress": 100,
        })

    def _bill(self, amount):
        vendor = self.env["res.partner"].create({"name": "Dash vendor"})
        self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": vendor.id, "site_id": self.site.id,
            "invoice_date": "2026-10-01",
            "invoice_line_ids": [Command.create({"name": "W", "quantity": 1, "price_unit": amount})],
        }).action_post()

    def test_budget_used_percent(self):
        self.assertEqual(self.site.budget_used_percent, 0.0)
        self._bill(500)
        self.assertEqual(self.site.budget_used_percent, 25.0)

    def test_budget_used_with_no_budget_is_zero(self):
        site = self.env["construction.site"].create({"name": "No budget"})
        self.assertEqual(site.budget_used_percent, 0.0)

    def test_margin_to_date_is_billed_minus_total_cost(self):
        self.assertEqual(self.site.margin_to_date, 0.0)
        self._bill(600)
        self.assertEqual(self.site.margin_to_date, -600.0, "costs incurred, nothing billed yet")
        statement = self.env["construction.progress.statement"].browse(
            self.site.action_new_progress_statement()["res_id"]
        )
        statement.action_confirm()  # 100% of 1000 + 25% markup
        self.assertEqual(self.site.billed_amount, 1250.0)
        self.assertEqual(self.site.margin_to_date, 650.0)

    def test_kanban_is_the_default_view_and_all_views_compile(self):
        action = self.env.ref("construction_site.action_construction_site")
        self.assertTrue(action.view_mode.startswith("kanban"))
        views = self.env["construction.site"].get_views(
            [(False, "kanban"), (False, "list"), (False, "form")]
        )
        self.assertIn("kanban", views["views"])
        overview = self.env.ref("construction_cost.action_construction_cost_overview")
        self.env["construction.site"].get_views(
            [(view.view_id.id, view.view_mode) for view in overview.view_ids]
        )
