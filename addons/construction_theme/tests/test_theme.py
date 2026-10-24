from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConstructionTheme(TransactionCase):
    def test_construction_app_has_icon(self):
        menu = self.env.ref("construction_site.menu_construction_root")
        self.assertEqual(menu.web_icon, "construction_theme,static/description/icon.png")
        self.assertTrue(menu.web_icon_data, "the icon file is found and loaded")

    def test_brand_colour_reaches_the_backend_stylesheet(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("web.assets_web", assets_params={})
        css = bundle.css().raw.decode().lower()
        self.assertGreater(css.count("#c2410c"), 50, "brand colour drives navbar, buttons, links")
        # one hardcoded purple remains in the rich-text table picker (html_editor), outside theme control
        self.assertLessEqual(css.count("#71639e"), 1)
