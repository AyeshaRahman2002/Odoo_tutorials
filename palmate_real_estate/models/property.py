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
            ("draft", "Draft"),
            ("available", "Available"),
            ("reserved", "Reserved"),
            ("sold", "Sold"),
            ("rented", "Rented"),
            ("archived", "Archived"),
        ],
        string = "Status",
        default = "draft",
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

    ai_description = fields.Text(
        string = "Description",
        tracking = True,
        help = "Auto-generated description draft based on the property details.",
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

    inquiry_ids = fields.One2many(
        "palmate.property.inquiry",
        "property_id",
        string = "Inquiries",
    )

    reservation_ids = fields.One2many(
        "palmate.property.reservation",
        "property_id",
        string = "Reservations",
    )

    contract_ids = fields.One2many(
        "palmate.property.contract",
        "property_id",
        string = "Contracts",
    )

    maintenance_request_ids = fields.One2many(
        "palmate.maintenance.request",
        "property_id",
        string = "Maintenance Requests",
    )

    visit_count = fields.Integer(
        string = "Visit Count",
        compute = "_compute_visit_count",
    )

    inquiry_count = fields.Integer(
        string = "Inquiry Count",
        compute = "_compute_related_counts",
    )

    reservation_count = fields.Integer(
        string = "Reservation Count",
        compute = "_compute_related_counts",
    )

    contract_count = fields.Integer(
        string = "Contract Count",
        compute = "_compute_related_counts",
    )

    maintenance_count = fields.Integer(
        string = "Maintenance Count",
        compute = "_compute_related_counts",
    )

    def _compute_visit_count(self):
        for record in self:
            record.visit_count = len(record.visit_ids)

    def _compute_related_counts(self):
        for record in self:
            record.inquiry_count = len(record.inquiry_ids)
            record.reservation_count = len(record.reservation_ids)
            record.contract_count = len(record.contract_ids)
            record.maintenance_count = len(record.maintenance_request_ids)

    def action_publish_property(self):
        for record in self:
            record.status = "available"

    def action_reserve_property(self):
        for record in self:
            record.status = "reserved"

    def action_mark_sold(self):
        for record in self:
            record.status = "sold"

    def action_mark_rented(self):
        for record in self:
            record.status = "rented"

    def action_archive_property(self):
        for record in self:
            record.status = "archived"

    def action_generate_ai_description(self):
        type_labels = dict(self._fields["property_type"].selection)
        status_labels = dict(self._fields["status"].selection)

        tone_by_price = {
            "premium": _("premium listing"),
            "mid": _("well-positioned listing"),
            "affordable": _("value-focused listing"),
        }

        for record in self:
            property_type = type_labels.get(record.property_type, _("property")).lower()
            status = status_labels.get(record.status, _("available")).lower()
            location = record.location or _("a desirable location")
            currency = record.currency_id.symbol or record.currency_id.name or ""
            price_text = f"{currency}{record.price:,.0f}" if record.price else _("price available on request")

            if record.price >= 500000:
                tone = tone_by_price["premium"]
            elif record.price >= 150000:
                tone = tone_by_price["mid"]
            else:
                tone = tone_by_price["affordable"]

            if record.property_type == "villa":
                audience = _("families looking for privacy, comfort, and spacious living")
                highlights = _("space, privacy, and long-term residential value")
            elif record.property_type == "apartment":
                audience = _("professionals, couples, or small families")
                highlights = _("convenience, accessibility, and practical living")
            elif record.property_type == "office":
                audience = _("businesses looking for a functional workspace")
                highlights = _("accessibility, professional use, and operational convenience")
            elif record.property_type == "land":
                audience = _("investors or developers planning a future project")
                highlights = _("development potential and long-term investment value")
            else:
                audience = _("buyers with flexible real estate requirements")
                highlights = _("flexibility and market potential")

            record.ai_description = _(
                "%(name)s is a %(tone)s featuring a %(property_type)s in %(location)s. "
                "The property is currently %(status)s and listed at %(price)s. "
                "Based on its category and location, it is suitable for %(audience)s. "
                "Key strengths include %(highlights)s. "
                "Interested customers can schedule a viewing to better evaluate the property."
            ) % {
                "name": record.name,
                "tone": tone,
                "property_type": property_type,
                "location": location,
                "status": status,
                "price": price_text,
                "audience": audience,
                "highlights": highlights,
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

    def action_view_inquiries(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Property Inquiries"),
            "res_model": "palmate.property.inquiry",
            "view_mode": "list,form",
            "domain": [("property_id", "=", self.id)],
            "context": {"default_property_id": self.id},
        }

    def action_view_reservations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Property Reservations"),
            "res_model": "palmate.property.reservation",
            "view_mode": "list,form",
            "domain": [("property_id", "=", self.id)],
            "context": {"default_property_id": self.id},
        }

    def action_view_contracts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Property Contracts"),
            "res_model": "palmate.property.contract",
            "view_mode": "list,form",
            "domain": [("property_id", "=", self.id)],
            "context": {"default_property_id": self.id},
        }

    def action_view_maintenance_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Maintenance Requests"),
            "res_model": "palmate.maintenance.request",
            "view_mode": "list,form",
            "domain": [("property_id", "=", self.id)],
            "context": {"default_property_id": self.id},
        }
