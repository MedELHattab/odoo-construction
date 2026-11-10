{
    "name": "Construction Material Tracking",
    "summary": "Materials ordered for each site: quantities received, still to deliver, late deliveries",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_purchase", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/material_views.xml",
    ],
    "installable": True,
}
