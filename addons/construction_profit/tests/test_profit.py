from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionProfit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env["res.partner"].create({"name": "Profit client"})
        # planned cost 1000, selling value 1250 (25% markup)
        cls.site = cls.env["construction.site"].create({
            "name": "Profit Site", "partner_id": cls.client.id, "budget": 1500, "markup": 25,
        })
        cls.line = cls.env["construction.boq.line"].create({
            "site_id": cls.site.id, "name": "Works", "quantity": 1, "unit_cost": 1000,
        })

    def _bill(self, amount):
        vendor = self.env["res.partner"].create({"name": "Profit vendor"})
        self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": vendor.id, "site_id": self.site.id,
            "invoice_date": "2026-10-01",
            "invoice_line_ids": [Command.create({"name": "W", "quantity": 1, "price_unit": amount})],
        }).action_post()

    def _invoice_progress(self):
        statement = self.env["construction.progress.statement"].browse(
            self.site.action_new_progress_statement()["res_id"]
        )
        statement.action_confirm()
        return statement.invoice_id

    def test_forecast_without_progress_uses_the_plan(self):
        self.assertEqual(self.site.forecast_cost, 1000.0)
        self.assertEqual(self.site.forecast_margin, 250.0)
        self.assertEqual(self.site.forecast_margin_percent, 20.0)

    def test_forecast_without_progress_but_with_cost_never_drops_below_cost(self):
        self._bill(1200)
        self.assertEqual(self.site.forecast_cost, 1200.0)

    def test_forecast_extrapolates_cost_by_work_done(self):
        self.line.progress = 50   # earned value 500
        self._bill(600)           # spent 600 for work worth 500 -> 1000 * 600 / 500
        self.assertEqual(self.site.forecast_cost, 1200.0)
        self.assertEqual(self.site.forecast_margin, 50.0)
        self.assertEqual(self.site.forecast_margin_percent, 4.0)

    def test_forecast_at_full_progress_equals_actual_cost(self):
        self.line.progress = 100
        self._bill(900)
        self.assertEqual(self.site.forecast_cost, 900.0)
        self.assertEqual(self.site.forecast_margin, 350.0)

    def test_forecast_uses_budget_when_there_is_no_boq(self):
        site = self.env["construction.site"].create({"name": "No BoQ", "budget": 800})
        self.assertEqual(site.forecast_cost, 800.0)
        self.assertEqual(site.forecast_margin_percent, 0.0, "no contract value, no percentage")

    def test_cash_figures_follow_invoicing_and_payment(self):
        self.line.progress = 40   # 40% of 1250 = 500 billed
        invoice = self._invoice_progress()
        self.assertEqual(self.site.receivable_amount, 0.0, "a draft invoice is not receivable yet")
        invoice.action_post()
        self.assertEqual(self.site.collected_amount, 0.0)
        self.assertEqual(self.site.receivable_amount, invoice.amount_total)
        self._bill(300)
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create({"amount": 200.0}).action_create_payments()
        self.assertEqual(self.site.collected_amount, 200.0)
        self.assertEqual(self.site.receivable_amount, invoice.amount_total - 200.0)
        self.assertEqual(self.site.cash_position, 200.0 - 300.0)

    def test_form_view_compiles(self):
        self.env["construction.site"].get_views([(False, "form")])
