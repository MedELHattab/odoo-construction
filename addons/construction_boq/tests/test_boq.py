from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBoq(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env["res.partner"].create({"name": "Client"})
        cls.site = cls.env["construction.site"].create(
            {"name": "Tower", "partner_id": cls.client.id, "budget": 1000.0}
        )
        cls.Line = cls.env["construction.boq.line"]

    def test_totals_and_variance(self):
        self.Line.create({"site_id": self.site.id, "name": "Concrete", "quantity": 10, "unit_cost": 50})
        self.Line.create({"site_id": self.site.id, "name": "Steel", "quantity": 2, "unit_cost": 100})
        self.assertEqual(self.site.boq_total, 700.0)
        self.assertEqual(self.site.budget_variance, 300.0)

    def test_over_budget_is_negative(self):
        self.Line.create({"site_id": self.site.id, "name": "Gold", "quantity": 1, "unit_cost": 1500})
        self.assertEqual(self.site.budget_variance, -500.0)

    def test_negative_values_rejected(self):
        with self.assertRaises(ValidationError):
            self.Line.create({"site_id": self.site.id, "name": "Bad", "quantity": -1, "unit_cost": 1})

    def test_quotation_uses_markup_and_blocks_duplicates(self):
        self.site.markup = 20
        self.Line.create({"site_id": self.site.id, "name": "Concrete", "quantity": 10, "unit_cost": 50})
        self.site.action_create_quotation()
        order = self.site.sale_order_id
        self.assertEqual(order.partner_id, self.client)
        self.assertEqual(order.order_line.price_unit, 60.0)
        self.assertEqual(order.order_line.product_uom_qty, 10)
        with self.assertRaises(UserError):
            self.site.action_create_quotation()

    def test_quotation_requires_client_and_lines(self):
        site = self.env["construction.site"].create({"name": "No client"})
        with self.assertRaises(UserError):
            site.action_create_quotation()
