from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionExpense(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Expense Site", "budget": 5000})
        cls.employee = cls.env["hr.employee"].create({"name": "Foreman"})
        cls.product = cls.env.ref("hr_expense.product_product_no_cost")

    def _expense(self, amount, site=True):
        return self.env["hr.expense"].create({
            "name": "Fuel", "employee_id": self.employee.id, "product_id": self.product.id,
            "total_amount_currency": amount, "payment_mode": "own_account",
            "site_id": self.site.id if site else False,
        })

    def _approve(self, expense):
        expense.action_submit()
        expense.action_approve()
        return expense

    def test_draft_expenses_do_not_count_until_approved(self):
        expense = self._expense(120)
        self.assertEqual(self.site.expense_count, 1)
        self.assertEqual(expense.state, "draft")
        self.assertEqual(self.site.expense_cost, 0)
        # without an approval rule Odoo approves on submit, which is when it starts to count
        expense.action_submit()
        self.assertEqual(expense.state, "approved")
        self.assertEqual(self.site.expense_cost, 120)

    def test_approved_expenses_count(self):
        self._approve(self._expense(120))
        self._approve(self._expense(80))
        self.assertEqual(self.site.expense_cost, 200)

    def test_expenses_without_site_ignored(self):
        self._approve(self._expense(999, site=False))
        self.assertEqual(self.site.expense_cost, 0)

    def test_expense_cost_flows_into_total_cost(self):
        self._approve(self._expense(150))
        self.assertEqual(self.site.total_cost, 150)
        self.assertEqual(self.site.budget_after_total, 4850)
        # the equipment source added by the previous module still counts
        equipment = self.env["construction.equipment"].create({"name": "Mixer", "daily_rate": 100})
        self.env["construction.equipment.usage"].create({
            "site_id": self.site.id, "equipment_id": equipment.id,
            "date_from": "2026-11-01", "date_to": "2026-11-02",
        })
        self.assertEqual(self.site.total_cost, 350)

    def test_refused_expense_is_removed_from_cost(self):
        expense = self._expense(150)
        expense.action_submit()
        if expense.state != "approved":
            expense.action_approve()
        self.assertEqual(self.site.expense_cost, 150)
        expense._do_refuse("No receipt")
        self.assertEqual(expense.state, "refused")
        self.assertEqual(self.site.expense_cost, 0)

    def test_screens_and_report(self):
        self._approve(self._expense(75))
        self.env["hr.expense"].get_views([(False, "form")])
        self.env["construction.site"].get_views([(False, "form"), (False, "graph"), (False, "pivot")])
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "construction_report.report_site_cost", self.site.ids
        )
        text = html.decode()
        self.assertIn("Approved employee expenses", text)
        self.assertIn("Fuel", text)
        self.assertEqual(self.site.action_view_expenses()["domain"], [("site_id", "=", self.site.id)])

    def test_report_renders_in_every_active_language(self):
        """Inherited report sections must not depend on English text, or printing breaks
        as soon as a user works in French or Arabic."""
        languages = self.env["res.lang"].search([("active", "=", True)]).mapped("code")
        self.assertTrue(languages)
        for lang in languages:
            html, _fmt = self.env["ir.actions.report"].with_context(lang=lang)._render_qweb_html(
                "construction_report.report_site_cost", self.site.ids
            )
            text = html.decode()
            self.assertIn(self.site.name, text, f"report did not render for {lang}")
            self.assertIn(self.site.code, text, f"site code missing in {lang}")
            # the sections injected by other modules are all present, whatever the language
            self.assertGreaterEqual(text.count("<h5"), 6, f"sections missing in {lang}")
