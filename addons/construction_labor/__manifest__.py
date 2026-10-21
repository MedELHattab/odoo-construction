{
    "name": "Construction Labor Cost",
    "summary": "Timesheet hours and labor cost per construction site, included in cost control and reports",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "author": "Intelligent B2B",
    "license": "LGPL-3",
    "depends": ["construction_progress", "construction_report", "hr_timesheet"],
    "data": [
        "views/construction_site_views.xml",
        "views/site_cost_report.xml",
    ],
    "installable": True,
}
