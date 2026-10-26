{
    "name": "Construction Progress Billing",
    "summary": "Bill clients by percentage complete with retention, and release the retention at the end",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_progress", "account"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/progress_statement_views.xml",
        "views/construction_site_views.xml",
    ],
    "installable": True,
}
