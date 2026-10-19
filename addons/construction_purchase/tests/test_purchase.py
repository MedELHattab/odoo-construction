from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionPurchase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Bridge", "budget": 1000.0})
        cls.vendor = cls.env["res.partner"].create({"name": "Sub Ltd", "is_subcontractor": True})
        cls.product = cls.env["product.product"].create({"name": "Cement", "type": "consu"})

    def _order(self, price, qty=1, site=True):
        return self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "site_id": self.site.id if site else False,
            "order_line": [(0, 0, {
                "product_id": self.product.id,
                "product_qty": qty,
                "price_unit": price,
            })],
        })

    def test_draft_orders_not_committed(self):
        self._order(100)
        self.assertEqual(self.site.purchase_order_count, 1)
        self.assertEqual(self.site.committed_cost, 0.0)

    def test_confirmed_orders_are_committed(self):
        self._order(100, qty=3).button_confirm()
        self._order(50).button_confirm()
        self.assertEqual(self.site.committed_cost, 350.0)
        self.assertEqual(self.site.budget_after_commitments, 650.0)

    def test_orders_without_site_ignored(self):
        self._order(999, site=False).button_confirm()
        self.assertEqual(self.site.committed_cost, 0.0)

    def test_over_budget_goes_negative(self):
        self._order(1200).button_confirm()
        self.assertEqual(self.site.budget_after_commitments, -200.0)

    def test_open_orders_action_filters_on_site(self):
        action = self.site.action_view_purchase_orders()
        self.assertEqual(action["domain"], [("site_id", "=", self.site.id)])
