{
    "name": "Construction Expenses",
    "summary": "Link employee expenses to construction sites and include them in site cost",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_equipment", "hr_expense"],
    "data": [
        "views/hr_expense_views.xml",
        "views/construction_site_views.xml",
        "views/site_cost_report.xml",
    ],
    "installable": True,
}
