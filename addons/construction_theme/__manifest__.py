{
    "name": "Construction Theme",
    "summary": "Construction branding for the Odoo backend: brand colour and app icon",
    "version": "19.0.1.0.0",
    "category": "Themes/Backend",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["web", "construction_site"],
    "data": [
        "views/menu.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            ("before", "web/static/src/scss/primary_variables.scss",
             "construction_theme/static/src/scss/primary_variables.scss"),
        ],
    },
    "installable": True,
}
