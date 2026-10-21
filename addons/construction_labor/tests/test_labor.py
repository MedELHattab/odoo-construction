from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionLabor(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Labor Site", "budget": 5000})
        cls.employee = cls.env["hr.employee"].create({"name": "Worker", "hourly_cost": 50.0})
        cls.task = cls.env["project.task"].create({
            "name": "Pour concrete", "project_id": cls.site.project_id.id,
        })

    def _log(self, hours, task=None, employee=None):
        task = task or self.task
        return self.env["account.analytic.line"].create({
            "name": "Work", "project_id": task.project_id.id, "task_id": task.id,
            "employee_id": (employee or self.employee).id, "unit_amount": hours,
        })

    def test_hours_and_cost_come_from_timesheets(self):
        self._log(4)
        self._log(2)
        self.assertEqual(self.site.labor_hours, 6.0)
        self.assertEqual(self.site.labor_cost, 300.0)

    def test_other_projects_do_not_count(self):
        other = self.env["construction.site"].create({"name": "Other"})
        task = self.env["project.task"].create({"name": "T", "project_id": other.project_id.id})
        self._log(10, task=task)
        self.assertEqual(self.site.labor_hours, 0.0)
        self.assertEqual(other.labor_hours, 10.0)

    def test_total_cost_adds_bills_and_labor(self):
        self._log(4)  # 200
        vendor = self.env["res.partner"].create({"name": "Sub"})
        bill = self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": vendor.id, "site_id": self.site.id,
            "invoice_date": "2026-10-01",
            "invoice_line_ids": [Command.create({"name": "W", "quantity": 1, "price_unit": 1000})],
        })
        bill.action_post()
        self.assertEqual(self.site.actual_cost, 1000.0)
        self.assertEqual(self.site.total_cost, 1200.0)
        self.assertEqual(self.site.budget_after_total, 3800.0)

    def test_deleting_timesheet_updates_site(self):
        line = self._log(4)
        line.unlink()
        self.assertEqual(self.site.labor_cost, 0.0)

    def test_screens_and_report(self):
        self._log(3)
        self.env["construction.site"].get_views([(False, "form"), (False, "graph"), (False, "pivot")])
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "construction_report.report_site_cost", self.site.ids
        )
        text = html.decode()
        self.assertIn("Hours worked", text)
        self.assertIn("<span>3.0</span> h", text)
        self.assertEqual(self.site.action_view_timesheets()["domain"], [("site_id", "=", self.site.id)])
