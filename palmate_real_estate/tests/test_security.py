from odoo.tests.common import new_test_user, tagged

from .common import PalmateRealEstateTestCommon


@tagged("post_install", "-at_install")
class TestPalmateSecurity(PalmateRealEstateTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent_a = new_test_user(
            cls.env,
            login="palmate_agent_a",
            groups="palmate_real_estate.group_palmate_real_estate_agent",
        )
        cls.agent_b = new_test_user(
            cls.env,
            login="palmate_agent_b",
            groups="palmate_real_estate.group_palmate_real_estate_agent",
        )
        cls.manager = new_test_user(
            cls.env,
            login="palmate_manager",
            groups="palmate_real_estate.group_palmate_real_estate_manager",
        )
        cls.finance = new_test_user(
            cls.env,
            login="palmate_finance",
            groups="palmate_real_estate.group_palmate_real_estate_finance",
        )
        cls.maintenance_user = new_test_user(PalmateRealEstateTestCommon
            cls.env,
            login="palmate_maintenance",
            groups="palmate_real_estate.group_palmate_real_estate_maintenance",
        )

        cls.property_a = cls.env["palmate.property"].create({
            "name": "Agent A Property",
            "property_type": "apartment",
            "location": "Jeddah",
            "agent_id": cls.agent_a.id,
            "status": "available",
            "price": 100000.0,
            "currency_id": cls.currency.id,
            "company_id": cls.company.id,
        })
        cls.property_b = cls.env["palmate.property"].create({
            "name": "Agent B Property",
            "property_type": "villa",
            "location": "Riyadh",
            "agent_id": cls.agent_b.id,
            "status": "available",
            "price": 200000.0,
            "currency_id": cls.currency.id,
            "company_id": cls.company.id,
        })

        cls.inquiry_a = cls.env["palmate.property.inquiry"].create({
            "name": "/",
            "property_id": cls.property_a.id,
            "customer_id": cls.customer.id,
            "agent_id": cls.agent_a.id,
            "budget": 90000.0,
            "currency_id": cls.currency.id,
            "company_id": cls.company.id,
        })
        cls.inquiry_b = cls.env["palmate.property.inquiry"].create({
            "name": "/",
            "property_id": cls.property_b.id,
            "customer_id": cls.customer.id,
            "agent_id": cls.agent_b.id,
            "budget": 180000.0,
            "currency_id": cls.currency.id,
            "company_id": cls.company.id,
        })

        cls.contract_a = cls.env["palmate.property.contract"].create({
            "name": "/",
            "property_id": cls.property_a.id,
            "customer_id": cls.customer.id,
            "agent_id": cls.agent_a.id,
            "contract_type": "sale",
            "start_date": "2026-05-12",
            "amount": 100000.0,
            "currency_id": cls.currency.id,
            "company_id": cls.company.id,
        })
        cls.payment_a = cls.env["palmate.contract.payment"].create({
            "name": "Finance Line",
            "contract_id": cls.contract_a.id,
            "due_date": "2026-05-20",
            "amount": 20000.0,
        })
        cls.commission_a = cls.env["palmate.agent.commission"].create({
            "agent_id": cls.agent_a.id,
            "contract_id": cls.contract_a.id,
            "commission_percent": 5.0,
        })
        cls.maintenance_a = cls.env["palmate.maintenance.request"].create({
            "name": "/",
            "contract_id": cls.contract_a.id,
            "property_id": cls.property_a.id,
            "tenant_id": cls.customer.id,
            "issue_type": "other",
            "currency_id": cls.currency.id,
            "company_id": cls.company.id,
        })

    def test_agent_only_sees_own_records(self):
        properties = self.env["palmate.property"].with_user(self.agent_a).search([])
        inquiries = self.env["palmate.property.inquiry"].with_user(self.agent_a).search([])
        self.assertIn(self.property_a, properties)
        self.assertNotIn(self.property_b, properties)
        self.assertIn(self.inquiry_a, inquiries)
        self.assertNotIn(self.inquiry_b, inquiries)

    def test_manager_sees_all_records(self):
        properties = self.env["palmate.property"].with_user(self.manager).search([])
        inquiries = self.env["palmate.property.inquiry"].with_user(self.manager).search([])
        self.assertIn(self.property_a, properties)
        self.assertIn(self.property_b, properties)
        self.assertIn(self.inquiry_a, inquiries)
        self.assertIn(self.inquiry_b, inquiries)

    def test_finance_and_maintenance_roles_can_access_their_domains(self):
        finance_contracts = self.env["palmate.property.contract"].with_user(self.finance).search([])
        finance_payments = self.env["palmate.contract.payment"].with_user(self.finance).search([])
        finance_commissions = self.env["palmate.agent.commission"].with_user(self.finance).search([])
        maintenance_requests = self.env["palmate.maintenance.request"].with_user(self.maintenance_user).search([])

        self.assertIn(self.contract_a, finance_contracts)
        self.assertIn(self.payment_a, finance_payments)
        self.assertIn(self.commission_a, finance_commissions)
        self.assertIn(self.maintenance_a, maintenance_requests)
