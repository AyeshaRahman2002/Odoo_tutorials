from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PalmatePropertyVisit(models.Model):
    _name = "palmate.property.visit"
    _description = "Property Visit"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "visit_date desc"

    name = fields.Char(
        string = "Visit Reference",
        required = True,
        default = "New Property Visit",
        tracking = True,
    )

    property_id = fields.Many2one(
        "palmate.property",
        string = "Selected Property",
        required = False,
        tracking = True,
    )

    customer_id = fields.Many2one(
        "res.partner",
        string = "Customer",
        required = True,
        tracking = True,
    )

    inquiry_id = fields.Many2one(
        "palmate.property.inquiry",
        string = "Inquiry",
        tracking = True,
    )

    reservation_ids = fields.One2many(
        "palmate.property.reservation",
        "visit_id",
        string = "Reservations",
    )

    agent_id = fields.Many2one(
        "res.users",
        string = "Agent",
        default = lambda self: self.env.user,
        tracking = True,
    )

    visit_date = fields.Datetime(
        string = "Visit Date",
        required = True,
        tracking = True,
    )

    status = fields.Selection(
        [
            ("scheduled", "Scheduled"),
            ("completed", "Completed"),
            ("interested", "Interested"),
            ("offer_sent", "Offer Sent"),
            ("closed", "Closed"),
            ("lost", "Lost"),
            ("cancelled", "Cancelled"),
        ],
        string = "Status",
        default = "scheduled",
        required = True,
        tracking = True,
    )

    company_id = fields.Many2one(
        "res.company",
        string = "Company",
        default = lambda self: self.env.company,
        required = True,
    )

    feedback = fields.Text(
        string = "Customer Feedback",
    )

    preferred_location = fields.Char(
        string = "Preferred Location",
        tracking = True,
    )

    preferred_budget = fields.Monetary(
        string = "Budget",
        currency_field = "currency_id",
        tracking = True,
    )

    preferred_property_type = fields.Selection(
        selection = lambda self: self.env["palmate.property"]._fields["property_type"].selection,
        string = "Preferred Property Type",
        tracking = True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string = "Currency",
        default = lambda self: self.env.company.currency_id,
        required = True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            inquiry_id = vals.get("inquiry_id")
            if inquiry_id:
                inquiry = self.env["palmate.property.inquiry"].browse(inquiry_id)
                vals.setdefault("property_id", inquiry.property_id.id)
                vals.setdefault("customer_id", inquiry.customer_id.id)
                vals.setdefault("agent_id", inquiry.agent_id.id)
                vals.setdefault("preferred_location", inquiry.preferred_location)
                vals.setdefault("preferred_budget", inquiry.budget)
                vals.setdefault("preferred_property_type", inquiry.property_type)
        return super().create(vals_list)

    @api.onchange("inquiry_id")
    def _onchange_inquiry_id(self):
        for record in self:
            if record.inquiry_id:
                record.property_id = record.inquiry_id.property_id
                record.customer_id = record.inquiry_id.customer_id
                record.agent_id = record.inquiry_id.agent_id
                record.preferred_location = record.inquiry_id.preferred_location
                record.preferred_budget = record.inquiry_id.budget
                record.preferred_property_type = record.inquiry_id.property_type

    @api.constrains("inquiry_id", "property_id", "customer_id")
    def _check_inquiry_consistency(self):
        for record in self:
            inquiry = record.inquiry_id
            if not inquiry:
                continue
            if inquiry.property_id and record.property_id and inquiry.property_id != record.property_id:
                raise ValidationError(_("The selected property must match the inquiry property."))
            if record.customer_id and inquiry.customer_id != record.customer_id:
                raise ValidationError(_("The visit customer must match the inquiry customer."))

    def action_complete(self):
        for record in self:
            record.status = "completed"

    def action_mark_interested(self):
        for record in self:
            record.status = "interested"

    def action_send_offer(self):
        for record in self:
            record.status = "offer_sent"

    def action_close(self):
        for record in self:
            record.status = "closed"

    def action_mark_lost(self):
        for record in self:
            record.status = "lost"

    def action_cancel(self):
        for record in self:
            record.status = "cancelled"

    def action_reset_to_scheduled(self):
        for record in self:
            record.status = "scheduled"

    def action_suggest_matching_properties(self):
        self.ensure_one()

        domain = [("status", "=", "available")]
        if self.preferred_property_type:
            domain.append(("property_type", "=", self.preferred_property_type))
        if self.preferred_location:
            domain.append(("location", "ilike", self.preferred_location))
        if self.preferred_budget:
            domain.append(("price", "<=", self.preferred_budget))

        return {
            "type": "ir.actions.act_window",
            "name": _("Suggested Properties"),
            "res_model": "palmate.property",
            "view_mode": "kanban,list,form",
            "domain": domain,
            "context": {
                "search_default_available": 1,
                "default_agent_id": self.agent_id.id,
            },
        }

    def action_create_reservation(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Reservation"),
            "res_model": "palmate.property.reservation",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_visit_id": self.id,
                "default_inquiry_id": self.inquiry_id.id,
                "default_property_id": self.property_id.id,
                "default_customer_id": self.customer_id.id,
                "default_agent_id": self.agent_id.id,
            },
        }
