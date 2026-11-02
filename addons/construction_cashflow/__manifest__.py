{
    "name": "Construction Cash Flow Forecast",
    "summary": "Expected money in and out per site and month, from open invoices, vendor bills and held retention",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_billing", "construction_cost"],
    "data": [
        "security/ir.model.access.csv",
        "views/cashflow_views.xml",
    ],
    "installable": True,
}
