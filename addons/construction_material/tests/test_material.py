from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionMaterial(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Material Site"})
        cls.vendor = cls.env["res.partner"].create({"name": "Material vendor"})
        cls.cement = cls.env["product.product"].create({"name": "Cement bag", "type": "consu"})
        cls.labour = cls.env["product.product"].create({"name": "Labour service", "type": "service"})

    def _order(self, qty=10, price=5.0, planned="2999-01-01", site=True, confirm=True):
        order = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "site_id": self.site.id if site else False,
            "order_line": [
                Command.create({"product_id": self.cement.id, "product_qty": qty, "price_unit": price,
                                "date_planned": planned}),
                Command.create({"product_id": self.labour.id, "product_qty": 1, "price_unit": 100,
                                "date_planned": planned}),
            ],
        })
        if confirm:
            order.button_confirm()
        return order

    def _rows(self, order):
        self.env.flush_all()
        self.env.invalidate_all()
        return self.env["construction.material"].search([("order_id", "=", order.id)])

    def _receive(self, order, qty):
        picking = order.picking_ids
        picking.move_ids.quantity = qty
        picking.with_context(skip_backorder=True).button_validate()

    def test_only_goods_on_confirmed_site_orders(self):
        (row,) = self._rows(self._order())
        self.assertEqual(row.product_id, self.cement, "services are not materials")
        self.assertEqual((row.ordered_qty, row.received_qty, row.outstanding_qty), (10.0, 0.0, 10.0))
        self.assertEqual((row.ordered_amount, row.outstanding_amount), (50.0, 50.0))
        self.assertFalse(self._rows(self._order(confirm=False)), "draft order")
        self.assertFalse(self._rows(self._order(site=False)), "no site")

    def test_partial_receipt_reduces_what_is_outstanding(self):
        order = self._order()
        self._receive(order, 4)
        (row,) = self._rows(order)
        self.assertEqual((row.received_qty, row.outstanding_qty), (4.0, 6.0))
        self.assertEqual((row.received_amount, row.outstanding_amount), (20.0, 30.0))

    def test_late_only_when_overdue_and_not_fully_delivered(self):
        order = self._order(planned="2020-01-01")
        (row,) = self._rows(order)
        self.assertTrue(row.is_late)
        self._receive(order, 10)
        (row,) = self._rows(order)
        self.assertFalse(row.is_late)
        self.assertEqual(row.outstanding_qty, 0.0)

    def test_views_compile(self):
        self.env["construction.material"].get_views(
            [(False, "list"), (False, "pivot"), (False, "graph"), (False, "search")]
        )
