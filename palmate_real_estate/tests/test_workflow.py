from datetime import timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import PalmateRealEstateTestCommon


@tagged("post_install", "-at_install")
class TestPalmateWorkflow(PalmateRealEstateTestCommon):
    def test_full_workflow_and_property_sync(self):
        inquiry = self._create_inquiry()
        self.assertTrue(inquiry.crm_lead_id)

        visit = self._create_visit(inquiry)
        reservation = self._create_reservation(inquiry, visit=visit)
        self.property.invalidate_recordset(["status"])
        self.assertEqual(self.property.status, "reserved")

        contract = self._create_contract(inquiry, reservation=reservation, visit=visit)
        contract.payment_line_ids = [(0, 0, {
            "name": "Booking Fee",
            "due_date": "2026-05-12",
            "amount": 60000.0,
        })]

        contract.action_sign()
        self.assertEqual(contract.status, "signed")

        with self.assertRaises(ValidationError):
            contract.action_activate()

        contract.payment_line_ids[0].paid = True
        contract.action_activate()

        self.assertEqual(contract.status, "active")
        self.assertEqual(inquiry.status, "won")
        self.assertEqual(reservation.status, "converted")
        self.property.invalidate_recordset(["status"])
        self.assertEqual(self.property.status, "sold")

    def test_contract_discount_requires_approval(self):
        inquiry = self._create_inquiry()
        contract = self._create_contract(inquiry, discount_amount=10000.0)

        with self.assertRaises(ValidationError):
            contract.action_sign()

        contract.action_approve_discount()
        contract.action_sign()
        self.assertEqual(contract.status, "signed")

    def test_reservation_extension_flow(self):
        inquiry = self._create_inquiry()
        reservation = self._create_reservation(inquiry, extension_days=5)

        old_expiry = reservation.expiry_date
        reservation.action_request_extension()
        self.assertTrue(reservation.extension_requested)

        reservation.action_approve_extension()
        self.assertFalse(reservation.extension_requested)
        self.assertTrue(reservation.extension_approved)
        self.assertEqual(reservation.expiry_date, old_expiry + timedelta(days=5))
