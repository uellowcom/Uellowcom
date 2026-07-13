/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";

export class DeliveryDashboard extends Component {
    static template = "delivery_carrier_portal.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        // canvas refs for the Chart.js charts
        this.trendCanvas   = useRef("trendCanvas");
        this.statusCanvas  = useRef("statusCanvas");
        this.carrierCanvas = useRef("carrierCanvas");

        // live Chart instances (destroyed/recreated on each refresh)
        this._charts = {};
        this._timer = null;
        this._chartLibReady = false;

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
            try {
                await loadJS("/web/static/lib/Chart/Chart.js");
                this._chartLibReady = typeof window.Chart !== "undefined";
            } catch (e) {
                console.error("Chart.js load failed:", e);
            }
            await this.loadCarriers();
            await this.loadData();
            this._timer = setInterval(() => this.loadData(), 3 * 60 * 1000);
        });

        onWillUnmount(() => {
            if (this._timer) {
                clearInterval(this._timer);
            }
            this._destroyCharts();
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
            const result = await rpc("/delivery-portal/dashboard-data", {
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
        // render charts after the DOM settles (canvas refs ready)
        setTimeout(() => this._renderCharts(), 50);
    }

    // ─────────────────────────────── Charts ───────────────────────────────
    _destroyCharts() {
        for (const k of Object.keys(this._charts)) {
            try { this._charts[k].destroy(); } catch (e) { /* noop */ }
        }
        this._charts = {};
    }

    _renderCharts() {
        if (!this._chartLibReady || typeof window.Chart === "undefined") {
            return;
        }
        this._destroyCharts();
        const Chart = window.Chart;
        Chart.defaults.font.family =
            "system-ui, -apple-system, 'Segoe UI', Tahoma, sans-serif";

        // 1) Daily trend — last 14 days (grouped bars: delivered vs failed + total line)
        if (this.trendCanvas.el && this.state.daily_trend.length) {
            const labels = this.state.daily_trend.map((d) =>
                d.date ? d.date.slice(5) : ""
            );
            this._charts.trend = new Chart(this.trendCanvas.el, {
                type: "bar",
                data: {
                    labels,
                    datasets: [
                        {
                            label: "تم التوصيل / Delivered",
                            data: this.state.daily_trend.map((d) => d.delivered || 0),
                            backgroundColor: "#16a34a",
                            borderRadius: 4,
                            stack: "s",
                        },
                        {
                            label: "فشل / Failed",
                            data: this.state.daily_trend.map((d) => d.failed || 0),
                            backgroundColor: "#dc2626",
                            borderRadius: 4,
                            stack: "s",
                        },
                        {
                            label: "إجمالي / Total",
                            data: this.state.daily_trend.map((d) => d.total || 0),
                            type: "line",
                            borderColor: "#2563eb",
                            backgroundColor: "rgba(37,99,235,.08)",
                            borderWidth: 2,
                            tension: 0.35,
                            fill: true,
                            pointRadius: 2,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: "index", intersect: false },
                    plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 10 } } } },
                    scales: {
                        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 9 } } },
                        y: { stacked: true, beginAtZero: true, ticks: { precision: 0, font: { size: 10 } } },
                    },
                },
            });
        }

        // 2) Status distribution doughnut
        if (this.statusCanvas.el) {
            const k = this.state.kpi || {};
            this._charts.status = new Chart(this.statusCanvas.el, {
                type: "doughnut",
                data: {
                    labels: ["تم التوصيل", "في الطريق", "مخصص", "فشل"],
                    datasets: [
                        {
                            data: [k.delivered || 0, k.in_transit || 0, k.assigned || 0, k.failed || 0],
                            backgroundColor: ["#16a34a", "#2563eb", "#d97706", "#dc2626"],
                            borderWidth: 2,
                            borderColor: "#fff",
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "62%",
                    plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 10 } } } },
                },
            });
        }

        // 3) Carrier comparison — orders vs delivered per carrier
        if (this.carrierCanvas.el && this.state.carriers_data.length) {
            const cd = this.state.carriers_data;
            this._charts.carrier = new Chart(this.carrierCanvas.el, {
                type: "bar",
                data: {
                    labels: cd.map((c) => c.name),
                    datasets: [
                        {
                            label: "طلبات / Orders",
                            data: cd.map((c) => c.total || 0),
                            backgroundColor: "#93c5fd",
                            borderRadius: 4,
                        },
                        {
                            label: "مُوصَّل / Delivered",
                            data: cd.map((c) => c.delivered || 0),
                            backgroundColor: "#16a34a",
                            borderRadius: 4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 10 } } } },
                    scales: {
                        x: { grid: { display: false }, ticks: { font: { size: 9 } } },
                        y: { beginAtZero: true, ticks: { precision: 0, font: { size: 10 } } },
                    },
                },
            });
        }
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
