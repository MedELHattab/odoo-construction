{
    "name": "Construction Subcontracts",
    "summary": "Subcontractor contracts with payment certificates, retention and vendor bills linked to the site",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_cost", "construction_purchase"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/subcontract_views.xml",
        "views/construction_site_views.xml",
    ],
    "installable": True,
}
