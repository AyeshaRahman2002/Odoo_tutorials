from odoo import fields, models


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
        string = "Property",
        required = True,
        tracking = True,
    )

    customer_id = fields.Many2one(
        "res.partner",
        string = "Customer",
        required = True,
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

    def action_complete(self):
        for record in self:
            record.status = "completed"

    def action_cancel(self):
        for record in self:
            record.status = "cancelled"

    def action_reset_to_scheduled(self):
        for record in self:
            record.status = "scheduled"