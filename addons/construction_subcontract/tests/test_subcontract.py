from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSubcontract(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Sub Site", "budget": 10000})
        cls.sub = cls.env["res.partner"].create({"name": "Steel Works", "is_subcontractor": True})
        cls.contract = cls.env["construction.subcontract"].create({
            "title": "Steel frame", "site_id": cls.site.id, "partner_id": cls.sub.id,
            "contract_amount": 5000, "retention_percent": 10,
        })

    def _payment(self, amount, contract=None):
        return self.env["construction.subcontract.payment"].create({
            "subcontract_id": (contract or self.contract).id, "gross_amount": amount,
            "description": "Level 1",
        })

    def test_new_contract_defaults(self):
        self.assertTrue(self.contract.name.startswith("SC/"))
        self.assertEqual(self.contract.state, "draft")
        self.assertEqual(self.contract.balance, 5000.0)

    def test_payments_cannot_be_billed_before_the_contract_starts(self):
        payment = self._payment(1000)
        with self.assertRaises(UserError):
            payment.action_bill()

    def test_start_requires_an_amount(self):
        empty = self.env["construction.subcontract"].create(
            {"title": "No price", "site_id": self.site.id, "partner_id": self.sub.id}
        )
        with self.assertRaises(UserError):
            empty.action_activate()

    def test_payment_amounts_and_retention_default_from_contract(self):
        self.contract.action_activate()
        payment = self._payment(2000)
        self.assertEqual(payment.retention_percent, 10.0)
        self.assertEqual(payment.retention_amount, 200.0)
        self.assertEqual(payment.net_amount, 1800.0)

    def test_bill_is_for_the_full_certified_amount_and_counts_as_site_cost(self):
        self.contract.action_activate()
        payment = self._payment(2000)
        payment.action_bill()
        bill = payment.bill_id
        self.assertEqual(bill.move_type, "in_invoice")
        self.assertEqual(bill.partner_id, self.sub)
        self.assertEqual(bill.site_id, self.site)
        self.assertEqual(bill.amount_untaxed, 2000.0, "retention is withheld cash, not a lower cost")
        note = str(bill.narration).replace(",", "").replace("&nbsp;", " ")  # ignore number formatting
        self.assertIn("1800.00", note, "the bill tells accounts to pay the net amount now")
        self.assertIn("200.00", note, "and how much retention is withheld")
        self.assertEqual(payment.state, "billed")
        bill.action_post()
        self.assertEqual(self.site.actual_cost, 2000.0)

    def test_totals_and_retention_held(self):
        self.contract.action_activate()
        self._payment(2000).action_bill()
        self._payment(1000).action_bill()
        self.assertEqual(self.contract.certified_amount, 3000.0)
        self.assertEqual(self.contract.balance, 2000.0)
        self.assertEqual(self.contract.retention_held, 300.0)
        self.assertEqual(self.site.subcontract_value, 5000.0)
        self.assertEqual(self.site.subcontract_retention_held, 300.0)
        self.assertEqual(self.site.subcontract_count, 1)

    def test_cannot_certify_more_than_the_contract(self):
        self.contract.action_activate()
        self._payment(4000).action_bill()
        with self.assertRaises(UserError):
            self._payment(1500).action_bill()

    def test_complete_then_release_retention(self):
        self.contract.action_activate()
        self._payment(5000).action_bill()
        with self.assertRaises(UserError):
            self.contract.action_release_retention()  # not completed yet
        draft = self._payment(0)
        with self.assertRaises(UserError):
            self.contract.action_complete()  # a draft certificate is still open
        draft.action_cancel()
        self.contract.action_complete()
        self.contract.action_release_retention()
        self.assertEqual(self.contract.retention_held, 0.0)
        self.assertEqual(self.contract.retention_released, 500.0)
        with self.assertRaises(UserError):
            self.contract.action_release_retention()

    def test_cancel_rules_and_locking(self):
        self.contract.action_activate()
        payment = self._payment(1000)
        payment.action_bill()
        with self.assertRaises(UserError):
            self.contract.action_cancel()
        with self.assertRaises(UserError):
            payment.unlink()
        with self.assertRaises(UserError):
            self.contract.unlink()
        with self.assertRaises(UserError):
            payment.action_bill()  # not billed twice

    def test_invalid_values_rejected(self):
        with self.assertRaises(ValidationError):
            self.contract.retention_percent = 150
        with self.assertRaises(ValidationError):
            self._payment(-5)

    def test_billing_needs_accounting_rights(self):
        self.contract.action_activate()
        payment = self._payment(500)
        manager = self.env["res.users"].create({
            "name": "sub mgr", "login": "sub_mgr", "email": "sm@example.com",
            "group_ids": [Command.set([self.env.ref("construction_site.group_construction_manager").id])],
        })
        with self.assertRaises(AccessError):
            payment.with_user(manager).action_bill()

    def test_screens_compile(self):
        self.env["construction.subcontract"].get_views([(False, "list"), (False, "form"), (False, "search")])
        self.env["construction.subcontract.payment"].get_views([(False, "form")])
        self.env["construction.site"].get_views([(False, "form")])
        self.assertEqual(self.site.action_view_subcontracts()["domain"], [("site_id", "=", self.site.id)])
