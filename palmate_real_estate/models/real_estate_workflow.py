from odoo import _, api, fields, models


class PalmatePropertyInquiry(models.Model):
    _name = "palmate.property.inquiry"
    _description = "Property Inquiry"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string = "Inquiry Reference",
        required = True,
        default = "New Inquiry",
        tracking = True,
    )
    property_id = fields.Many2one(
        "palmate.property",
        string = "Property",
        tracking = True,
    )
    customer_id = fields.Many2one(
        "res.partner",
        string = "Customer",
        required = True,
        tracking = True,
    )
    preferred_location = fields.Char(
        string = "Preferred Location",
        tracking = True,
    )
    budget = fields.Monetary(
        string = "Budget",
        currency_field = "currency_id",
        tracking = True,
    )
    property_type = fields.Selection(
        selection = lambda self: self.env["palmate.property"]._fields["property_type"].selection,
        string = "Property Type",
        tracking = True,
    )
    agent_id = fields.Many2one(
        "res.users",
        string = "Assigned Agent",
        default = lambda self: self.env.user,
        tracking = True,
    )
    source = fields.Selection(
        [
            ("website", "Website"),
            ("walk_in", "Walk-in"),
            ("whatsapp", "WhatsApp"),
            ("referral", "Referral"),
        ],
        string = "Source",
        default = "website",
        tracking = True,
    )
    status = fields.Selection(
        [
            ("inquiry", "Inquiry"),
            ("qualified", "Qualified"),
            ("visit_scheduled", "Visit Scheduled"),
            ("offer_sent", "Offer Sent"),
            ("won", "Won"),
            ("lost", "Lost"),
        ],
        string = "Status",
        default = "inquiry",
        required = True,
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
    notes = fields.Text(string = "Notes")
    visit_ids = fields.One2many(
        "palmate.property.visit",
        "inquiry_id",
        string = "Visits",
    )
    visit_count = fields.Integer(
        string = "Visit Count",
        compute = "_compute_visit_count",
    )

    def _compute_visit_count(self):
        for record in self:
            record.visit_count = len(record.visit_ids)

    def action_qualify(self):
        for record in self:
            record.status = "qualified"

    def action_schedule_visit(self):
        for record in self:
            record.status = "visit_scheduled"

    def action_send_offer(self):
        for record in self:
            record.status = "offer_sent"

    def action_mark_won(self):
        for record in self:
            record.status = "won"

    def action_mark_lost(self):
        for record in self:
            record.status = "lost"

    def action_create_visit(self):
        self.ensure_one()
        self.status = "visit_scheduled"
        return {
            "type": "ir.actions.act_window",
            "name": _("Schedule Visit"),
            "res_model": "palmate.property.visit",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_inquiry_id": self.id,
                "default_property_id": self.property_id.id,
                "default_customer_id": self.customer_id.id,
                "default_agent_id": self.agent_id.id,
                "default_preferred_location": self.preferred_location,
                "default_preferred_budget": self.budget,
                "default_preferred_property_type": self.property_type,
            },
        }

    def action_view_visits(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Inquiry Visits"),
            "res_model": "palmate.property.visit",
            "view_mode": "list,form",
            "domain": [("inquiry_id", "=", self.id)],
            "context": {"default_inquiry_id": self.id},
        }


