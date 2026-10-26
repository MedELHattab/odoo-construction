{
    "name": "Construction Change Orders",
    "summary": "Client-approved extra work that is added to the site's bill of quantities and budget",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_boq"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/change_order_views.xml",
        "views/construction_site_views.xml",
    ],
    "installable": True,
}
