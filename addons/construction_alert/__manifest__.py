{
    "name": "Construction Alerts",
    "summary": "Daily alerts to site managers: budget warning and overrun, late sites, missing daily logs",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_expense", "construction_log"],
    "data": [
        "data/cron.xml",
        "views/construction_site_views.xml",
    ],
    "installable": True,
}
