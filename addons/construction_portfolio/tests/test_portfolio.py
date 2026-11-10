from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionPortfolio(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "Portfolio vendor"})
        cls.site = cls.env["construction.site"].create({
            "name": "Portfolio Site", "budget": 1000, "date_start": "2026-01-01", "date_end": "2026-06-30",
        })
        cls.site.action_start()

    def _row(self):
        self.env.flush_all()
        return self.env["construction.portfolio"].search([("site_id", "=", self.site.id)])

    def _bill(self, amount):
        self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": self.vendor.id, "site_id": self.site.id,
            "invoice_date": "2026-10-01",
            "invoice_line_ids": [Command.create({"name": "W", "quantity": 1, "price_unit": amount})],
        }).action_post()

    def test_row_mirrors_the_site(self):
        self._bill(400)
        row = self._row()
        self.assertEqual((row.budget, row.total_cost, row.site_count), (1000.0, 400.0, 1))
        self.assertEqual(row.over_budget, 0)
        self.assertEqual(row.late_sites, 1, "in progress and past its planned end date")

    def test_over_budget_flag(self):
        self._bill(1200)
        self.assertEqual(self._row().over_budget, 1)

    def test_punch_and_inspection_risks_are_counted(self):
        Punch = self.env["construction.punch.item"]
        Punch.create({"name": "Late", "site_id": self.site.id, "deadline": "2020-01-01"})
        Punch.create({"name": "Fine", "site_id": self.site.id, "deadline": "2999-01-01"})
        done = Punch.create({"name": "Done", "site_id": self.site.id})
        done.action_done()
        done.action_verify()
        insp = self.env["construction.inspection"].create({
            "name": "Walk", "site_id": self.site.id,
            "line_ids": [Command.create({"name": "Rails", "result": "fail"})],
        })
        insp.action_complete()
        row = self._row()
        self.assertEqual((row.open_punch, row.overdue_punch, row.failed_inspections), (2, 1, 1))

    def test_archived_sites_are_excluded(self):
        self.site.active = False
        self.assertFalse(self._row())

    def test_views_compile(self):
        self.env["construction.portfolio"].get_views(
            [(False, "list"), (False, "pivot"), (False, "graph"), (False, "search")]
        )
