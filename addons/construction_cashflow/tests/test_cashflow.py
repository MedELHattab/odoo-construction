from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionCashflow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env["res.partner"].create({"name": "Cash client"})
        cls.vendor = cls.env["res.partner"].create({"name": "Cash vendor"})
        cls.site = cls.env["construction.site"].create({
            "name": "Cash Site", "partner_id": cls.client.id, "retention_percent": 10,
            "date_end": "2027-03-15",
        })
        cls.line = cls.env["construction.boq.line"].create({
            "site_id": cls.site.id, "name": "Works", "quantity": 1, "unit_cost": 1000,
        })

    def _rows(self, kind=None):
        self.env.flush_all()
        domain = [("site_id", "=", self.site.id)]
        if kind:
            domain.append(("kind", "=", kind))
        return self.env["construction.cashflow"].search(domain)

    def _bill(self, amount, due):
        bill = self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": self.vendor.id, "site_id": self.site.id,
            "invoice_date": "2026-11-01", "invoice_date_due": due,
            "invoice_line_ids": [Command.create({"name": "W", "quantity": 1, "price_unit": amount})],
        })
        bill.action_post()
        return bill

    def _invoice(self, progress, due):
        self.line.progress = progress
        statement = self.env["construction.progress.statement"].browse(
            self.site.action_new_progress_statement()["res_id"]
        )
        statement.action_confirm()
        statement.invoice_id.invoice_date_due = due
        statement.invoice_id.action_post()
        return statement.invoice_id

    def _pay(self, move, amount):
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=move.ids
        ).create({"amount": amount}).action_create_payments()

    def test_empty_site_has_no_rows(self):
        self.assertFalse(self._rows())

    def test_open_vendor_bill_is_money_out_on_its_due_date(self):
        self._bill(400, "2026-12-10")
        (row,) = self._rows()
        self.assertEqual((row.kind, row.outflow, row.inflow, row.net), ("payment", 400.0, 0.0, -400.0))
        self.assertEqual(row.date, fields.Date.to_date("2026-12-10"))

    def test_open_client_invoice_is_money_in_net_of_retention(self):
        invoice = self._invoice(50, "2026-12-20")  # 500 gross, 50 retention -> 450 invoiced
        (row,) = self._rows("receipt")
        self.assertEqual(invoice.amount_total, 450.0)
        self.assertEqual((row.inflow, row.net, row.move_id), (450.0, 450.0, invoice))

    def test_retention_held_is_money_in_on_the_planned_end_date(self):
        self._invoice(50, "2026-12-20")
        (row,) = self._rows("retention")
        self.assertEqual((row.inflow, row.date), (50.0, fields.Date.to_date("2027-03-15")))

    def test_retention_needs_a_planned_end_date(self):
        self.site.date_end = False
        self._invoice(50, "2026-12-20")
        self.assertFalse(self._rows("retention"))

    def test_payments_reduce_what_is_still_expected(self):
        bill = self._bill(400, "2026-12-10")
        self._pay(bill, 150)
        (row,) = self._rows()
        self.assertEqual(row.outflow, 250.0)
        self._pay(bill, 250)
        self.assertFalse(self._rows(), "a fully paid bill is no longer expected")

    def test_draft_invoices_and_bills_are_ignored(self):
        self.line.progress = 50
        self.env["construction.progress.statement"].browse(
            self.site.action_new_progress_statement()["res_id"]
        ).action_confirm()  # the invoice exists but is still a draft
        self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": self.vendor.id, "site_id": self.site.id,
            "invoice_date": "2026-11-01",
            "invoice_line_ids": [Command.create({"name": "W", "quantity": 1, "price_unit": 99})],
        })
        self.assertFalse(self._rows("receipt"))
        self.assertFalse(self._rows("payment"))

    def test_bills_without_a_site_are_not_in_the_forecast(self):
        self.env.flush_all()
        before = self.env["construction.cashflow"].search_count([])
        self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": self.vendor.id, "invoice_date": "2026-11-01",
            "invoice_line_ids": [Command.create({"name": "W", "quantity": 1, "price_unit": 77})],
        }).action_post()
        self.env.flush_all()
        self.assertEqual(self.env["construction.cashflow"].search_count([]), before)

    def test_views_compile(self):
        self.env["construction.cashflow"].get_views(
            [(False, "pivot"), (False, "graph"), (False, "list"), (False, "search")]
        )
