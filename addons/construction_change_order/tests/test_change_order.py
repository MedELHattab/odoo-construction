from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestChangeOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "CO Site", "budget": 1000})
        cls.env["construction.boq.line"].create(
            {"site_id": cls.site.id, "name": "Base work", "quantity": 1, "unit_cost": 800}
        )

    def _order(self, **vals):
        return self.env["construction.change.order"].create({
            "title": "Extra terrace", "site_id": self.site.id,
            "line_ids": [
                Command.create({"name": "Slab", "quantity": 2, "unit_cost": 100}),
                Command.create({"name": "Railing", "quantity": 1, "unit_cost": 50}),
            ],
            **vals,
        })

    def test_total_and_reference(self):
        order = self._order()
        self.assertEqual(order.total, 250.0)
        self.assertTrue(order.name.startswith("CO/"))
        self.assertEqual(order.state, "draft")

    def test_approval_adds_boq_lines_and_budget(self):
        order = self._order()
        order.action_approve()
        self.assertEqual(order.state, "approved")
        self.assertEqual(len(order.boq_line_ids), 2)
        self.assertEqual(self.site.boq_total, 800 + 250)
        self.assertEqual(self.site.budget, 1250.0)
        self.assertEqual(self.site.approved_change_total, 250.0)
        self.assertEqual(self.site.change_order_count, 1)
        self.assertEqual(order.boq_line_ids.mapped("change_order_id"), order)

    def test_budget_can_be_left_unchanged(self):
        order = self._order(increase_budget=False)
        order.action_approve()
        self.assertEqual(self.site.budget, 1000.0)
        self.assertEqual(self.site.boq_total, 1050.0)

    def test_workflow_submit_reject_reopen(self):
        order = self._order()
        order.action_submit()
        self.assertEqual(order.state, "submitted")
        order.action_reject()
        self.assertEqual(order.state, "rejected")
        self.assertEqual(self.site.boq_total, 800.0, "rejected work is not added")
        order.action_reset()
        self.assertEqual(order.state, "draft")

    def test_empty_order_cannot_be_sent_or_approved(self):
        order = self.env["construction.change.order"].create({"title": "Empty", "site_id": self.site.id})
        with self.assertRaises(UserError):
            order.action_submit()
        with self.assertRaises(UserError):
            order.action_approve()

    def test_approved_order_is_locked_and_cannot_be_approved_twice(self):
        order = self._order()
        order.action_approve()
        with self.assertRaises(UserError):
            order.write({"title": "Changed"})
        with self.assertRaises(UserError):
            order.unlink()
        with self.assertRaises(UserError):
            order.action_approve()
        self.assertEqual(self.site.budget, 1250.0, "budget increased only once")

    def test_negative_values_rejected(self):
        with self.assertRaises(ValidationError):
            self._order(line_ids=[Command.create({"name": "Bad", "quantity": -1, "unit_cost": 5})])

    def test_roles_and_screens(self):
        viewer = self.env["res.users"].create({
            "name": "co viewer", "login": "co_viewer", "email": "v@example.com",
            "group_ids": [Command.set([self.env.ref("construction_site.group_construction_viewer").id])],
        })
        order = self._order()
        self.assertEqual(order.with_user(viewer).title, "Extra terrace")
        with self.assertRaises(AccessError):
            order.with_user(viewer).action_approve()
        self.env["construction.change.order"].get_views([(False, "list"), (False, "form"), (False, "search")])
        self.env["construction.site"].get_views([(False, "form")])
        self.assertEqual(self.site.action_view_change_orders()["domain"], [("site_id", "=", self.site.id)])
