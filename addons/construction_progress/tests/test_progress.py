from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionProgress(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Tunnel", "budget": 1000.0})
        cls.Line = cls.env["construction.boq.line"]

    def _line(self, cost, progress=0.0):
        return self.Line.create({
            "site_id": self.site.id, "name": "Item", "quantity": 1,
            "unit_cost": cost, "progress": progress,
        })

    def test_new_site_has_zero_progress(self):
        self.assertEqual(self.site.progress_percent, 0.0)
        self.assertEqual(self.site.earned_value, 0.0)

    def test_progress_is_weighted_by_cost(self):
        self._line(100, 50)
        self._line(300, 100)
        self.assertEqual(self.site.earned_value, 350.0)
        self.assertEqual(self.site.progress_percent, 87.5)

    def test_updating_progress_recomputes_site(self):
        line = self._line(200, 0)
        line.progress = 25
        self.assertEqual(self.site.earned_value, 50.0)
        self.assertEqual(self.site.progress_percent, 25.0)

    def test_progress_out_of_range_rejected(self):
        for bad in (-1, 100.5):
            with self.assertRaises(ValidationError):
                self._line(100, bad)

    def test_cost_variance_compares_earned_to_actual(self):
        self._line(400, 50)  # earned 200
        vendor = self.env["res.partner"].create({"name": "Sub"})
        bill = self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": vendor.id, "site_id": self.site.id,
            "invoice_date": "2026-10-01",
            "invoice_line_ids": [Command.create({"name": "Work", "quantity": 1, "price_unit": 300})],
        })
        bill.action_post()
        self.assertEqual(self.site.cost_variance, -100.0)
