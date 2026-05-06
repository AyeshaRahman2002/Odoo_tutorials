from odoo import fields, models


class PalmateProperty(models.Model):
    _name = "palmate.property"
    _description = "Real Estate Property"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string = "Property Name",
        required = True,
        tracking = True,
    )

    property_type = fields.Selection(
        [
            ("apartment", "Apartment"),
            ("villa", "Villa"),
            ("office", "Office"),
            ("land", "Land"),
            ("other", "Other"),
        ],
        string = "Property Type",
        required = True,
        default = "apartment",
        tracking = True,
    )

    location = fields.Char(
        string = "Location",
        tracking = True,
    )

    owner_id = fields.Many2one(
        "res.partner",
        string = "Owner",
        tracking = True,
    )

    agent_id = fields.Many2one(
        "res.users",
        string = "Assigned Agent",
        default = lambda self: self.env.user,
        tracking = True,
    )

    status = fields.Selection(
        [
            ("available", "Available"),
            ("reserved", "Reserved"),
            ("sold", "Sold"),
            ("rented", "Rented"),
        ],
        string = "Status",
        default = "available",
        required = True,
        tracking = True,
    )

    price = fields.Monetary(
        string = "Price / Rent",
        currency_field = "currency_id",
        tracking = True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string = "Currency",
        default = lambda self: self.env.company.currency_id,
        required = True,
    )

    company_id = fields.Many2one(
        "res.company",
        string = "Company",
        default = lambda self: self.env.company,
        required = True,
    )

    notes = fields.Html(
        string = "Notes",
    )

    visit_ids = fields.One2many(
        "palmate.property.visit",
        "property_id",
        string = "Visits",
    )

    visit_count = fields.Integer(
        string = "Visit Count",
        compute = "_compute_visit_count",
    )

    def _compute_visit_count(self):
        for record in self:
            record.visit_count = len(record.visit_ids)

    def action_mark_reserved(self):
        for record in self:
            record.status = "reserved"

    def action_mark_available(self):
        for record in self:
            record.status = "available"