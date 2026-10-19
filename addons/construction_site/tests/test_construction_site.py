from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionSite(TransactionCase):
    def test_create_generates_code_and_project(self):
        site = self.env["construction.site"].create({"name": "Villa Atlas"})
        self.assertTrue(site.code.startswith("SITE/"))
        self.assertTrue(site.project_id)
        self.assertIn("Villa Atlas", site.project_id.name)

    def test_codes_are_unique_and_sequential(self):
        sites = self.env["construction.site"].create(
            [{"name": "A"}, {"name": "B"}]
        )
        self.assertNotEqual(sites[0].code, sites[1].code)

    def test_end_date_before_start_date_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["construction.site"].create(
                {"name": "Bad", "date_start": "2026-05-01", "date_end": "2026-04-01"}
            )

    def test_negative_budget_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["construction.site"].create({"name": "Bad", "budget": -1})

    def test_state_workflow(self):
        site = self.env["construction.site"].create({"name": "Flow"})
        site.action_start()
        self.assertEqual(site.state, "in_progress")
        site.action_done()
        self.assertEqual(site.state, "done")
