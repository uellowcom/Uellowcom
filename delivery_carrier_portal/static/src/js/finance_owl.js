/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

/**
 * Delivery Finance & Settlements Center.
 * Live, per-carrier money view:
 *  - cash the carrier is holding (collected COD not yet remitted)
 *  - carrier cost Uellow owes (delivery fees / commission)
 *  - net balance per carrier (who owes whom)
 *  - one-click "Create Settlement" → draft delivery.cash.remittance
 *  - settlements ledger with state badges (click to open the record)
 */
export class DeliveryFinance extends Component {
    static template = "delivery_carrier_portal.Finance";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");

        this._timer = null;
        this.state = useState({
            loading: true,
            busy: false,
            carrier_id: 0,
            carriers: [],
            settlements: [],
            totals: {},
            allCarriers: [],   // for the filter dropdown
            timestamp: "—",
        });

        onMounted(async () => {
            await this.loadCarrierList();
            await this.loadData();
            this._timer = setInterval(() => this.loadData(), 3 * 60 * 1000);
        });
        onWillUnmount(() => {
            if (this._timer) {
                clearInterval(this._timer);
            }
        });
    }

    async loadCarrierList() {
        try {
            this.state.allCarriers = await this.orm.searchRead(
                "delivery.carrier.company",
                [["active", "=", true]],
                ["id", "name"]
            );
        } catch (e) {
            console.error("loadCarrierList error:", e);
        }
    }

    async loadData() {
        this.state.loading = true;
        try {
            const result = await rpc("/delivery-portal/finance-data", {
                carrier_id: this.state.carrier_id,
            });
            if (result) {
                this.state.carriers = result.carriers || [];
                this.state.settlements = result.settlements || [];
                this.state.totals = result.totals || {};
                this.state.timestamp = new Date().toLocaleTimeString();
            }
        } catch (e) {
            console.error("Finance loadData error:", e);
        }
        this.state.loading = false;
    }

    onCarrierChange(ev) {
        this.state.carrier_id = parseInt(ev.target.value) || 0;
        this.loadData();
    }

    async createSettlement(carrier) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const res = await rpc("/delivery-portal/finance-create-settlement", {
                carrier_id: carrier.id,
            });
            if (res && res.remittance_id) {
                this.notification.add(
                    `تم إنشاء التسوية ${res.name} بعدد ${res.count} طلب`,
                    { type: "success" }
                );
                this.openSettlement(res.remittance_id);
            } else if (res && res.error === "nothing_to_settle") {
                this.notification.add(
                    "لا توجد طلبات مستحقة للتسوية لدى هذه الشركة",
                    { type: "warning" }
                );
            } else {
                this.notification.add("تعذّر إنشاء التسوية", { type: "danger" });
            }
        } catch (e) {
            console.error("createSettlement error:", e);
            this.notification.add("خطأ أثناء إنشاء التسوية", { type: "danger" });
        }
        this.state.busy = false;
        this.loadData();
    }

    openSettlement(remId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Settlement",
            res_model: "delivery.cash.remittance",
            res_id: remId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllSettlements() {
        this.action.doAction("delivery_carrier_portal.action_delivery_cash_remittance");
    }

    // Outstanding orders held at a carrier (delivered COD not yet remitted)
    openCarrierOrders(carrier) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `الكاش المحتجز — ${carrier.name}`,
            res_model: "sale.order",
            view_mode: "list,form",
            domain: [
                ["delivery_carrier_company_id", "=", carrier.id],
                ["payment_method_type", "=", "cash"],
                ["delivery_status", "=", "delivered"],
                ["cash_collection_status", "in", ["pending", "collected"]],
            ],
            target: "current",
        });
    }

    fmt(n) {
        return parseFloat(n || 0).toFixed(3);
    }

    netClass(n) {
        const v = parseFloat(n || 0);
        if (v > 0.0005) return "db-owl-tag-green";
        if (v < -0.0005) return "db-owl-tag-red";
        return "db-owl-tag-blue";
    }

    stateClass(s) {
        if (s === "remitted") return "db-owl-tag-green";
        if (s === "rejected") return "db-owl-tag-red";
        if (s === "partial") return "db-owl-tag-yellow";
        if (s === "pending") return "db-owl-tag-yellow";
        return "db-owl-tag-blue";
    }

    stateLabel(s) {
        const map = {
            draft: "مسودة",
            pending: "بانتظار الموافقة",
            partial: "جزئية",
            remitted: "مُسوّاة",
            rejected: "مرفوضة",
        };
        return map[s] || s;
    }
}

registry.category("actions").add(
    "delivery_carrier_portal.finance",
    DeliveryFinance
);
