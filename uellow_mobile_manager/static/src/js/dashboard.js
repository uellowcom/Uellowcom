/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";

class MobileDashboard extends Component {
    static template = "mobile_manager.DashboardTemplate";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            data: null,
            error: null,
            lastUpdate: null,
        });
        this._interval = null;
        onMounted(() => {
            this.loadData();
            this._interval = setInterval(() => this.loadData(), 30000);
        });
        onWillUnmount(() => {
            if (this._interval) clearInterval(this._interval);
        });
    }

    async loadData() {
        try {
            const result = await this.orm.call("mobile.dashboard", "get_dashboard_data", [], {});
            this.state.data = result;
            this.state.lastUpdate = new Date().toLocaleTimeString();
            this.state.loading = false;
            this.state.error = null;
        } catch (e) {
            this.state.error = e.message || "Failed to load dashboard data";
            this.state.loading = false;
        }
    }

    formatCurrency(val) {
        return "KD " + (val || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    get platformChartStyle() {
        if (!this.state.data) return "";
        const a = this.state.data.users.android_pct;
        return `background: conic-gradient(#3DDC84 0% ${a}%, #007AFF ${a}% 100%)`;
    }
}

registry.category("actions").add("mobile_manager.Dashboard", MobileDashboard);
