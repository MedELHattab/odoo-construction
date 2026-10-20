import base64

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionSign(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env["construction.site"].create({"name": "Harbour"})

    def _request(self, **vals):
        return self.env["sign.oca.request"].create({
            "name": "Contract",
            "data": base64.b64encode(b"%PDF-1.4 test"),
            **vals,
        })

    def test_request_linked_to_site_is_counted(self):
        self._request(site_id=self.site.id)
        self._request()
        self.assertEqual(self.site.sign_request_count, 1)

    def test_wizard_passes_site_to_request(self):
        wizard = self.env["sign.oca.template.generate"].new({"site_id": self.site.id})
        wizard.template_id = self.env["sign.oca.template"].create({
            "name": "NDA", "data": base64.b64encode(b"%PDF-1.4 test"),
        })
        self.assertEqual(wizard._generate_vals()["site_id"], self.site.id)

    def test_site_actions(self):
        send = self.site.action_send_for_signature()
        self.assertEqual(send["context"]["default_site_id"], self.site.id)
        listing = self.site.action_view_sign_requests()
        self.assertEqual(listing["domain"], [("site_id", "=", self.site.id)])
