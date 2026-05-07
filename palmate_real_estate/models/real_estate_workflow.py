from datetime import timedelta

from odoo import _, Command, api, fields, models
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
    reservation_count = fields.Integer(
        string = "Reservation Count",
        compute = "_compute_flow_counts",
    )
    contract_count = fields.Integer(
        string = "Contract Count",
        compute = "_compute_flow_counts",
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
    overdue_followup = fields.Boolean(
        string = "Overdue Follow-up",
        compute = "_compute_followup_flags",
        store = True,
    )
    followup_reminder_sent_on = fields.Date(
        string = "Follow-up Reminder Sent On",
        copy = False,
    )
    crm_lead_id = fields.Many2one(
        "crm.lead",
        string = "CRM Opportunity",
        copy = False,
        tracking = True,
    )
    lost_reason = fields.Char(
        string = "Lost Reason",
        tracking = True,
    )

    def _compute_visit_count(self):
        for record in self:
            record.visit_count = len(record.visit_ids)

    def _compute_flow_counts(self):
        for record in self:
            record.reservation_count = len(record.reservation_ids)
            record.contract_count = len(record.contract_ids)

    @api.depends("followup_date", "status")
    def _compute_followup_flags(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.overdue_followup = bool(
                record.followup_date
                and record.followup_date < today
                and record.status not in ("won", "lost")
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("palmate.property.inquiry") or "/"
        records = super().create(vals_list)
        for record in records.filtered(lambda inquiry: inquiry.customer_id and not inquiry.crm_lead_id):
            record.crm_lead_id = record.env["crm.lead"].create(record._prepare_crm_lead_vals())
            record._sync_crm_stage_from_status()
        return records

    def _prepare_crm_lead_vals(self):
        self.ensure_one()
        description_parts = [self.notes or ""]
        if self.property_id:
            description_parts.append(_("Property: %s") % self.property_id.display_name)
        if self.preferred_location:
            description_parts.append(_("Preferred location: %s") % self.preferred_location)
        if self.property_type:
            property_types = dict(self.fields_get(["property_type"])["property_type"]["selection"])
            description_parts.append(
                _("Preferred property type: %s") % property_types.get(self.property_type, self.property_type)
            )
        if self.budget:
            description_parts.append(_("Budget: %s %.2f") % (self.currency_id.symbol or "", self.budget))
        return {
            "name": self.name,
            "type": "opportunity",
            "partner_id": self.customer_id.id,
            "user_id": self.agent_id.id or self.env.user.id,
            "expected_revenue": self.budget or self.property_id.price or 0.0,
            "probability": self.probability,
            "date_deadline": self.expected_close_date,
            "description": "<br/>".join(filter(None, description_parts)),
        }

    def _sync_crm_stage_from_status(self):
        non_won_stages = self.env["crm.stage"].search([("is_won", "=", False)], order="sequence asc")
        stage_index_map = {
            "inquiry": 0,
            "qualified": 1,
            "visit_scheduled": 2,
            "offer_sent": 3,
        }
        for record in self.filtered("crm_lead_id"):
            lead = record.crm_lead_id
            if record.status == "won":
                lead.action_set_won()
                continue
            if record.status == "lost":
                lead.action_set_lost()
                continue
            vals = record._prepare_crm_lead_vals()
            if non_won_stages:
                vals["stage_id"] = non_won_stages[min(stage_index_map.get(record.status, 0), len(non_won_stages) - 1)].id
            vals["active"] = True
            lead.write(vals)

    def action_create_crm_opportunity(self):
        self.ensure_one()
        if not self.crm_lead_id:
            self.crm_lead_id = self.env["crm.lead"].create(self._prepare_crm_lead_vals())
            self._sync_crm_stage_from_status()
        return self.action_view_crm_opportunity()

    def action_view_crm_opportunity(self):
        self.ensure_one()
        if not self.crm_lead_id:
            return self.action_create_crm_opportunity()
        return {
            "type": "ir.actions.act_window",
            "name": _("CRM Opportunity"),
            "res_model": "crm.lead",
            "res_id": self.crm_lead_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_qualify(self):
        for record in self:
            record.status = "qualified"
            record.probability = max(record.probability, 35.0)
            record._sync_crm_stage_from_status()

    def action_schedule_visit(self):
        for record in self:
            record.status = "visit_scheduled"
            record.probability = max(record.probability, 50.0)
            record._sync_crm_stage_from_status()

    def action_send_offer(self):
        for record in self:
            record.status = "offer_sent"
            record.probability = max(record.probability, 75.0)
            record._sync_crm_stage_from_status()

    def action_mark_won(self):
        for record in self:
            record.status = "won"
            record.probability = 100.0
            if record.crm_lead_id:
                record.crm_lead_id.action_set_won()

    def action_mark_lost(self):
        for record in self:
            record.status = "lost"
            record.probability = 0.0
            if record.crm_lead_id:
                record.crm_lead_id.action_set_lost()

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

    def action_send_inquiry_email(self):
        template = self.env.ref("palmate_real_estate.mail_template_property_inquiry_update")
        for record in self:
            if record.customer_id.email:
                template.send_mail(record.id, force_send=False)
        return True

    def action_view_reservations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Inquiry Reservations"),
            "res_model": "palmate.property.reservation",
            "view_mode": "list,form",
            "domain": [("inquiry_id", "=", self.id)],
            "context": {"default_inquiry_id": self.id},
        }

    def action_view_contracts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Inquiry Contracts"),
            "res_model": "palmate.property.contract",
            "view_mode": "list,form",
            "domain": [("inquiry_id", "=", self.id)],
            "context": {"default_inquiry_id": self.id},
        }

    def write(self, vals):
        result = super().write(vals)
        sync_fields = {
            "name",
            "property_id",
            "customer_id",
            "agent_id",
            "budget",
            "probability",
            "expected_close_date",
            "preferred_location",
            "property_type",
            "notes",
        }
        if sync_fields.intersection(vals):
            for record in self.filtered("crm_lead_id"):
                record.crm_lead_id.write(record._prepare_crm_lead_vals())
                record._sync_crm_stage_from_status()
        return result

    @api.model
    def _cron_schedule_followup_activities(self):
        today = fields.Date.context_today(self)
        model_id = self.env["ir.model"]._get_id(self._name)
        todo_type = self.env.ref("mail.mail_activity_data_todo")

        inquiries = self.search([
            ("followup_date", "<=", today),
            ("status", "not in", ("won", "lost")),
        ])
        for inquiry in inquiries:
            if inquiry.followup_reminder_sent_on == today:
                continue
            summary = _("Follow up on inquiry %s") % inquiry.name
            existing = self.env["mail.activity"].search_count([
                ("res_model_id", "=", model_id),
                ("res_id", "=", inquiry.id),
                ("summary", "=", summary),
                ("date_deadline", "=", today),
                ("user_id", "=", inquiry.agent_id.id or self.env.user.id),
            ])
            if not existing:
                self.env["mail.activity"].create({
                    "activity_type_id": todo_type.id,
                    "res_model_id": model_id,
                    "res_id": inquiry.id,
                    "user_id": inquiry.agent_id.id or self.env.user.id,
                    "summary": summary,
                    "note": _(
                        "This inquiry requires follow-up with %(customer)s regarding %(property)s."
                    ) % {
                        "customer": inquiry.customer_id.display_name,
                        "property": inquiry.property_id.display_name or _("the requested property"),
                    },
                    "date_deadline": today,
                })
            inquiry.followup_reminder_sent_on = today


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
    contract_ids = fields.One2many(
        "palmate.property.contract",
        "reservation_id",
        string = "Contracts",
    )
    contract_count = fields.Integer(
        string = "Contract Count",
        compute = "_compute_contract_count",
    )
    days_to_expiry = fields.Integer(
        string = "Days to Expiry",
        compute = "_compute_days_to_expiry",
    )
    expiring_soon = fields.Boolean(
        string = "Expiring Soon",
        compute = "_compute_days_to_expiry",
    )
    expiry_reminder_sent_on = fields.Date(
        string = "Expiry Reminder Sent On",
        copy = False,
    )
    extension_requested = fields.Boolean(
        string = "Extension Requested",
        tracking = True,
    )
    extension_days = fields.Integer(
        string = "Extension Days",
        default = 7,
        tracking = True,
    )
    extension_approved = fields.Boolean(
        string = "Extension Approved",
        copy = False,
        tracking = True,
    )

    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.expiry_date:
                record.days_to_expiry = (record.expiry_date - today).days
            else:
                record.days_to_expiry = 0
            record.expiring_soon = bool(
                record.expiry_date
                and record.status == "active"
                and record.days_to_expiry <= 2
            )

    def _compute_contract_count(self):
        for record in self:
            record.contract_count = len(record.contract_ids)

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
        records.mapped("property_id")._sync_status_from_pipeline()
        return records

    def write(self, vals):
        properties = self.mapped("property_id")
        result = super().write(vals)
        (properties | self.mapped("property_id"))._sync_status_from_pipeline()
        return result

    def unlink(self):
        properties = self.mapped("property_id")
        result = super().unlink()
        properties._sync_status_from_pipeline()
        return result

    def action_activate(self):
        for record in self:
            record.status = "active"
        self.mapped("property_id")._sync_status_from_pipeline()

    def action_expire(self):
        for record in self:
            record.status = "expired"
        self.mapped("property_id")._sync_status_from_pipeline()

    def action_convert(self):
        for record in self:
            record.status = "converted"
        self.mapped("property_id")._sync_status_from_pipeline()

    def action_cancel(self):
        for record in self:
            record.status = "cancelled"
        self.mapped("property_id")._sync_status_from_pipeline()

    def action_request_extension(self):
        for record in self:
            if not record.expiry_date:
                raise ValidationError(_("Set an expiry date before requesting an extension."))
            if record.extension_days <= 0:
                raise ValidationError(_("Extension days must be greater than zero."))
            record.extension_requested = True
            record.extension_approved = False

    def action_approve_extension(self):
        for record in self:
            if not record.extension_requested:
                raise ValidationError(_("There is no pending extension request to approve."))
            record.expiry_date = record.expiry_date + timedelta(days=record.extension_days or 0)
            record.extension_requested = False
            record.extension_approved = True

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

    def action_send_reservation_email(self):
        template = self.env.ref("palmate_real_estate.mail_template_property_reservation_update")
        for record in self:
            if record.customer_id.email:
                template.send_mail(record.id, force_send=False)
        return True

    def action_view_contracts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Reservation Contracts"),
            "res_model": "palmate.property.contract",
            "view_mode": "list,form",
            "domain": [("reservation_id", "=", self.id)],
            "context": {"default_reservation_id": self.id},
        }

    @api.model
    def _cron_schedule_expiry_activities(self):
        today = fields.Date.context_today(self)
        limit_date = today + timedelta(days=2)
        model_id = self.env["ir.model"]._get_id(self._name)
        todo_type = self.env.ref("mail.mail_activity_data_todo")

        reservations = self.search([
            ("status", "=", "active"),
            ("expiry_date", "!=", False),
            ("expiry_date", "<=", limit_date),
        ])
        for reservation in reservations:
            if reservation.expiry_reminder_sent_on == today:
                continue
            summary = _("Reservation expiring soon: %s") % reservation.name
            existing = self.env["mail.activity"].search_count([
                ("res_model_id", "=", model_id),
                ("res_id", "=", reservation.id),
                ("summary", "=", summary),
                ("user_id", "=", reservation.agent_id.id or self.env.user.id),
            ])
            if not existing:
                self.env["mail.activity"].create({
                    "activity_type_id": todo_type.id,
                    "res_model_id": model_id,
                    "res_id": reservation.id,
                    "user_id": reservation.agent_id.id or self.env.user.id,
                    "summary": summary,
                    "note": _(
                        "Reservation %(reservation)s for %(customer)s expires on %(expiry)s."
                    ) % {
                        "reservation": reservation.name,
                        "customer": reservation.customer_id.display_name,
                        "expiry": reservation.expiry_date,
                    },
                    "date_deadline": reservation.expiry_date,
                })
            reservation.expiry_reminder_sent_on = today


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
    maintenance_request_ids = fields.One2many(
        "palmate.maintenance.request",
        "contract_id",
        string = "Maintenance Requests",
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
    payment_count = fields.Integer(
        string = "Payment Count",
        compute = "_compute_related_counts",
    )
    commission_count = fields.Integer(
        string = "Commission Count",
        compute = "_compute_related_counts",
    )
    maintenance_count = fields.Integer(
        string = "Maintenance Count",
        compute = "_compute_related_counts",
    )
    invoice_count = fields.Integer(
        string = "Invoice Count",
        compute = "_compute_related_counts",
    )
    discount_amount = fields.Monetary(
        string = "Discount Amount",
        currency_field = "currency_id",
        tracking = True,
    )
    discount_approved = fields.Boolean(
        string = "Discount Approved",
        copy = False,
        tracking = True,
    )
    booking_percent_required = fields.Float(
        string = "Required Paid % Before Activation",
        default = 10.0,
        tracking = True,
    )
    required_booking_amount = fields.Monetary(
        string = "Required Paid Amount",
        currency_field = "currency_id",
        compute = "_compute_payment_totals",
        store = True,
    )
    net_amount = fields.Monetary(
        string = "Net Amount",
        currency_field = "currency_id",
        compute = "_compute_payment_totals",
        store = True,
    )

    @api.depends(
        "amount",
        "discount_amount",
        "booking_percent_required",
        "payment_line_ids.amount",
        "payment_line_ids.paid",
        "payment_line_ids.invoice_payment_state",
    )
    def _compute_payment_totals(self):
        for record in self:
            paid_lines = record.payment_line_ids.filtered(
                lambda line: line.paid or line.invoice_payment_state in ("paid", "in_payment")
            )
            paid_amount = sum(paid_lines.mapped("amount"))
            total_amount = record.amount or sum(record.payment_line_ids.mapped("amount"))
            net_amount = max(total_amount - (record.discount_amount or 0.0), 0.0)
            record.paid_amount = paid_amount
            record.net_amount = net_amount
            record.required_booking_amount = net_amount * (record.booking_percent_required or 0.0) / 100.0
            record.outstanding_amount = max(net_amount - paid_amount, 0.0)
            record.payment_progress = (paid_amount / net_amount * 100.0) if net_amount else 0.0

    def _compute_related_counts(self):
        for record in self:
            record.payment_count = len(record.payment_line_ids)
            record.commission_count = len(record.commission_ids)
            record.maintenance_count = len(record.maintenance_request_ids)
            record.invoice_count = len(record.payment_line_ids.mapped("invoice_id"))

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
        records = super().create(vals_list)
        records.mapped("property_id")._sync_status_from_pipeline()
        return records

    def write(self, vals):
        properties = self.mapped("property_id")
        result = super().write(vals)
        (properties | self.mapped("property_id"))._sync_status_from_pipeline()
        return result

    def unlink(self):
        properties = self.mapped("property_id")
        result = super().unlink()
        properties._sync_status_from_pipeline()
        return result

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
            if record.discount_amount and not record.discount_approved:
                raise ValidationError(_("Approve the contract discount before signing the contract."))
            record.status = "signed"
        self.mapped("property_id")._sync_status_from_pipeline()

    def action_activate(self):
        for record in self:
            if record.status != "signed":
                raise ValidationError(_("Only signed contracts can be activated."))
            if record.discount_amount and not record.discount_approved:
                raise ValidationError(_("Approve the discount before activating the contract."))
            if record.payment_line_ids and record.paid_amount < record.required_booking_amount:
                raise ValidationError(
                    _(
                        "This contract requires at least %(required).2f to be paid before activation. "
                        "Current paid amount is %(paid).2f."
                    ) % {
                        "required": record.required_booking_amount,
                        "paid": record.paid_amount,
                    }
                )
            record.status = "active"
            if record.reservation_id:
                record.reservation_id.status = "converted"
            if record.inquiry_id:
                record.inquiry_id.status = "won"
        self.mapped("property_id")._sync_status_from_pipeline()

    def action_close(self):
        for record in self:
            record.status = "closed"
        self.mapped("property_id")._sync_status_from_pipeline()

    def action_send_contract_email(self):
        template = self.env.ref("palmate_real_estate.mail_template_property_contract_update")
        for record in self:
            if record.customer_id.email:
                template.send_mail(record.id, force_send=False)
        return True

    def action_view_payments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Contract Payment Plan"),
            "res_model": "palmate.contract.payment",
            "view_mode": "list,form",
            "domain": [("contract_id", "=", self.id)],
            "context": {"default_contract_id": self.id},
        }

    def action_create_all_invoices(self):
        self.ensure_one()
        for line in self.payment_line_ids.filtered(lambda payment: not payment.invoice_id):
            line.action_create_invoice()
        return self.action_view_invoices()

    def action_approve_discount(self):
        for record in self:
            record.discount_approved = True

    def action_view_commissions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Contract Commissions"),
            "res_model": "palmate.agent.commission",
            "view_mode": "list,form",
            "domain": [("contract_id", "=", self.id)],
            "context": {"default_contract_id": self.id, "default_agent_id": self.agent_id.id},
        }

    def action_view_maintenance_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Contract Maintenance Requests"),
            "res_model": "palmate.maintenance.request",
            "view_mode": "list,form",
            "domain": [("contract_id", "=", self.id)],
            "context": {
                "default_contract_id": self.id,
                "default_property_id": self.property_id.id,
                "default_tenant_id": self.customer_id.id,
            },
        }

    def action_view_invoices(self):
        self.ensure_one()
        invoice_ids = self.payment_line_ids.mapped("invoice_id").ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", invoice_ids), ("move_type", "=", "out_invoice")],
            "context": {"default_move_type": "out_invoice"},
        }

    def action_create_maintenance_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Maintenance Request"),
            "res_model": "palmate.maintenance.request",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_contract_id": self.id,
                "default_property_id": self.property_id.id,
                "default_tenant_id": self.customer_id.id,
            },
        }


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
    property_id = fields.Many2one(
        related = "contract_id.property_id",
        comodel_name = "palmate.property",
        string = "Property",
        store = True,
        readonly = True,
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
    agent_id = fields.Many2one(
        related = "contract_id.agent_id",
        comodel_name = "res.users",
        string = "Agent",
        store = True,
        readonly = True,
    )
    inquiry_id = fields.Many2one(
        related = "contract_id.inquiry_id",
        comodel_name = "palmate.property.inquiry",
        string = "Inquiry",
        store = True,
        readonly = True,
    )
    visit_id = fields.Many2one(
        related = "contract_id.visit_id",
        comodel_name = "palmate.property.visit",
        string = "Visit",
        store = True,
        readonly = True,
    )
    reservation_id = fields.Many2one(
        related = "contract_id.reservation_id",
        comodel_name = "palmate.property.reservation",
        string = "Reservation",
        store = True,
        readonly = True,
    )
    company_id = fields.Many2one(
        related = "contract_id.company_id",
        comodel_name = "res.company",
        string = "Company",
        store = True,
        readonly = True,
    )
    days_overdue = fields.Integer(
        string = "Days Overdue",
        compute = "_compute_payment_status",
        store = True,
    )
    invoice_id = fields.Many2one(
        "account.move",
        string = "Customer Invoice",
        copy = False,
        readonly = True,
    )
    invoice_state = fields.Selection(
        related = "invoice_id.state",
        string = "Invoice Status",
        store = True,
        readonly = True,
    )
    invoice_payment_state = fields.Selection(
        related = "invoice_id.payment_state",
        string = "Payment State",
        store = True,
        readonly = True,
    )

    @api.depends("paid", "due_date", "invoice_id.state", "invoice_id.payment_state")
    def _compute_payment_status(self):
        today = fields.Date.context_today(self)
        for record in self:
            invoice_paid = record.invoice_id and record.invoice_payment_state in ("paid", "in_payment")
            if record.paid or invoice_paid:
                record.payment_status = "paid"
                record.days_overdue = 0
            elif record.due_date and record.due_date < today:
                record.payment_status = "overdue"
                record.days_overdue = (today - record.due_date).days
            else:
                record.payment_status = "pending"
                record.days_overdue = 0

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            return self.action_view_invoice()
        income_account = self.env["account.account"].search([
            ("company_ids", "in", self.company_id.id),
            ("internal_group", "=", "income"),
        ], limit=1)
        line_vals = {
            "name": _("%s - %s") % (self.contract_id.name, self.name),
            "quantity": 1.0,
            "price_unit": self.amount,
        }
        if income_account:
            line_vals["account_id"] = income_account.id
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.customer_id.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_date_due": self.due_date or fields.Date.context_today(self),
            "invoice_origin": self.contract_id.name,
            "ref": self.name,
            "invoice_line_ids": [
                Command.create(line_vals),
            ],
        })
        self.invoice_id = invoice.id
        return self.action_view_invoice()

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return self.action_create_invoice()
        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Invoice"),
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }


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
    property_id = fields.Many2one(
        related = "contract_id.property_id",
        comodel_name = "palmate.property",
        string = "Property",
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
    inquiry_id = fields.Many2one(
        related = "contract_id.inquiry_id",
        comodel_name = "palmate.property.inquiry",
        string = "Inquiry",
        store = True,
        readonly = True,
    )
    visit_id = fields.Many2one(
        related = "contract_id.visit_id",
        comodel_name = "palmate.property.visit",
        string = "Visit",
        store = True,
        readonly = True,
    )
    reservation_id = fields.Many2one(
        related = "contract_id.reservation_id",
        comodel_name = "palmate.property.reservation",
        string = "Reservation",
        store = True,
        readonly = True,
    )
    contract_type = fields.Selection(
        related = "contract_id.contract_type",
        string = "Contract Type",
        store = True,
        readonly = True,
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
    company_id = fields.Many2one(
        related = "contract_id.company_id",
        comodel_name = "res.company",
        string = "Company",
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
    contract_id = fields.Many2one(
        "palmate.property.contract",
        string = "Contract",
        tracking = True,
    )
    tenant_id = fields.Many2one(
        "res.partner",
        string = "Tenant",
        tracking = True,
    )
    agent_id = fields.Many2one(
        related = "contract_id.agent_id",
        comodel_name = "res.users",
        string = "Contract Agent",
        store = True,
        readonly = True,
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
    due_date = fields.Date(
        string = "Target Resolution Date",
        tracking = True,
    )
    overdue = fields.Boolean(
        string = "Overdue",
        compute = "_compute_overdue",
    )
    maintenance_app_request_id = fields.Many2one(
        "maintenance.request",
        string = "Maintenance App Ticket",
        copy = False,
        tracking = True,
    )
    response_due_date = fields.Date(
        string = "Response Due Date",
        tracking = True,
    )
    response_overdue = fields.Boolean(
        string = "Response Overdue",
        compute = "_compute_overdue",
    )
    official_ticket_done = fields.Boolean(
        related = "maintenance_app_request_id.done",
        string = "Official Ticket Done",
        store = True,
        readonly = True,
    )

    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.overdue = bool(
                record.due_date and record.due_date < today and record.status != "done"
            )
            record.response_overdue = bool(
                record.response_due_date and record.response_due_date < today and record.status == "new"
            )

    @api.onchange("contract_id")
    def _onchange_contract_id(self):
        for record in self:
            if record.contract_id:
                record.property_id = record.contract_id.property_id
                record.tenant_id = record.contract_id.customer_id

    @api.constrains("contract_id", "property_id", "tenant_id")
    def _check_contract_alignment(self):
        for record in self:
            if record.contract_id:
                if record.property_id and record.property_id != record.contract_id.property_id:
                    raise ValidationError(_("The maintenance property must match the contract property."))
                if record.tenant_id and record.tenant_id != record.contract_id.customer_id:
                    raise ValidationError(_("The maintenance tenant must match the contract customer."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("palmate.maintenance.request") or "/"
            contract_id = vals.get("contract_id")
            if contract_id:
                contract = self.env["palmate.property.contract"].browse(contract_id)
                vals.setdefault("property_id", contract.property_id.id)
                vals.setdefault("tenant_id", contract.customer_id.id)
        return super().create(vals_list)

    def action_start(self):
        for record in self:
            record.status = "in_progress"

    def action_done(self):
        for record in self:
            record.status = "done"
            record.completion_date = fields.Date.context_today(record)

    def _prepare_maintenance_app_vals(self):
        self.ensure_one()
        priority_map = {"low": "1", "medium": "2", "high": "3"}
        technician = self.assigned_partner_id.user_ids[:1]
        team_domain = [("company_id", "=", self.company_id.id)]
        if self.issue_type:
            team = self.env["maintenance.team"].search(team_domain + [("name", "ilike", self.issue_type)], limit=1)
        else:
            team = self.env["maintenance.team"]
        if not team:
            team = self.env["maintenance.team"].search(team_domain, limit=1)
        if not team:
            team = self.env["maintenance.team"].search([], limit=1)
        description = _(
            "<p><strong>Property:</strong> %s</p>"
            "<p><strong>Tenant:</strong> %s</p>"
            "<p><strong>Issue Type:</strong> %s</p>"
            "<p>%s</p>"
        ) % (
            self.property_id.display_name or "",
            self.tenant_id.display_name or "",
            dict(self._fields["issue_type"].selection).get(self.issue_type, self.issue_type),
            self.description or "",
        )
        return {
            "name": self.name,
            "description": description,
            "request_date": self.reported_date or fields.Date.context_today(self),
            "schedule_date": self.due_date,
            "user_id": technician.id if technician else False,
            "priority": priority_map.get(self.priority, "2"),
            "maintenance_type": "corrective",
            "maintenance_team_id": team.id,
            "company_id": self.company_id.id,
        }

    def action_create_maintenance_app_request(self):
        self.ensure_one()
        if not self.maintenance_app_request_id:
            self.maintenance_app_request_id = self.env["maintenance.request"].create(
                self._prepare_maintenance_app_vals()
            )
        return self.action_view_maintenance_app_request()

    def action_view_maintenance_app_request(self):
        self.ensure_one()
        if not self.maintenance_app_request_id:
            return self.action_create_maintenance_app_request()
        return {
            "type": "ir.actions.act_window",
            "name": _("Maintenance App Ticket"),
            "res_model": "maintenance.request",
            "res_id": self.maintenance_app_request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_sync_official_ticket_status(self):
        for record in self.filtered("maintenance_app_request_id"):
            if record.maintenance_app_request_id.done:
                record.status = "done"
                if not record.completion_date:
                    record.completion_date = fields.Date.context_today(record)
            elif record.maintenance_app_request_id.schedule_date:
                record.status = "in_progress"
            else:
                record.status = "new"

    def write(self, vals):
        result = super().write(vals)
        tracked_fields = {
            "name",
            "description",
            "reported_date",
            "due_date",
            "assigned_partner_id",
            "priority",
            "issue_type",
        }
        if tracked_fields.intersection(vals):
            for record in self.filtered("maintenance_app_request_id"):
                record.maintenance_app_request_id.write(record._prepare_maintenance_app_vals())
        return result


class ResPartner(models.Model):
    _inherit = "res.partner"

    property_inquiry_count = fields.Integer(
        string = "Inquiry Count",
        compute = "_compute_real_estate_counts",
    )
    property_visit_count = fields.Integer(
        string = "Visit Count",
        compute = "_compute_real_estate_counts",
    )
    property_reservation_count = fields.Integer(
        string = "Reservation Count",
        compute = "_compute_real_estate_counts",
    )
    property_contract_count = fields.Integer(
        string = "Contract Count",
        compute = "_compute_real_estate_counts",
    )
    property_payment_count = fields.Integer(
        string = "Payment Count",
        compute = "_compute_real_estate_counts",
    )
    property_maintenance_count = fields.Integer(
        string = "Maintenance Count",
        compute = "_compute_real_estate_counts",
    )

    def _compute_real_estate_counts(self):
        inquiry_model = self.env["palmate.property.inquiry"]
        visit_model = self.env["palmate.property.visit"]
        reservation_model = self.env["palmate.property.reservation"]
        contract_model = self.env["palmate.property.contract"]
        payment_model = self.env["palmate.contract.payment"]
        maintenance_model = self.env["palmate.maintenance.request"]
        for partner in self:
            partner.property_inquiry_count = inquiry_model.search_count([("customer_id", "=", partner.id)])
            partner.property_visit_count = visit_model.search_count([("customer_id", "=", partner.id)])
            partner.property_reservation_count = reservation_model.search_count([("customer_id", "=", partner.id)])
            partner.property_contract_count = contract_model.search_count([("customer_id", "=", partner.id)])
            partner.property_payment_count = payment_model.search_count([("customer_id", "=", partner.id)])
            partner.property_maintenance_count = maintenance_model.search_count([("tenant_id", "=", partner.id)])

    def _real_estate_window_action(self, name, model, domain):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model,
            "view_mode": "list,form",
            "domain": domain,
            "target": "current",
        }

    def action_view_property_inquiries(self):
        self.ensure_one()
        return self._real_estate_window_action(_("Customer Inquiries"), "palmate.property.inquiry", [("customer_id", "=", self.id)])

    def action_view_property_visits(self):
        self.ensure_one()
        return self._real_estate_window_action(_("Customer Visits"), "palmate.property.visit", [("customer_id", "=", self.id)])

    def action_view_property_reservations(self):
        self.ensure_one()
        return self._real_estate_window_action(_("Customer Reservations"), "palmate.property.reservation", [("customer_id", "=", self.id)])

    def action_view_property_contracts(self):
        self.ensure_one()
        return self._real_estate_window_action(_("Customer Contracts"), "palmate.property.contract", [("customer_id", "=", self.id)])

    def action_view_property_payments(self):
        self.ensure_one()
        return self._real_estate_window_action(_("Customer Payments"), "palmate.contract.payment", [("customer_id", "=", self.id)])

    def action_view_property_maintenance(self):
        self.ensure_one()
        return self._real_estate_window_action(_("Customer Maintenance"), "palmate.maintenance.request", [("tenant_id", "=", self.id)])
