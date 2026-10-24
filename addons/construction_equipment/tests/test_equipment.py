from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionEquipment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Equip Site", "budget": 10000})
        cls.other_site = cls.env["construction.site"].create({"name": "Other Site"})
        cls.crane = cls.env["construction.equipment"].create(
            {"name": "Tower crane", "code": "CR-01", "category": "crane", "daily_rate": 400}
        )
        cls.Usage = cls.env["construction.equipment.usage"]

    def _assign(self, start, end, site=None, equipment=None, **vals):
        return self.Usage.create({
            "site_id": (site or self.site).id,
            "equipment_id": (equipment or self.crane).id,
            "date_from": start, "date_to": end, **vals,
        })

    def test_cost_is_days_times_rate_inclusive(self):
        usage = self._assign("2026-11-01", "2026-11-05")
        self.assertEqual(usage.days, 5)
        self.assertEqual(usage.daily_rate, 400)  # defaulted from the equipment
        self.assertEqual(usage.cost, 2000)
        self.assertEqual(self.site.equipment_cost, 2000)

    def test_rate_can_be_overridden_per_assignment(self):
        usage = self._assign("2026-11-01", "2026-11-02", daily_rate=300)
        self.assertEqual(usage.cost, 600)

    def test_equipment_cost_flows_into_total_cost(self):
        self._assign("2026-11-01", "2026-11-02")  # 800
        self.assertEqual(self.site.total_cost, 800)
        self.assertEqual(self.site.budget_after_total, 9200)
        vendor = self.env["res.partner"].create({"name": "Sub"})
        bill = self.env["account.move"].create({
            "move_type": "in_invoice", "partner_id": vendor.id, "site_id": self.site.id,
            "invoice_date": "2026-10-01",
            "invoice_line_ids": [Command.create({"name": "W", "quantity": 1, "price_unit": 1000})],
        })
        bill.action_post()
        # bills + equipment still add up after a different component changes
        self.assertEqual(self.site.total_cost, 1800)

    def test_removing_assignment_updates_site(self):
        usage = self._assign("2026-11-01", "2026-11-02")
        usage.unlink()
        self.assertEqual(self.site.equipment_cost, 0)
        self.assertEqual(self.site.total_cost, 0)

    def test_same_equipment_cannot_be_on_two_sites_at_once(self):
        self._assign("2026-11-01", "2026-11-10")
        with self.assertRaises(ValidationError):
            self._assign("2026-11-10", "2026-11-12", site=self.other_site)
        # back-to-back is fine
        self._assign("2026-11-11", "2026-11-12", site=self.other_site)

    def test_invalid_dates_and_rates_rejected(self):
        with self.assertRaises(ValidationError):
            self._assign("2026-11-05", "2026-11-01")
        with self.assertRaises(ValidationError):
            self._assign("2026-12-01", "2026-12-02", daily_rate=-1)
        with self.assertRaises(ValidationError):
            self.env["construction.equipment"].create({"name": "Bad", "daily_rate": -5})

    def test_roles(self):
        def user(login, group):
            return self.env["res.users"].create({
                "name": login, "login": login, "email": f"{login}@example.com",
                "group_ids": [Command.set([self.env.ref(group).id])],
            })
        viewer = user("eq_viewer", "construction_site.group_construction_viewer")
        manager = user("eq_manager", "construction_site.group_construction_manager")
        self.assertEqual(self.crane.with_user(viewer).name, "Tower crane")
        with self.assertRaises(AccessError):
            self.crane.with_user(viewer).write({"daily_rate": 1})
        self.crane.with_user(manager).write({"daily_rate": 450})
        with self.assertRaises(AccessError):
            self.crane.with_user(manager).unlink()

    def test_screens_and_report(self):
        self._assign("2026-11-01", "2026-11-03")
        self.env["construction.equipment"].get_views([(False, "list"), (False, "form"), (False, "search")])
        self.env["construction.site"].get_views([(False, "form"), (False, "graph"), (False, "pivot")])
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "construction_report.report_site_cost", self.site.ids
        )
        text = html.decode()
        self.assertIn("Tower crane", text)
        self.assertIn("Equipment total", text)
