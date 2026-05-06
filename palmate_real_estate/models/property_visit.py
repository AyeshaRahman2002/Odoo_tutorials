from odoo import _, fields, models


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
