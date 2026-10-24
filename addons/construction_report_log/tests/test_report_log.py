from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReportLogs(TransactionCase):
    def _html(self, site):
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "construction_report.report_site_cost", site.ids
        )
        return html.decode()

    def test_site_without_logs(self):
        site = self.env["construction.site"].create({"name": "No logs"})
        text = self._html(site)
        self.assertIn("Daily logs", text)
        self.assertIn("No daily logs recorded", text)

    def test_logs_and_incidents_are_listed(self):
        site = self.env["construction.site"].create({"name": "Logged"})
        Log = self.env["construction.site.log"]
        Log.create({"site_id": site.id, "date": "2026-10-01", "work_done": "Excavation done"})
        Log.create({
            "site_id": site.id, "date": "2026-10-02", "work_done": "Rebar fixing",
            "issues": "Delivery late", "safety_incident": True,
            "incident_details": "Minor cut on hand",
        })
        text = self._html(site)
        self.assertIn("Excavation done", text)
        self.assertIn("Rebar fixing", text)
        self.assertIn("Delivery late", text)
        self.assertIn("Minor cut on hand", text)
        self.assertIn("safety incident(s) recorded", text)

    def test_only_the_latest_ten_logs_are_printed(self):
        site = self.env["construction.site"].create({"name": "Busy"})
        Log = self.env["construction.site.log"]
        for day in range(1, 13):
            Log.create({"site_id": site.id, "date": f"2026-10-{day:02d}", "work_done": f"Task number {day:02d}"})
        text = self._html(site)
        self.assertIn("Task number 12", text)
        self.assertIn("Task number 03", text)
        self.assertNotIn("Task number 02", text)
        self.assertNotIn("Task number 01", text)
