from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PalmatePropertyInquiry(models.Model):
    _name = "palmate.property.inquiry"
    _description = "Property Inquiry"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string = "Inquiry Reference",
        required = True,
        default = "/",
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
    reservation_ids = fields.One2many(
        "palmate.property.reservation",
        "inquiry_id",
        string = "Reservations",
    )
    contract_ids = fields.One2many(
        "palmate.property.contract",
        "inquiry_id",
        string = "Contracts",
    )
    visit_count = fields.Integer(
        string = "Visit Count",
        compute = "_compute_visit_count",
    )
    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Medium"),
            ("2", "High"),
        ],
        string = "Priority",
        default = "1",
        tracking = True,
    )
    followup_date = fields.Date(
        string = "Next Follow-up",
        tracking = True,
    )
    expected_close_date = fields.Date(
        string = "Expected Close Date",
        tracking = True,
    )
    probability = fields.Float(
        string = "Probability %",
        default = 10.0,
        tracking = True,
    )

    def _compute_visit_count(self):
        for record in self:
            record.visit_count = len(record.visit_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("palmate.property.inquiry") or "/"
        return super().create(vals_list)

    def action_qualify(self):
        for record in self:
            record.status = "qualified"
            record.probability = max(record.probability, 35.0)

    def action_schedule_visit(self):
        for record in self:
            record.status = "visit_scheduled"
            record.probability = max(record.probability, 50.0)

    def action_send_offer(self):
        for record in self:
            record.status = "offer_sent"
            record.probability = max(record.probability, 75.0)

    def action_mark_won(self):
        for record in self:
            record.status = "won"
            record.probability = 100.0

    def action_mark_lost(self):
        for record in self:
            record.status = "lost"
            record.probability = 0.0

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

    def action_create_reservation(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Reservation"),
            "res_model": "palmate.property.reservation",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_inquiry_id": self.id,
                "default_property_id": self.property_id.id,
                "default_customer_id": self.customer_id.id,
                "default_agent_id": self.agent_id.id,
            },
        }


