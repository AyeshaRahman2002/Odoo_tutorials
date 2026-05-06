{
    "name": "Palmate Real Estate",
    "version": "19.0.1.0.0",
    "category": "Real Estate",
    "summary": "Basic property and property visit management",
    "description": """
Palmate Real Estate practice module.

This module manages:
- Properties
- Property visits
- Customers
- Agents
- Property status
- Visit workflow
    """,
    "author": "Palmate Technologies",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "data/mail_template_data.xml",
        "data/cron_data.xml",
        "views/property_views.xml",
        "views/property_visit_views.xml",
        "views/real_estate_workflow_views.xml",
    ],
    "installable": True,
    "application": True,
}
