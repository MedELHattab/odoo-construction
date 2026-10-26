from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProgressBilling(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env["res.partner"].create({"name": "Billing Client"})
        # cost 1000 + 20% markup = 1200 selling value; 2 lines: 600 and 400 cost
        cls.site = cls.env["construction.site"].create({
            "name": "Billing Site", "partner_id": cls.client.id, "markup": 20, "retention_percent": 10,
        })
        Line = cls.env["construction.boq.line"]
        cls.foundations = Line.create({"site_id": cls.site.id, "name": "Foundations", "quantity": 1, "unit_cost": 600})
        cls.walls = Line.create({"site_id": cls.site.id, "name": "Walls", "quantity": 1, "unit_cost": 400})

    def _statement(self):
        action = self.site.action_new_progress_statement()
        return self.env["construction.progress.statement"].browse(action["res_id"])

    def _set(self, statement, foundations=None, walls=None):
        for line in statement.line_ids:
            if line.boq_line_id == self.foundations and foundations is not None:
                line.current_progress = foundations
            if line.boq_line_id == self.walls and walls is not None:
                line.current_progress = walls

    def test_statement_proposes_work_progress_and_computes_amounts(self):
        self.foundations.progress = 50  # of 720 selling value -> 360
        self.walls.progress = 25        # of 480 selling value -> 120
        statement = self._statement()
        self.assertEqual(statement.gross_amount, 480.0)
        self.assertEqual(statement.retention_amount, 48.0)
        self.assertEqual(statement.net_amount, 432.0)
        self.assertEqual(statement.state, "draft")
        self.assertTrue(statement.name.startswith("PS/"))

    def test_invoice_matches_statement_and_is_a_customer_invoice(self):
        self.foundations.progress = 50
        statement = self._statement()
        statement.action_confirm()
        invoice = statement.invoice_id
        self.assertEqual(invoice.move_type, "out_invoice")
        self.assertEqual(invoice.partner_id, self.client)
        self.assertEqual(invoice.amount_untaxed, statement.net_amount)
        self.assertEqual(invoice.amount_untaxed, 324.0)  # 360 gross - 10% retention
        self.assertEqual(invoice.invoice_origin, statement.name)
        self.assertEqual(statement.state, "invoiced")
        self.assertTrue(any(line.price_unit < 0 for line in invoice.invoice_line_ids), "retention line")

    def test_second_statement_only_bills_the_difference(self):
        self.foundations.progress = 50
        first = self._statement()
        first.action_confirm()
        statement = self._statement()
        foundations_line = statement.line_ids.filtered(lambda l: l.boq_line_id == self.foundations)
        self.assertEqual(foundations_line.previous_progress, 50.0)
        self.assertEqual(statement.gross_amount, 0.0)
        self._set(statement, foundations=80)
        self.assertEqual(statement.gross_amount, 216.0)  # 30% of 720
        statement.action_confirm()
        self.assertEqual(self.site.billed_amount, 360.0 + 216.0)

    def test_site_totals_and_retention_held(self):
        self.foundations.progress = 100
        self.walls.progress = 100
        statement = self._statement()
        statement.action_confirm()
        self.assertEqual(self.site.contract_value, 1200.0)
        self.assertEqual(self.site.billed_amount, 1200.0)
        self.assertEqual(self.site.billed_percent, 100.0)
        self.assertEqual(self.site.retention_held, 120.0)

    def test_retention_release_invoices_the_held_amount_once(self):
        self.foundations.progress = 100
        self.walls.progress = 100
        self._statement().action_confirm()
        action = self.site.action_release_retention()
        release = self.env["construction.progress.statement"].browse(action["res_id"])
        self.assertEqual(release.kind, "retention")
        self.assertEqual(release.net_amount, 120.0)
        release.action_confirm()
        self.assertEqual(release.invoice_id.amount_untaxed, 120.0)
        self.assertEqual(self.site.retention_held, 0.0)
        with self.assertRaises(UserError):
            self.site.action_release_retention()

    def test_cannot_invoice_without_progress_or_client(self):
        statement = self._statement()
        with self.assertRaises(UserError):
            statement.action_confirm()  # nothing to invoice
        statement.action_cancel()
        site = self.env["construction.site"].create({"name": "No client"})
        self.env["construction.boq.line"].create({"site_id": site.id, "name": "X", "quantity": 1, "unit_cost": 100, "progress": 50})
        orphan = self.env["construction.progress.statement"].browse(site.action_new_progress_statement()["res_id"])
        with self.assertRaises(UserError):
            orphan.action_confirm()

    def test_only_one_draft_statement_per_site(self):
        self._statement()
        with self.assertRaises(ValidationError):
            self._statement()

    def test_progress_cannot_go_backwards_or_above_100(self):
        self.foundations.progress = 50
        self._statement().action_confirm()
        statement = self._statement()
        line = statement.line_ids.filtered(lambda l: l.boq_line_id == self.foundations)
        with self.assertRaises(ValidationError):
            line.current_progress = 40
        with self.assertRaises(ValidationError):
            line.current_progress = 101

    def test_invoiced_statement_cannot_be_deleted_or_billed_twice(self):
        self.foundations.progress = 50
        statement = self._statement()
        statement.action_confirm()
        with self.assertRaises(UserError):
            statement.unlink()
        with self.assertRaises(UserError):
            statement.action_confirm()

    def test_values_are_frozen_after_creation(self):
        self.foundations.progress = 50
        statement = self._statement()
        before = statement.gross_amount
        self.foundations.unit_cost = 6000  # later price change must not rewrite the statement
        self.assertEqual(statement.gross_amount, before)

    def test_invoicing_needs_accounting_rights(self):
        self.foundations.progress = 50
        statement = self._statement()
        manager = self.env["res.users"].create({
            "name": "Site mgr", "login": "bill_mgr", "email": "m@example.com",
            "group_ids": [Command.set([self.env.ref("construction_site.group_construction_manager").id])],
        })
        with self.assertRaises(AccessError):
            statement.with_user(manager).action_confirm()

    def test_screens_compile(self):
        self.env["construction.progress.statement"].get_views(
            [(False, "list"), (False, "form"), (False, "search")]
        )
        self.env["construction.site"].get_views([(False, "form")])
        self.assertEqual(
            self.site.action_view_statements()["domain"], [("site_id", "=", self.site.id)]
        )
