{
    "name": "Construction Site Daily Log",
    "summary": "Daily site diary: weather, workforce, work done, issues, incidents and photos",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_site", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/construction_site_log_views.xml",
        "views/construction_site_views.xml",
    ],
    "installable": True,
}
