/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

function formatDate(date) {
    return date.toISOString().slice(0, 10);
}

function windowAction(name, resModel, domain = [], context = {}) {
    return {
        type: "ir.actions.act_window",
        name,
        res_model: resModel,
        views: [
            [false, "list"],
            [false, "form"],
        ],
        target: "current",
        domain,
        context,
    };
}

class PalmateDashboard extends Component {
    static template = "palmate_real_estate.Dashboard";
    static components = {
        CheckBox,
        Dropdown,
        DropdownItem,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            error: false,
            monthLabel: "",
            summary: [],
            sections: [],
            sectionFilter: "all",
            actionableOnly: false,
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        this.state.loading = true;
        this.state.error = false;
        try {
            const now = new Date();
            const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
            const nextMonthStart = new Date(now.getFullYear(), now.getMonth() + 1, 1);
            const today = formatDate(now);
            const monthStartStr = formatDate(monthStart);
            const nextMonthStartStr = formatDate(nextMonthStart);

            const [
                inquiriesThisMonth,
                wonInquiriesThisMonth,
                overdueFollowups,
                crmPipelineCount,
                crmPipelineLeads,
                openReservations,
                convertedReservations,
                totalReservations,
                signedContracts,
                activeContracts,
                overduePayments,
                overdueInvoices,
                monthlyInvoices,
                unpaidCommissions,
                openMaintenance,
                officialOpenMaintenance,
                currentMonthInquiries,
            ] = await Promise.all([
                this.orm.searchCount("palmate.property.inquiry", [
                    ["create_date", ">=", `${monthStartStr} 00:00:00`],
                    ["create_date", "<", `${nextMonthStartStr} 00:00:00`],
                ]),
                this.orm.searchCount("palmate.property.inquiry", [
                    ["create_date", ">=", `${monthStartStr} 00:00:00`],
                    ["create_date", "<", `${nextMonthStartStr} 00:00:00`],
                    ["status", "=", "won"],
                ]),
                this.orm.searchCount("palmate.property.inquiry", [["overdue_followup", "=", true]]),
                this.orm.searchCount("crm.lead", [["type", "=", "opportunity"], ["active", "=", true], ["probability", "<", 100]]),
                this.orm.searchRead(
                    "crm.lead",
                    [["type", "=", "opportunity"], ["active", "=", true], ["probability", "<", 100]],
                    ["expected_revenue"]
                ),
                this.orm.searchCount("palmate.property.reservation", [["status", "=", "active"]]),
                this.orm.searchCount("palmate.property.reservation", [["status", "=", "converted"]]),
                this.orm.searchCount("palmate.property.reservation", []),
                this.orm.searchCount("palmate.property.contract", [["status", "=", "signed"]]),
                this.orm.searchCount("palmate.property.contract", [["status", "=", "active"]]),
                this.orm.searchCount("palmate.contract.payment", [["payment_status", "=", "overdue"]]),
                this.orm.searchCount("account.move", [
                    ["move_type", "=", "out_invoice"],
                    ["state", "=", "posted"],
                    ["invoice_date_due", "<", today],
                    ["payment_state", "not in", ["paid", "reversed"]],
                ]),
                this.orm.searchRead(
                    "account.move",
                    [
                        ["move_type", "=", "out_invoice"],
                        ["state", "=", "posted"],
                        ["invoice_date", ">=", monthStartStr],
                        ["invoice_date", "<", nextMonthStartStr],
                    ],
                    ["amount_total", "payment_state"]
                ),
                this.orm.searchCount("palmate.agent.commission", [["status", "!=", "paid"]]),
                this.orm.searchCount("palmate.maintenance.request", [["status", "!=", "done"]]),
                this.orm.searchCount("maintenance.request", [["archive", "=", false], ["done", "=", false]]),
                this.orm.searchRead(
                    "palmate.property.inquiry",
                    [
                        ["create_date", ">=", `${monthStartStr} 00:00:00`],
                        ["create_date", "<", `${nextMonthStartStr} 00:00:00`],
                    ],
                    ["agent_id"]
                ),
            ]);

            const conversionRate = inquiriesThisMonth
                ? `${Math.round((wonInquiriesThisMonth / inquiriesThisMonth) * 100)}%`
                : "0%";
            const pipelineValue = crmPipelineLeads.reduce((sum, lead) => sum + (lead.expected_revenue || 0), 0);
            const monthlyRevenue = monthlyInvoices
                .filter((invoice) => ["paid", "in_payment"].includes(invoice.payment_state))
                .reduce((sum, invoice) => sum + (invoice.amount_total || 0), 0);
            const inquiriesByAgent = currentMonthInquiries.reduce((acc, inquiry) => {
                const agent = inquiry.agent_id;
                if (agent && agent[0]) {
                    acc[agent[1]] = (acc[agent[1]] || 0) + 1;
                }
                return acc;
            }, {});
            const topAgentEntry = Object.entries(inquiriesByAgent).sort((a, b) => b[1] - a[1])[0];

            this.state.monthLabel = now.toLocaleString(undefined, { month: "long", year: "numeric" });
            this.state.summary = [
                { label: "Conversion This Month", value: conversionRate, hint: `${wonInquiriesThisMonth} won from ${inquiriesThisMonth} inquiries` },
                { label: "Pipeline Value", value: pipelineValue.toLocaleString(), hint: `${crmPipelineCount} active CRM opportunities` },
                { label: "Collected Revenue", value: monthlyRevenue.toLocaleString(), hint: "Paid or in-payment invoices this month" },
                { label: "Top Agent", value: topAgentEntry ? topAgentEntry[0] : "N/A", hint: topAgentEntry ? `${topAgentEntry[1]} inquiries this month` : "No inquiries yet" },
            ];
            this.state.sections = [
                {
                    id: "pipeline",
                    title: "Pipeline",
                    description: "Top-of-funnel and deal progression metrics. Each card opens the exact filtered records used for that number.",
                    cards: [
                        {
                            id: "inquiries",
                            title: "Inquiries This Month",
                            value: inquiriesThisMonth,
                            tone: "primary",
                            actionable: true,
                            subtitle: "Created this month",
                            action: windowAction(
                                "Inquiries This Month",
                                "palmate.property.inquiry",
                                [
                                    ["create_date", ">=", `${monthStartStr} 00:00:00`],
                                    ["create_date", "<", `${nextMonthStartStr} 00:00:00`],
                                ],
                            ),
                        },
                        {
                            id: "overdue_followups",
                            title: "Overdue Follow-ups",
                            value: overdueFollowups,
                            tone: "accent",
                            actionable: true,
                            subtitle: "Inquiry follow-up date is overdue",
                            action: windowAction(
                                "Overdue Follow-ups",
                                "palmate.property.inquiry",
                                [["overdue_followup", "=", true]],
                            ),
                        },
                        {
                            id: "crm_pipeline",
                            title: "CRM Opportunities",
                            value: crmPipelineCount,
                            tone: "dark",
                            actionable: true,
                            subtitle: "Live CRM pipeline items",
                            action: windowAction(
                                "CRM Opportunities",
                                "crm.lead",
                                [["type", "=", "opportunity"], ["active", "=", true], ["probability", "<", 100]],
                            ),
                        },
                        {
                            id: "open_reservations",
                            title: "Open Reservations",
                            value: openReservations,
                            tone: "secondary",
                            actionable: true,
                            subtitle: "Reservation status = Active",
                            action: windowAction(
                                "Open Reservations",
                                "palmate.property.reservation",
                                [["status", "=", "active"]],
                            ),
                        },
                        {
                            id: "converted_reservations",
                            title: "Converted Reservations",
                            value: convertedReservations,
                            tone: "neutral",
                            actionable: false,
                            subtitle: "Reservation status = Converted",
                            action: windowAction(
                                "Converted Reservations",
                                "palmate.property.reservation",
                                [["status", "=", "converted"]],
                            ),
                        },
                        {
                            id: "signed_contracts",
                            title: "Signed Contracts",
                            value: signedContracts,
                            tone: "dark",
                            actionable: true,
                            subtitle: "Signed but not active yet",
                            action: windowAction(
                                "Signed Contracts",
                                "palmate.property.contract",
                                [["status", "=", "signed"]],
                            ),
                        },
                        {
                            id: "active_contracts",
                            title: "Active Contracts",
                            value: activeContracts,
                            tone: "success",
                            actionable: true,
                            subtitle: "Contract status = Active",
                            action: windowAction(
                                "Active Contracts",
                                "palmate.property.contract",
                                [["status", "=", "active"]],
                            ),
                        },
                    ],
                },
                {
                    id: "operations",
                    title: "Operations",
                    description: "Execution queues for finance and property management. These cards focus on work that still needs action.",
                    cards: [
                        {
                            id: "overdue_invoices",
                            title: "Overdue Invoices",
                            value: overdueInvoices,
                            tone: "danger",
                            actionable: true,
                            subtitle: "Posted customer invoices past due",
                            action: windowAction(
                                "Overdue Invoices",
                                "account.move",
                                [
                                    ["move_type", "=", "out_invoice"],
                                    ["state", "=", "posted"],
                                    ["invoice_date_due", "<", today],
                                    ["payment_state", "not in", ["paid", "reversed"]],
                                ],
                            ),
                        },
                        {
                            id: "overdue_payments",
                            title: "Overdue Payment Lines",
                            value: overduePayments,
                            tone: "accent",
                            actionable: true,
                            subtitle: "Custom payment lines still overdue",
                            action: windowAction(
                                "Overdue Payments",
                                "palmate.contract.payment",
                                [["payment_status", "=", "overdue"]],
                            ),
                        },
                        {
                            id: "unpaid_commissions",
                            title: "Unpaid Commissions",
                            value: unpaidCommissions,
                            tone: "warning",
                            actionable: true,
                            subtitle: "Commission status is not Paid",
                            action: windowAction(
                                "Unpaid Commissions",
                                "palmate.agent.commission",
                                [["status", "!=", "paid"]],
                            ),
                        },
                        {
                            id: "open_maintenance",
                            title: "Official Maintenance Queue",
                            value: officialOpenMaintenance,
                            tone: "secondary",
                            actionable: true,
                            subtitle: "Open tickets in Odoo Maintenance",
                            action: windowAction(
                                "Official Maintenance Requests",
                                "maintenance.request",
                                [["archive", "=", false], ["done", "=", false]],
                            ),
                        },
                        {
                            id: "custom_maintenance",
                            title: "Custom Maintenance",
                            value: openMaintenance,
                            tone: "primary",
                            actionable: true,
                            subtitle: "Open requests in the real-estate flow",
                            action: windowAction("Maintenance", "palmate.maintenance.request", [["status", "!=", "done"]]),
                        },
                    ],
                },
            ];
            this.today = today;
        } catch (error) {
            this.state.error = true;
            this.notification.add("Unable to load the dashboard data.", {
                type: "danger",
            });
            throw error;
        } finally {
            this.state.loading = false;
        }
    }

