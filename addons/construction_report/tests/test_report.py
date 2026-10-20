from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSiteCostReport(TransactionCase):
    def test_report_html_contains_site_data(self):
        site = self.env["construction.site"].create({"name": "Report Villa", "budget": 5000})
        self.env["construction.boq.line"].create({
            "site_id": site.id, "name": "Roofing works", "quantity": 2, "unit_cost": 750, "progress": 40,
        })
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "construction_report.report_site_cost", site.ids
        )
        text = html.decode()
        self.assertIn("Report Villa", text)
        self.assertIn("Roofing works", text)
        self.assertIn("<span>40</span> %", text)
        self.assertIn("<span>40.0</span> %", text)
        self.assertIn(site.code, text)

    def test_report_handles_empty_site(self):
        site = self.env["construction.site"].create({"name": "Empty"})
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "construction_report.report_site_cost", site.ids
        )
        self.assertIn("No bill of quantities lines", html.decode())

    def test_report_is_bound_to_site_print_menu(self):
        report = self.env.ref("construction_report.action_report_site_cost")
        self.assertEqual(report.model, "construction.site")
        self.assertTrue(report.binding_model_id)
