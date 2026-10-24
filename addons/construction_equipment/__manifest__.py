{
    "name": "Construction Equipment",
    "summary": "Equipment and machinery register with daily rates charged to construction sites",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_labor"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/construction_equipment_views.xml",
        "views/construction_site_views.xml",
        "views/site_cost_report.xml",
    ],
    "installable": True,
}