    openCard(ev) {
        const { cardId } = ev.currentTarget.dataset;
        const card = this.state.sections
            .flatMap((section) => section.cards)
            .find((item) => item.id === cardId);
        if (card) {
            this.action.doAction(card.action);
        }
    }

    openQuickAction(ev) {
        const { quickAction } = ev.currentTarget.dataset;
        this.doQuickAction(quickAction);
    }

    doQuickAction(quickAction) {
        const actions = {
            pipeline: windowAction("CRM Pipeline", "crm.lead", [["type", "=", "opportunity"]], { group_by: "stage_id" }),
            visits: windowAction("Upcoming Visits", "palmate.property.visit", [["visit_date", ">=", `${this.today} 00:00:00`]]),
            payments: windowAction("Customer Invoices", "account.move", [["move_type", "=", "out_invoice"]], { group_by: "state" }),
            maintenance: windowAction("Maintenance Queue", "maintenance.request", [["archive", "=", false]], { group_by: "stage_id" }),
        };
        if (actions[quickAction]) {
            this.action.doAction(actions[quickAction]);
        }
    }

    setSectionFilter(filter) {
        this.state.sectionFilter = filter;
    }

    toggleActionableOnly(checked) {
        this.state.actionableOnly = checked;
    }

    get currentSectionLabel() {
        const labels = {
            all: "All Sections",
            pipeline: "Pipeline Only",
            operations: "Operations Only",
        };
        return labels[this.state.sectionFilter] || labels.all;
    }

    get visibleSections() {
        const sections = this.state.sectionFilter === "all"
            ? this.state.sections
            : this.state.sections.filter((section) => section.id === this.state.sectionFilter);

        return sections
            .map((section) => ({
                ...section,
                cards: this.state.actionableOnly
                    ? section.cards.filter((card) => card.actionable !== false)
                    : section.cards,
            }))
            .filter((section) => section.cards.length);
    }
}

registry.category("actions").add("palmate_real_estate.dashboard", PalmateDashboard);
