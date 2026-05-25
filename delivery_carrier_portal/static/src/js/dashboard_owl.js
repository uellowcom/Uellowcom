/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DeliveryDashboard extends Component {
    static template = "delivery_carrier_portal.Dashboard";
    static props = {};

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            period: "30",
            carrier_id: 0,
            carriers: [],
            kpi: {},
            daily_trend: [],
            carriers_data: [],
            drivers: [],
            recent_orders: [],
            alerts: [],
            timestamp: "—",
        });

        onMounted(async () => {
            await this.loadCarriers();
            await this.loadData();
            setInterval(() => this.loadData(), 3 * 60 * 1000);
        });
    }

    async loadCarriers() {
        try {
            const carriers = await this.orm.searchRead(
                "delivery.carrier.company",
                [["active", "=", true]],
                ["id", "name"]
            );
            this.state.carriers = carriers;
        } catch (e) {
            console.error("loadCarriers error:", e);
        }
    }

    async loadData() {
        this.state.loading = true;
        try {
            const result = await this.rpc("/delivery-portal/dashboard-data", {
                period: this.state.period,
                carrier_id: this.state.carrier_id,
            });
            if (result) {
                this.state.kpi           = result.kpi || {};
                this.state.daily_trend   = result.daily_trend || [];
                this.state.carriers_data = result.carriers || [];
                this.state.drivers       = result.drivers || [];
                this.state.recent_orders = result.recent_orders || [];
                this.state.alerts        = result.alerts || [];
                this.state.timestamp     = new Date().toLocaleTimeString();
            }
        } catch (e) {
            console.error("Dashboard loadData error:", e);
        }
        this.state.loading = false;
    }

    onPeriodChange(ev) {
        this.state.period = ev.target.value;
        this.loadData();
    }

    onCarrierChange(ev) {
        this.state.carrier_id = parseInt(ev.target.value) || 0;
        this.loadData();
    }

    openOrders(status) {
        const domain = status
            ? [["delivery_status", "=", status]]
            : [["delivery_carrier_company_id", "!=", false]];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Delivery Orders",
            res_model: "sale.order",
            view_mode: "list,form",
            domain: domain,
        });
    }

    openOrder(orderId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Order",
            res_model: "sale.order",
            res_id: orderId,
            view_mode: "form",
        });
    }

    fmt(n) {
        return parseFloat(n || 0).toFixed(3);
    }

    barHeight(d, trend) {
        const maxVal = Math.max(...trend.map(x => x.total || 1), 1);
        return Math.round((d.total / maxVal) * 120) || 2;
    }

    failHeight(d, trend) {
        const maxVal = Math.max(...trend.map(x => x.total || 1), 1);
        return Math.round((d.failed / maxVal) * 120) || 0;
    }

    getStatusClass(status) {
        if (status === "delivered") return "db-owl-tag-green";
        if (status === "failed" || status === "failed_returned") return "db-owl-tag-red";
        if (status === "out_for_delivery") return "db-owl-tag-yellow";
        return "db-owl-tag-blue";
    }

    getCarrierColor(rate) {
        if (rate >= 80) return "#16a34a";
        if (rate >= 70) return "#d97706";
        return "#dc2626";
    }
}

registry.category("actions").add(
    "delivery_carrier_portal.dashboard",
    DeliveryDashboard
);
