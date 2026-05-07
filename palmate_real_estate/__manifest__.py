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
    "depends": ["base", "mail", "web", "crm", "calendar", "account", "maintenance"],
    "data": [
        "security/palmate_security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "data/mail_template_data.xml",
        "data/cron_data.xml",
        "data/property_sync_data.xml",
        "views/property_views.xml",
        "views/property_visit_views.xml",
        "views/real_estate_workflow_views.xml",
        "views/dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "palmate_real_estate/static/src/dashboard/**/*",
        ],
    },
    "installable": True,
    "application": True,
}