class PalmatePropertyReservation(models.Model):
    _name = "palmate.property.reservation"
    _description = "Property Reservation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "reservation_date desc"

    name = fields.Char(
        string = "Reservation Reference",
        required = True,
        default = "New Reservation",
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
    reservation_date = fields.Date(
        string = "Reservation Date",
        default = fields.Date.context_today,
        required = True,
        tracking = True,
    )
    expiry_date = fields.Date(
        string = "Expiry Date",
        tracking = True,
    )
    deposit_amount = fields.Monetary(
        string = "Deposit Amount",
        currency_field = "currency_id",
        tracking = True,
    )
    status = fields.Selection(
        [
            ("active", "Active"),
            ("expired", "Expired"),
            ("converted", "Converted"),
            ("cancelled", "Cancelled"),
        ],
        string = "Status",
        default = "active",
        required = True,
        tracking = True,
    )
    inquiry_id = fields.Many2one(
        "palmate.property.inquiry",
        string = "Inquiry",
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
    notes = fields.Text(string = "Notes")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.property_id.status = "reserved"
        return records

    def action_activate(self):
        for record in self:
            record.status = "active"
            record.property_id.status = "reserved"

    def action_expire(self):
        for record in self:
            record.status = "expired"
            if record.property_id.status == "reserved":
                record.property_id.status = "available"

    def action_convert(self):
        for record in self:
            record.status = "converted"

    def action_cancel(self):
        for record in self:
            record.status = "cancelled"
            if record.property_id.status == "reserved":
                record.property_id.status = "available"


class PalmatePropertyContract(models.Model):
    _name = "palmate.property.contract"
    _description = "Property Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_date desc, create_date desc"

    name = fields.Char(
        string = "Contract Reference",
        required = True,
        default = "New Contract",
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
    contract_type = fields.Selection(
        [
            ("sale", "Sale"),
            ("rent", "Rent"),
        ],
        string = "Contract Type",
        required = True,
        default = "sale",
        tracking = True,
    )
    start_date = fields.Date(
        string = "Start Date",
        required = True,
        tracking = True,
    )
    end_date = fields.Date(
        string = "End Date",
        tracking = True,
    )
    amount = fields.Monetary(
        string = "Amount",
        currency_field = "currency_id",
        tracking = True,
    )
    payment_plan = fields.Text(string = "Payment Plan")
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("signed", "Signed"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        string = "Status",
        default = "draft",
        required = True,
        tracking = True,
    )
    reservation_id = fields.Many2one(
        "palmate.property.reservation",
        string = "Reservation",
        tracking = True,
    )
    inquiry_id = fields.Many2one(
        "palmate.property.inquiry",
        string = "Inquiry",
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
    payment_line_ids = fields.One2many(
        "palmate.contract.payment",
        "contract_id",
        string = "Payment Plan Lines",
    )
    commission_ids = fields.One2many(
        "palmate.agent.commission",
        "contract_id",
        string = "Commissions",
    )

    def action_sign(self):
        for record in self:
            record.status = "signed"

    def action_activate(self):
        for record in self:
            record.status = "active"
            record.property_id.status = "sold" if record.contract_type == "sale" else "rented"
            if record.reservation_id:
                record.reservation_id.status = "converted"

    def action_close(self):
        for record in self:
            record.status = "closed"


class PalmateContractPayment(models.Model):
    _name = "palmate.contract.payment"
    _description = "Contract Payment Plan Line"
    _order = "due_date asc, id asc"

    name = fields.Char(
        string = "Milestone",
        required = True,
    )
    contract_id = fields.Many2one(
        "palmate.property.contract",
        string = "Contract",
        required = True,
        ondelete = "cascade",
    )
    due_date = fields.Date(
        string = "Due Date",
        required = True,
    )
    amount = fields.Monetary(
        string = "Amount",
        currency_field = "currency_id",
        required = True,
    )
    paid = fields.Boolean(string = "Paid")
    payment_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("overdue", "Overdue"),
            ("paid", "Paid"),
        ],
        string = "Payment Status",
        compute = "_compute_payment_status",
        store = True,
    )
    currency_id = fields.Many2one(
        related = "contract_id.currency_id",
        comodel_name = "res.currency",
        string = "Currency",
        store = True,
        readonly = True,
    )
    customer_id = fields.Many2one(
        related = "contract_id.customer_id",
        comodel_name = "res.partner",
        string = "Customer",
        store = True,
        readonly = True,
    )

    @api.depends("paid", "due_date")
    def _compute_payment_status(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.paid:
                record.payment_status = "paid"
            elif record.due_date and record.due_date < today:
                record.payment_status = "overdue"
            else:
                record.payment_status = "pending"


class PalmateAgentCommission(models.Model):
    _name = "palmate.agent.commission"
    _description = "Agent Commission"
    _order = "create_date desc"

    agent_id = fields.Many2one(
        "res.users",
        string = "Agent",
        required = True,
    )
    contract_id = fields.Many2one(
        "palmate.property.contract",
        string = "Contract",
        required = True,
        ondelete = "cascade",
    )
    commission_percent = fields.Float(
        string = "Commission %",
        digits = (16, 2),
        default = 5.0,
    )
    commission_amount = fields.Monetary(
        string = "Commission Amount",
        currency_field = "currency_id",
        compute = "_compute_commission_amount",
        store = True,
    )
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("paid", "Paid"),
        ],
        string = "Status",
        default = "pending",
        required = True,
    )
    currency_id = fields.Many2one(
        related = "contract_id.currency_id",
        comodel_name = "res.currency",
        string = "Currency",
        store = True,
        readonly = True,
    )

    @api.depends("contract_id.amount", "commission_percent")
    def _compute_commission_amount(self):
        for record in self:
            record.commission_amount = (record.contract_id.amount or 0.0) * (record.commission_percent or 0.0) / 100.0

    def action_approve(self):
        for record in self:
            record.status = "approved"

    def action_mark_paid(self):
        for record in self:
            record.status = "paid"


class PalmateMaintenanceRequest(models.Model):
    _name = "palmate.maintenance.request"
    _description = "Maintenance Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string = "Request Reference",
        required = True,
        default = "New Maintenance Request",
        tracking = True,
    )
    property_id = fields.Many2one(
        "palmate.property",
        string = "Property",
        required = True,
        tracking = True,
    )
    tenant_id = fields.Many2one(
        "res.partner",
        string = "Tenant",
        tracking = True,
    )
    issue_type = fields.Selection(
        [
            ("electrical", "Electrical"),
            ("plumbing", "Plumbing"),
            ("hvac", "HVAC"),
            ("cleaning", "Cleaning"),
            ("other", "Other"),
        ],
        string = "Issue Type",
        required = True,
        default = "other",
        tracking = True,
    )
    priority = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        string = "Priority",
        default = "medium",
        tracking = True,
    )
    assigned_partner_id = fields.Many2one(
        "res.partner",
        string = "Assigned Person / Vendor",
        tracking = True,
    )
    status = fields.Selection(
        [
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
        ],
        string = "Status",
        default = "new",
        required = True,
        tracking = True,
    )
    cost = fields.Monetary(
        string = "Cost",
        currency_field = "currency_id",
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
    description = fields.Text(string = "Description")

    def action_start(self):
        for record in self:
            record.status = "in_progress"

    def action_done(self):
        for record in self:
            record.status = "done"
