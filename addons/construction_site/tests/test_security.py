from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionRoles(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.viewer = cls._user("viewer", "construction_site.group_construction_viewer")
        cls.manager = cls._user("manager", "construction_site.group_construction_manager")
        cls.admin = cls._user("admin", "construction_site.group_construction_admin")
        cls.site = cls.env["construction.site"].create({"name": "Secure Site", "budget": 100})

    @classmethod
    def _user(cls, login, group_xmlid):
        return cls.env["res.users"].create({
            "name": f"Construction {login}",
            "login": f"construction_{login}",
            "email": f"{login}@example.com",
            "group_ids": [Command.set([cls.env.ref(group_xmlid).id])],
        })

    def test_viewer_can_read_but_not_change(self):
        site = self.site.with_user(self.viewer)
        self.assertEqual(site.name, "Secure Site")
        with self.assertRaises(AccessError):
            site.write({"name": "Hacked"})
        with self.assertRaises(AccessError):
            self.env["construction.site"].with_user(self.viewer).create({"name": "New"})
        with self.assertRaises(AccessError):
            site.unlink()

    def test_viewer_does_not_need_project_access(self):
        # project_id is restricted to Project users; reading the rest still works
        site = self.site.with_user(self.viewer)
        self.assertEqual(site.code, self.site.code)
        self.assertEqual(site.state, "draft")
        with self.assertRaises(AccessError):
            site.project_id

    def test_manager_can_create_and_edit_but_not_delete(self):
        Site = self.env["construction.site"].with_user(self.manager)
        site = Site.create({"name": "Mgr Site"})
        site.write({"budget": 500})
        self.assertEqual(site.sudo().budget, 500)
        self.assertTrue(site.sudo().project_id, "linked project is created without Project rights")
        with self.assertRaises(AccessError):
            site.unlink()

    def test_admin_can_delete(self):
        site = self.env["construction.site"].with_user(self.admin).create({"name": "To delete"})
        site.unlink()
        self.assertFalse(site.exists())

    def test_roles_are_hierarchical(self):
        self.assertIn(
            self.env.ref("construction_site.group_construction_viewer"),
            self.admin.all_group_ids,
        )

    def test_existing_project_users_keep_access(self):
        project_mgr = self.env["res.users"].create({
            "name": "PM", "login": "construction_pm", "email": "pm@example.com",
            "group_ids": [Command.set([self.env.ref("project.group_project_manager").id])],
        })
        self.assertIn(
            self.env.ref("construction_site.group_construction_manager"), project_mgr.all_group_ids
        )
        project_mgr_site = self.site.with_user(project_mgr)
        project_mgr_site.write({"budget": 250})
        self.assertEqual(self.site.budget, 250)
