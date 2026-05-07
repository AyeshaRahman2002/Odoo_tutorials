from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import PalmateRealEstateTestCommon


@tagged("post_install", "-at_install")
class TestPalmateIntegrations(PalmateRealEstateTestCommon):
    def test_visit_creates_calendar_event_and_blocks_overlap(self):
        inquiry = self._create_inquiry()
        first_visit = self._create_visit(inquiry, visit_date="2026-05-10 10:00:00", visit_duration_hours=2.0)
        first_visit.action_create_calendar_event()

        self.assertTrue(first_visit.calendar_event_id)
        self.assertEqual(first_visit.calendar_event_id.res_model, "palmate.property.visit")
        self.assertEqual(first_visit.calendar_event_id.res_id, first_visit.id)

        with self.assertRaises(ValidationError):
            self._create_visit(inquiry, visit_date="2026-05-10 11:00:00", visit_duration_hours=1.0)

    def test_invoice_creation_and_contract_payment_progress(self):
        inquiry = self._create_inquiry()
        contract = self._create_contract(inquiry)
        payment_line = self.env["palmate.contract.payment"].create({
            "name": "Installment 1",
            "contract_id": contract.id,
            "due_date": "2026-05-15",
            "amount": 80000.0,
        })

        payment_line.action_create_invoice()
        self.assertTrue(payment_line.invoice_id)
        self.assertEqual(payment_line.invoice_id.move_type, "out_invoice")
        self.assertEqual(payment_line.invoice_state, "draft")

        payment_line.paid = True
        contract.invalidate_recordset(["paid_amount", "payment_progress"])
        self.assertEqual(contract.paid_amount, 80000.0)
        self.assertGreater(contract.payment_progress, 0.0)

    def test_maintenance_official_ticket_sync(self):
        inquiry = self._create_inquiry()
        contract = self._create_contract(inquiry)
        maintenance = self.env["palmate.maintenance.request"].create({
            "name": "/",
            "contract_id": contract.id,
            "property_id": contract.property_id.id,
            "tenant_id": contract.customer_id.id,
            "issue_type": "plumbing",
            "priority": "high",
            "response_due_date": "2026-05-11",
            "due_date": "2026-05-12",
            "currency_id": self.currency.id,
            "company_id": self.company.id,
        })

        maintenance.action_create_maintenance_app_request()
        self.assertTrue(maintenance.maintenance_app_request_id)
        self.assertEqual(maintenance.maintenance_app_request_id.maintenance_type, "corrective")

        maintenance.maintenance_app_request_id.schedule_date = "2026-05-11 12:00:00"
        maintenance.action_sync_official_ticket_status()
        self.assertEqual(maintenance.status, "in_progress")

    def test_inquiry_crm_sync(self):
        inquiry = self._create_inquiry()
        self.assertTrue(inquiry.crm_lead_id)
        self.assertEqual(inquiry.crm_lead_id.type, "opportunity")

        inquiry.action_qualify()
        self.assertEqual(inquiry.crm_lead_id.probability, inquiry.probability)

        inquiry.action_mark_won()
        self.assertEqual(inquiry.crm_lead_id.probability, 100)
