{
    "name": "Construction Sites",
    "summary": "Manage construction sites, linked to projects, clients and budgets",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["base", "mail", "project"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/construction_site_views.xml",
    ],
    "application": True,
    "installable": True,
}
