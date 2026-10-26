from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, tagged

MONDAY = date(2026, 11, 2)  # previous working day is Friday 2026-10-30


@tagged("post_install", "-at_install")
class TestConstructionAlerts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env["res.users"].create({
            "name": "Alert manager", "login": "alert_mgr", "email": "am@example.com",
            "group_ids": [Command.set([cls.env.ref("construction_site.group_construction_manager").id])],
        })
        # other in-progress sites would add noise to the counts
        cls.env["construction.site"].search([("state", "=", "in_progress")]).write({"state": "on_hold"})
        cls.site = cls.env["construction.site"].create({
            "name": "Alert Site", "budget": 1000, "manager_id": cls.manager.id,
            "date_start": "2026-01-01",
        })
        cls.site.action_start()
        cls.vendor = cls.env["res.partner"].create({"name": "Alert vendor"})

    def _spend(self, amount):
        bill = self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": self.vendor.id, "site_id": self.site.id,
            "invoice_date": "2026-10-01",
            "invoice_line_ids": [Command.create({"name": "Work", "quantity": 1, "price_unit": amount})],
        })
        bill.action_post()
        return bill

    def _activities(self, fragment=None):
        activities = self.env["mail.activity"].search([
            ("res_model", "=", "construction.site"), ("res_id", "=", self.site.id),
        ])
        return activities.filtered(lambda a: not fragment or fragment in a.summary)

    def _log(self, day):
        self.env["construction.site.log"].create({"site_id": self.site.id, "date": day, "work_done": "x"})

    def test_no_alert_when_everything_is_fine(self):
        self._log("2026-10-30")
        self.assertEqual(self.site._run_alerts(today=MONDAY), 0)
        self.assertFalse(self._activities())

    def test_warning_then_over_budget_each_alerted_once(self):
        self._log("2026-10-30")
        self._spend(950)
        self.assertEqual(self.site._run_alerts(today=MONDAY), 1)
        self.assertEqual(self.site.budget_alert_level, "warning")
        self.assertEqual(self.site._run_alerts(today=MONDAY), 0, "same level is not repeated")
        self._spend(100)
        self.assertEqual(self.site._run_alerts(today=MONDAY), 1)
        self.assertEqual(self.site.budget_alert_level, "over")
        self.assertTrue(self._activities("Over budget"))
        self.assertEqual(self._activities("Over budget").user_id, self.manager)

    def test_alert_level_resets_when_back_under_budget(self):
        self._log("2026-10-30")
        bill = self._spend(1200)
        self.site._run_alerts(today=MONDAY)
        self.assertEqual(self.site.budget_alert_level, "over")
        bill.button_draft()
        self.site._run_alerts(today=MONDAY)
        self.assertEqual(self.site.budget_alert_level, "none")

    def test_warning_threshold_is_configurable(self):
        self._log("2026-10-30")
        self.env["ir.config_parameter"].sudo().set_param("construction_alert.budget_warning_percent", "50")
        self._spend(600)
        self.assertEqual(self.site._run_alerts(today=MONDAY), 1)
        self.assertEqual(self.site.budget_alert_level, "warning")

    def test_missing_log_alert_skips_weekends(self):
        self.assertEqual(self.site._run_alerts(today=MONDAY), 1)
        self.assertTrue(self._activities("2026-10-30"), "Monday checks Friday, not the weekend")
        self.assertEqual(self.site._run_alerts(today=MONDAY), 0, "still open: not duplicated")

    def test_missing_log_alert_ignores_sites_not_yet_started(self):
        self.site.date_start = "2026-12-01"
        self.assertEqual(self.site._run_alerts(today=MONDAY), 0)

    def test_overdue_site_alerted_once_until_date_changes(self):
        self._log("2026-10-30")
        self.site.date_end = "2026-10-15"
        self.assertEqual(self.site._run_alerts(today=MONDAY), 1)
        self.assertTrue(self._activities("Past planned end date"))
        self.assertEqual(self.site._run_alerts(today=MONDAY), 0)
        self._activities().unlink()
        self.assertEqual(self.site._run_alerts(today=MONDAY), 0, "completed alert is not recreated")
        self.site.date_end = "2026-10-20"  # extended but still late
        self.assertEqual(self.site._run_alerts(today=MONDAY), 1)

    def test_only_sites_in_progress_are_checked(self):
        self.site.action_hold()
        self.assertEqual(self.site._run_alerts(today=MONDAY), 0)

    def test_site_without_manager_does_not_crash(self):
        self.site.manager_id = False
        self._spend(2000)
        self.assertEqual(self.site._run_alerts(today=MONDAY), 0)

    def test_cron_and_button_exist(self):
        cron = self.env.ref("construction_alert.ir_cron_construction_alerts")
        self.assertTrue(cron.active)
        result = self.site.action_run_alerts()
        self.assertEqual(result["tag"], "display_notification")
        self.env["construction.site"].get_views([(False, "form")])