class PalmatePropertyReservation(models.Model):
    _name = "palmate.property.reservation"
    _description = "Property Reservation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "reservation_date desc"

    name = fields.Char(
        string = "Reservation Reference",
        required = True,
        default = "/",
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
    visit_id = fields.Many2one(
        "palmate.property.visit",
        string = "Visit",
        tracking = True,
    )
    agent_id = fields.Many2one(
        "res.users",
        string = "Agent",
        default = lambda self: self.env.user,
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
    days_to_expiry = fields.Integer(
        string = "Days to Expiry",
        compute = "_compute_days_to_expiry",
    )

    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.expiry_date:
                record.days_to_expiry = (record.expiry_date - today).days
            else:
                record.days_to_expiry = 0

    @api.onchange("inquiry_id")
    def _onchange_inquiry_id(self):
        for record in self:
            if record.inquiry_id:
                record.property_id = record.inquiry_id.property_id
                record.customer_id = record.inquiry_id.customer_id
                record.agent_id = record.inquiry_id.agent_id

    @api.onchange("visit_id")
    def _onchange_visit_id(self):
        for record in self:
            if record.visit_id:
                record.inquiry_id = record.visit_id.inquiry_id
                record.property_id = record.visit_id.property_id
                record.customer_id = record.visit_id.customer_id
                record.agent_id = record.visit_id.agent_id

    @api.constrains("inquiry_id", "visit_id", "property_id", "customer_id")
    def _check_reservation_consistency(self):
        for record in self:
            if record.inquiry_id:
                if record.inquiry_id.property_id and record.property_id and record.inquiry_id.property_id != record.property_id:
                    raise ValidationError(_("The reservation property must match the inquiry property."))
                if record.customer_id and record.inquiry_id.customer_id != record.customer_id:
                    raise ValidationError(_("The reservation customer must match the inquiry customer."))
            if record.visit_id:
                if record.visit_id.property_id and record.property_id and record.visit_id.property_id != record.property_id:
                    raise ValidationError(_("The reservation property must match the visit property."))
                if record.customer_id and record.visit_id.customer_id != record.customer_id:
                    raise ValidationError(_("The reservation customer must match the visit customer."))
                if record.inquiry_id and record.visit_id.inquiry_id and record.inquiry_id != record.visit_id.inquiry_id:
                    raise ValidationError(_("The reservation inquiry must match the linked visit inquiry."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("palmate.property.reservation") or "/"
            visit_id = vals.get("visit_id")
            inquiry_id = vals.get("inquiry_id")
            if visit_id:
                visit = self.env["palmate.property.visit"].browse(visit_id)
                vals.setdefault("inquiry_id", visit.inquiry_id.id)
                vals.setdefault("property_id", visit.property_id.id)
                vals.setdefault("customer_id", visit.customer_id.id)
                vals.setdefault("agent_id", visit.agent_id.id)
            elif inquiry_id:
                inquiry = self.env["palmate.property.inquiry"].browse(inquiry_id)
                vals.setdefault("property_id", inquiry.property_id.id)
                vals.setdefault("customer_id", inquiry.customer_id.id)
                vals.setdefault("agent_id", inquiry.agent_id.id)
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

    def action_create_contract(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Contract"),
            "res_model": "palmate.property.contract",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_reservation_id": self.id,
                "default_visit_id": self.visit_id.id,
                "default_inquiry_id": self.inquiry_id.id,
                "default_property_id": self.property_id.id,
                "default_customer_id": self.customer_id.id,
                "default_agent_id": self.agent_id.id,
            },
        }


class PalmatePropertyContract(models.Model):
    _name = "palmate.property.contract"
    _description = "Property Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_date desc, create_date desc"

    name = fields.Char(
        string = "Contract Reference",
        required = True,
        default = "/",
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
    visit_id = fields.Many2one(
        "palmate.property.visit",
        string = "Visit",
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
    paid_amount = fields.Monetary(
        string = "Paid Amount",
        currency_field = "currency_id",
        compute = "_compute_payment_totals",
        store = True,
    )
    outstanding_amount = fields.Monetary(
        string = "Outstanding Amount",
        currency_field = "currency_id",
        compute = "_compute_payment_totals",
        store = True,
    )
    payment_progress = fields.Float(
        string = "Payment Progress %",
        compute = "_compute_payment_totals",
        store = True,
    )

    @api.depends("amount", "payment_line_ids.amount", "payment_line_ids.paid")
    def _compute_payment_totals(self):
        for record in self:
            paid_amount = sum(record.payment_line_ids.filtered("paid").mapped("amount"))
            total_amount = record.amount or sum(record.payment_line_ids.mapped("amount"))
            record.paid_amount = paid_amount
            record.outstanding_amount = max(total_amount - paid_amount, 0.0)
            record.payment_progress = (paid_amount / total_amount * 100.0) if total_amount else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("palmate.property.contract") or "/"
            reservation_id = vals.get("reservation_id")
            visit_id = vals.get("visit_id")
            inquiry_id = vals.get("inquiry_id")
            if reservation_id:
                reservation = self.env["palmate.property.reservation"].browse(reservation_id)
                vals.setdefault("visit_id", reservation.visit_id.id)
                vals.setdefault("inquiry_id", reservation.inquiry_id.id)
                vals.setdefault("property_id", reservation.property_id.id)
                vals.setdefault("customer_id", reservation.customer_id.id)
                vals.setdefault("agent_id", reservation.agent_id.id)
            elif visit_id:
                visit = self.env["palmate.property.visit"].browse(visit_id)
                vals.setdefault("inquiry_id", visit.inquiry_id.id)
                vals.setdefault("property_id", visit.property_id.id)
                vals.setdefault("customer_id", visit.customer_id.id)
                vals.setdefault("agent_id", visit.agent_id.id)
            elif inquiry_id:
                inquiry = self.env["palmate.property.inquiry"].browse(inquiry_id)
                vals.setdefault("property_id", inquiry.property_id.id)
                vals.setdefault("customer_id", inquiry.customer_id.id)
                vals.setdefault("agent_id", inquiry.agent_id.id)
        return super().create(vals_list)

    @api.onchange("reservation_id")
    def _onchange_reservation_id(self):
        for record in self:
            if record.reservation_id:
                record.property_id = record.reservation_id.property_id
                record.customer_id = record.reservation_id.customer_id
                record.agent_id = record.reservation_id.agent_id
                record.inquiry_id = record.reservation_id.inquiry_id
                record.visit_id = record.reservation_id.visit_id

    @api.onchange("visit_id")
    def _onchange_visit_id(self):
        for record in self:
            if record.visit_id:
                record.property_id = record.visit_id.property_id
                record.customer_id = record.visit_id.customer_id
                record.agent_id = record.visit_id.agent_id
                record.inquiry_id = record.visit_id.inquiry_id

    @api.onchange("inquiry_id")
    def _onchange_inquiry_id(self):
        for record in self:
            if record.inquiry_id:
                record.property_id = record.inquiry_id.property_id
                record.customer_id = record.inquiry_id.customer_id
                record.agent_id = record.inquiry_id.agent_id

    @api.constrains("reservation_id", "visit_id", "inquiry_id", "property_id", "customer_id")
    def _check_contract_consistency(self):
        for record in self:
            if record.reservation_id:
                if record.property_id and record.reservation_id.property_id != record.property_id:
                    raise ValidationError(_("The contract property must match the reservation property."))
                if record.customer_id and record.reservation_id.customer_id != record.customer_id:
                    raise ValidationError(_("The contract customer must match the reservation customer."))
                if record.visit_id and record.reservation_id.visit_id and record.visit_id != record.reservation_id.visit_id:
                    raise ValidationError(_("The contract visit must match the reservation visit."))
                if record.inquiry_id and record.reservation_id.inquiry_id and record.inquiry_id != record.reservation_id.inquiry_id:
                    raise ValidationError(_("The contract inquiry must match the reservation inquiry."))
            if record.visit_id:
                if record.property_id and record.visit_id.property_id and record.visit_id.property_id != record.property_id:
                    raise ValidationError(_("The contract property must match the visit property."))
                if record.customer_id and record.visit_id.customer_id != record.customer_id:
                    raise ValidationError(_("The contract customer must match the visit customer."))
                if record.inquiry_id and record.visit_id.inquiry_id and record.inquiry_id != record.visit_id.inquiry_id:
                    raise ValidationError(_("The contract inquiry must match the visit inquiry."))
            if record.inquiry_id:
                if record.property_id and record.inquiry_id.property_id and record.inquiry_id.property_id != record.property_id:
                    raise ValidationError(_("The contract property must match the inquiry property."))
                if record.customer_id and record.inquiry_id.customer_id != record.customer_id:
                    raise ValidationError(_("The contract customer must match the inquiry customer."))

    def action_sign(self):
        for record in self:
            record.status = "signed"

    def action_activate(self):
        for record in self:
            record.status = "active"
            record.property_id.status = "sold" if record.contract_type == "sale" else "rented"
            if record.reservation_id:
                record.reservation_id.status = "converted"
            if record.inquiry_id:
                record.inquiry_id.status = "won"

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
        default = "/",
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
    reported_date = fields.Date(
        string = "Reported Date",
        default = fields.Date.context_today,
        tracking = True,
    )
    completion_date = fields.Date(
        string = "Completion Date",
        tracking = True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("palmate.maintenance.request") or "/"
        return super().create(vals_list)

    def action_start(self):
        for record in self:
            record.status = "in_progress"

    def action_done(self):
        for record in self:
            record.status = "done"
            record.completion_date = fields.Date.context_today(record)
