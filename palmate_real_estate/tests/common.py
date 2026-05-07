from odoo import Command
from odoo.tests.common import TransactionCase


class PalmateRealEstateTestCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id

        cls.receivable_account = cls.env["account.account"].search([
            ("company_ids", "in", cls.company.id),
            ("account_type", "=", "asset_receivable"),
        ], limit=1)
        if not cls.receivable_account:
            cls.receivable_account = cls.env["account.account"].create({
                "name": "Palmate Test Receivable",
                "code": "PTRCV",
                "account_type": "asset_receivable",
                "company_ids": [Command.set([cls.company.id])],
            })

        cls.income_account = cls.env["account.account"].search([
            ("company_ids", "in", cls.company.id),
            ("account_type", "=", "income"),
        ], limit=1)
        if not cls.income_account:
            cls.income_account = cls.env["account.account"].create({
                "name": "Palmate Test Income",
                "code": "PTINC",
                "account_type": "income",
                "company_ids": [Command.set([cls.company.id])],
            })

        cls.sale_journal = cls.env["account.journal"].search([
            ("company_id", "=", cls.company.id),
            ("type", "=", "sale"),
        ], limit=1)
        if not cls.sale_journal:
            cls.sale_journal = cls.env["account.journal"].create({
                "name": "Palmate Test Sales",
                "code": "PTSJ",
                "type": "sale",
                "company_id": cls.company.id,
            })

        cls.customer = cls.env["res.partner"].create({
            "name": "Palmate Test Customer",
            "email": "customer@example.com",
            "property_account_receivable_id": cls.receivable_account.id,
        })
        cls.owner = cls.env["res.partner"].create({"name": "Palmate Test Owner"})

        cls.property = cls.env["palmate.property"].create({
            "name": "Palmate Test Villa",
            "property_type": "villa",
            "location": "Riyadh",
            "owner_id": cls.owner.id,
            "agent_id": cls.env.user.id,
            "status": "available",
            "price": 450000.0,
            "currency_id": cls.currency.id,
            "company_id": cls.company.id,
        })

    def _create_inquiry(self, **extra_vals):
        vals = {
            "name": "/",
            "property_id": self.property.id,
            "customer_id": self.customer.id,
            "preferred_location": "Riyadh",
            "budget": 400000.0,
            "property_type": "villa",
            "agent_id": self.env.user.id,
            "source": "website",
            "currency_id": self.currency.id,
            "company_id": self.company.id,
        }
        vals.update(extra_vals)
        return self.env["palmate.property.inquiry"].create(vals)

    def _create_visit(self, inquiry, **extra_vals):
        vals = {
            "name": "/",
            "inquiry_id": inquiry.id,
            "property_id": inquiry.property_id.id,
            "customer_id": inquiry.customer_id.id,
            "agent_id": inquiry.agent_id.id,
            "visit_date": "2026-05-10 10:00:00",
            "visit_duration_hours": 1.0,
            "currency_id": self.currency.id,
            "company_id": self.company.id,
        }
        vals.update(extra_vals)
        return self.env["palmate.property.visit"].create(vals)

    def _create_reservation(self, inquiry, visit=None, **extra_vals):
        vals = {
            "name": "/",
            "inquiry_id": inquiry.id,
            "visit_id": visit.id if visit else False,
            "property_id": inquiry.property_id.id,
            "customer_id": inquiry.customer_id.id,
            "agent_id": inquiry.agent_id.id,
            "reservation_date": "2026-05-10",
            "expiry_date": "2026-05-20",
            "deposit_amount": 25000.0,
            "currency_id": self.currency.id,
            "company_id": self.company.id,
        }
        vals.update(extra_vals)
        return self.env["palmate.property.reservation"].create(vals)

    def _create_contract(self, inquiry, reservation=None, visit=None, **extra_vals):
        vals = {
            "name": "/",
            "inquiry_id": inquiry.id,
            "reservation_id": reservation.id if reservation else False,
            "visit_id": visit.id if visit else False,
            "property_id": inquiry.property_id.id,
            "customer_id": inquiry.customer_id.id,
            "agent_id": inquiry.agent_id.id,
            "contract_type": "sale",
            "start_date": "2026-05-12",
            "amount": 450000.0,
            "currency_id": self.currency.id,
            "company_id": self.company.id,
        }
        vals.update(extra_vals)
        return self.env["palmate.property.contract"].create(vals)
