from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestConstructionSafety(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Safety Site"})

    def _inspection(self, results):
        return self.env["construction.inspection"].create({
            "name": "Weekly safety walk", "site_id": self.site.id,
            "line_ids": [
                Command.create({"name": f"Check {i}", "result": r, "note": f"note {i}"})
                for i, r in enumerate(results)
            ],
        })

    def test_result_follows_failed_lines(self):
        insp = self._inspection(["pass", "na"])
        self.assertEqual((insp.result, insp.fail_count), ("pass", 0))
        insp.line_ids[0].result = "fail"
        self.assertEqual((insp.result, insp.fail_count), ("fail", 1))

    def test_cannot_complete_empty_or_unanswered(self):
        with self.assertRaises(UserError):
            self._inspection([]).action_complete()
        with self.assertRaises(UserError):
            self._inspection(["pass", False]).action_complete()
        insp = self._inspection(["pass", "fail"])
        insp.action_complete()
        self.assertEqual(insp.state, "done")

    def test_failed_lines_become_punch_items_once(self):
        insp = self._inspection(["pass", "fail", "fail"])
        insp.action_create_punch_items()
        self.assertEqual(len(insp.punch_ids), 2)
        self.assertEqual(insp.punch_ids.site_id, self.site)
        insp.action_create_punch_items()
        self.assertEqual(len(insp.punch_ids), 2, "running it twice must not duplicate")

    def test_punch_workflow_requires_fix_before_verify(self):
        item = self.env["construction.punch.item"].create({"name": "Crack", "site_id": self.site.id})
        with self.assertRaises(UserError):
            item.action_verify()
        item.action_done()
        item.action_verify()
        self.assertEqual(item.state, "verified")
        item.action_reopen()
        self.assertEqual(item.state, "open")

    def test_late_flag_and_site_counters(self):
        Punch = self.env["construction.punch.item"]
        late = Punch.create({"name": "Late", "site_id": self.site.id, "deadline": "2020-01-01"})
        ok = Punch.create({"name": "Future", "site_id": self.site.id, "deadline": "2999-01-01"})
        self.assertTrue(late.is_late)
        self.assertFalse(ok.is_late)
        self.assertEqual(self.site.punch_open_count, 2)
        late.action_done()
        self.assertFalse(late.is_late)
        late.action_verify()
        self.assertEqual(self.site.punch_open_count, 1)
        self._inspection(["fail"]).action_complete()
        self.assertEqual(self.site.inspection_count, 1)
        self.assertEqual(self.site.failed_inspection_count, 1)

    def test_viewer_is_read_only(self):
        viewer = new_test_user(
            self.env, "safety_viewer", groups="construction_site.group_construction_viewer"
        )
        with self.assertRaises(AccessError):
            self.env["construction.punch.item"].with_user(viewer).create(
                {"name": "x", "site_id": self.site.id}
            )

    def test_views_compile(self):
        for model in ("construction.punch.item", "construction.inspection"):
            self.env[model].get_views([(False, "list"), (False, "form"), (False, "search")])
        self.site.action_view_punch_items()
        self.site.action_view_inspections()
