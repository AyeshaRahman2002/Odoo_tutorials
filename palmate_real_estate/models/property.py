from odoo import _, fields, models


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

    property_count = fields.Integer(
        string = "Property Count",
        default = 1,
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

    ai_description = fields.Text(
        string = "AI Description",
        tracking = True,
        help = "Rule-based placeholder description. Replace the generator later with a real AI service.",
    )

    title_deed_file = fields.Binary(
        string = "Title Deed / Contract",
        attachment = True,
    )

    title_deed_filename = fields.Char(
        string = "Title Deed Filename",
    )

    brochure_file = fields.Binary(
        string = "Brochure PDF",
        attachment = True,
    )

    brochure_filename = fields.Char(
        string = "Brochure Filename",
    )

    property_image = fields.Image(
        string = "Main Property Image",
        max_width = 1920,
        max_height = 1920,
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

    def action_generate_ai_description(self):
        type_labels = dict(self._fields["property_type"].selection)
        status_labels = dict(self._fields["status"].selection)
        audience_by_type = {
            "apartment": _("professionals or small families"),
            "villa": _("families looking for spacious living"),
            "office": _("businesses seeking a practical workspace"),
            "land": _("investors or developers planning a new project"),
            "other": _("buyers with flexible real estate needs"),
        }

        for record in self:
            property_type = type_labels.get(record.property_type, _("property")).lower()
            status = status_labels.get(record.status, _("available")).lower()
            location = record.location or _("a well-connected area")
            currency = record.currency_id.symbol or record.currency_id.name or ""
            price_text = (
                _("%(currency)s%(amount)s")
                % {
                    "currency": currency,
                    "amount": f"{record.price:,.0f}" if record.price else _("upon request"),
                }
                if record.price
                else _("upon request")
            )
            audience = audience_by_type.get(record.property_type, _("buyers seeking value"))

            record.ai_description = _(
                "This %(property_type)s in %(location)s is currently %(status)s and listed at %(price)s. "
                "It may be suitable for %(audience)s in a strong local market."
            ) % {
                "property_type": property_type,
                "location": location,
                "status": status,
                "price": price_text,
                "audience": audience,
            }

    def action_view_visits(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Property Visits"),
            "res_model": "palmate.property.visit",
            "view_mode": "list,form",
            "domain": [("property_id", "=", self.id)],
            "context": {
                "default_property_id": self.id,
                "search_default_group_by_status": 1,
            },
        }
