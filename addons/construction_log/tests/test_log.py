import base64

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from psycopg2 import IntegrityError
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestConstructionSiteLog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Log Site"})
        cls.Log = cls.env["construction.site.log"]

    def _log(self, date="2026-10-01", **vals):
        return self.Log.create({
            "site_id": self.site.id, "date": date, "work_done": "Foundations poured",
            **vals,
        })

    def test_counts_and_last_date(self):
        self._log("2026-10-01")
        self._log("2026-10-03", safety_incident=True, incident_details="Worker slipped")
        self.assertEqual(self.site.log_count, 2)
        self.assertEqual(self.site.incident_count, 1)
        self.assertEqual(str(self.site.last_log_date), "2026-10-03")

    def test_one_log_per_site_per_day(self):
        self._log("2026-10-01")
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self._log("2026-10-01")

    def test_incident_requires_details(self):
        with self.assertRaises(ValidationError):
            self._log(safety_incident=True)

    def test_negative_workers_rejected(self):
        with self.assertRaises(ValidationError):
            self._log(workers_count=-3)

    def test_photos_can_be_attached(self):
        photo = self.env["ir.attachment"].create({
            "name": "wall.jpg", "datas": base64.b64encode(b"fake-image"),
        })
        log = self._log(attachment_ids=[Command.set([photo.id])])
        self.assertEqual(log.attachment_ids.name, "wall.jpg")

    def test_roles(self):
        def user(login, group):
            return self.env["res.users"].create({
                "name": login, "login": login, "email": f"{login}@example.com",
                "group_ids": [Command.set([self.env.ref(group).id])],
            })
        viewer = user("log_viewer", "construction_site.group_construction_viewer")
        manager = user("log_manager", "construction_site.group_construction_manager")
        log = self._log()
        self.assertEqual(log.with_user(viewer).work_done, "Foundations poured")
        with self.assertRaises(AccessError):
            self.Log.with_user(viewer).create({"site_id": self.site.id, "work_done": "x"})
        new = self.Log.with_user(manager).create(
            {"site_id": self.site.id, "date": "2026-10-09", "work_done": "Walls"}
        )
        self.assertEqual(new.author_id, manager)
        with self.assertRaises(AccessError):
            new.unlink()

    def test_screens_compile(self):
        self.Log.get_views([(False, "list"), (False, "form"), (False, "search")])
        self.env["construction.site"].get_views([(False, "form")])
        self.assertEqual(self.site.action_view_logs()["domain"], [("site_id", "=", self.site.id)])
