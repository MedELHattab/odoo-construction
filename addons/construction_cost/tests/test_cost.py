from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionCost(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Dam", "budget": 1000.0})
        cls.vendor = cls.env["res.partner"].create({"name": "Sub Ltd"})

    def _bill(self, price, move_type="in_invoice", post=True):
        bill = self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": self.vendor.id,
            "site_id": self.site.id,
            "invoice_date": "2026-10-01",
            "invoice_line_ids": [Command.create({"name": "Work", "quantity": 1, "price_unit": price})],
        })
        if post:
            bill.action_post()
        return bill

    def test_draft_bills_not_counted(self):
        self._bill(300, post=False)
        self.assertEqual(self.site.bill_count, 1)
        self.assertEqual(self.site.actual_cost, 0.0)

    def test_posted_bills_are_actual_cost(self):
        self._bill(300)
        self._bill(200)
        self.assertEqual(self.site.actual_cost, 500.0)
        self.assertEqual(self.site.budget_after_actual, 500.0)

    def test_refunds_reduce_actual_cost(self):
        self._bill(300)
        self._bill(100, move_type="in_refund")
        self.assertEqual(self.site.actual_cost, 200.0)

    def test_bill_created_from_po_inherits_site(self):
        po = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "site_id": self.site.id,
        })
        self.assertEqual(po._prepare_invoice()["site_id"], self.site.id)

    def test_bills_action_filters_on_site(self):
        action = self.site.action_view_bills()
        self.assertIn(("site_id", "=", self.site.id), action["domain"])
