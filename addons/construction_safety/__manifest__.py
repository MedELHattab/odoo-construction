{
    "name": "Construction Safety Inspections and Punch List",
    "summary": "Site inspection checklists and a punch list of defects to fix before handover",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_site", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/construction_punch_item_views.xml",
        "views/construction_inspection_views.xml",
        "views/construction_site_views.xml",
    ],
    "installable": True,
}
