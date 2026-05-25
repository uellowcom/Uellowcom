/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, xml } from "@odoo/owl";

class SmartConnectorDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            data: null,
        });
        onMounted(() => this.loadData());
    }

    async loadData() {
        try {
            const data = await this.orm.call(
                "uellow.sc.dashboard",
                "get_dashboard_data",
                [],
            );
            this.state.data = data;
        } catch (e) {
            this.notification.add("Failed to load dashboard data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    openImportJobs() {
        this.action.doAction("uellow_smart_connector.action_import_job");
    }
    openNewJob() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "uellow.import.job",
            views: [[false, "form"]],
            target: "current",
        });
    }
    openPriceIntel() {
        this.action.doAction("uellow_smart_connector.action_price_intel");
    }
    openDeadStock() {
        this.action.doAction("uellow_smart_connector.action_dead_stock");
    }
    openJob(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "uellow.import.job",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    openPriceRecord(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "uellow.price.intelligence",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    getBadgeClass(state) {
        const map = {
            draft: "sc-badge-gray",
            processing: "sc-badge-info",
            review: "sc-badge-warn",
            done: "sc-badge-ok",
            error: "sc-badge-err",
            rolled_back: "sc-badge-gray",
            pricier: "sc-badge-err",
            cheaper: "sc-badge-ok",
            ok: "sc-badge-ok",
        };
        return map[state] || "sc-badge-gray";
    }

    getStateLabel(state) {
        const map = {
            draft: "Draft",
            processing: "Processing",
            review: "Review",
            done: "Done",
            error: "Error",
            rolled_back: "Rolled Back",
            pricier: "We're More Expensive",
            cheaper: "We're Cheaper",
            ok: "Normal",
        };
        return map[state] || state;
    }

    static template = xml`
<div class="sc-dashboard">
    <t t-if="state.loading">
        <div class="sc-loading">
            <i class="fa fa-spinner fa-spin"></i>
            Loading dashboard...
        </div>
    </t>

    <t t-elif="state.data">
        <!-- Header -->
        <div class="sc-header">
            <div>
                <div class="sc-header-title">
                    Smart <span>Connector</span>
                </div>
                <div class="sc-header-sub">
                    Product Import · AI Enrichment · Price Intelligence · Dead Stock
                </div>
            </div>
            <div class="sc-header-actions">
                <button class="sc-btn-outline" t-on-click="openImportJobs">
                    <i class="fa fa-list"></i> All Jobs
                </button>
                <button class="sc-btn-primary" t-on-click="openNewJob">
                    <i class="fa fa-plus"></i> New Import
                </button>
            </div>
        </div>

        <!-- Alerts -->
        <t t-if="state.data.jobs.review > 0">
            <div class="sc-alert sc-alert-warn">
                <i class="fa fa-clock-o"></i>
                <strong t-out="state.data.jobs.review"/> import job(s) waiting for review.
                <button class="sc-card-action" style="margin-left:auto" t-on-click="openImportJobs">
                    Review now →
                </button>
            </div>
        </t>
        <t t-if="state.data.dead_stock.critical > 0">
            <div class="sc-alert sc-alert-danger">
                <i class="fa fa-exclamation-triangle"></i>
                <strong t-out="state.data.dead_stock.critical"/> products with critical dead stock.
                <button class="sc-card-action" style="margin-left:auto" t-on-click="openDeadStock">
                    View →
                </button>
            </div>
        </t>

        <!-- KPI Grid -->
        <div class="sc-kpi-grid">
            <!-- Import Jobs -->
            <div class="sc-kpi-card green" t-on-click="openImportJobs">
                <div class="sc-kpi-icon green"><i class="fa fa-download"></i></div>
                <div class="sc-kpi-value" t-out="state.data.jobs.total"></div>
                <div class="sc-kpi-label">Import Jobs</div>
                <div class="sc-kpi-sub">
                    <t t-out="state.data.jobs.done"/> done ·
                    <t t-out="state.data.jobs.review"/> pending
                    <t t-if="state.data.jobs.review > 0">
                        <span class="sc-kpi-badge warn"><t t-out="state.data.jobs.review"/> to review</span>
                    </t>
                </div>
            </div>

            <!-- Products Imported -->
            <div class="sc-kpi-card blue" t-on-click="openImportJobs">
                <div class="sc-kpi-icon blue"><i class="fa fa-cube"></i></div>
                <div class="sc-kpi-value" t-out="state.data.products.imported"></div>
                <div class="sc-kpi-label">Products Imported</div>
                <div class="sc-kpi-sub">
                    <t t-out="state.data.products.ai_enriched"/> AI enriched ·
                    <t t-if="state.data.products.pending > 0">
                        <span class="sc-kpi-badge warn"><t t-out="state.data.products.pending"/> pending</span>
                    </t>
                </div>
            </div>

            <!-- Price Intelligence -->
            <div class="sc-kpi-card amber" t-on-click="openPriceIntel">
                <div class="sc-kpi-icon amber"><i class="fa fa-line-chart"></i></div>
                <div class="sc-kpi-value" t-out="state.data.price_intel.monitored"></div>
                <div class="sc-kpi-label">Prices Monitored</div>
                <div class="sc-kpi-sub">
                    <t t-out="state.data.price_intel.pricier"/> we're expensive ·
                    <t t-out="state.data.price_intel.cheaper"/> we're cheaper
                    <t t-if="state.data.price_intel.pricier > 0">
                        <span class="sc-kpi-badge danger"><t t-out="state.data.price_intel.pricier"/> alerts</span>
                    </t>
                </div>
            </div>

            <!-- Dead Stock -->
            <div class="sc-kpi-card red" t-on-click="openDeadStock">
                <div class="sc-kpi-icon red"><i class="fa fa-archive"></i></div>
                <div class="sc-kpi-value" t-out="state.data.dead_stock.total"></div>
                <div class="sc-kpi-label">Dead Stock Items</div>
                <div class="sc-kpi-sub">
                    <t t-if="state.data.dead_stock.critical > 0">
                        <span class="sc-kpi-badge danger"><t t-out="state.data.dead_stock.critical"/> critical</span>
                    </t>
                    <t t-else="">
                        No critical items
                    </t>
                </div>
            </div>
        </div>

        <!-- Section Grid -->
        <div class="sc-section-grid">

            <!-- Recent Import Jobs -->
            <div class="sc-card">
                <div class="sc-card-header">
                    <span class="sc-card-title">
                        <i class="fa fa-history" style="margin-right:6px;color:#1A7A6E"></i>
                        Recent Import Jobs
                    </span>
                    <button class="sc-card-action" t-on-click="openImportJobs">View all →</button>
                </div>
                <table class="sc-table">
                    <thead>
                        <tr>
                            <th>Job</th>
                            <th>Type</th>
                            <th>Products</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-if="state.data.recent_jobs.length === 0">
                            <tr>
                                <td colspan="4">
                                    <div class="sc-empty">
                                        <i class="fa fa-inbox"></i>
                                        No import jobs yet
                                    </div>
                                </td>
                            </tr>
                        </t>
                        <t t-foreach="state.data.recent_jobs" t-as="job" t-key="job.id">
                            <tr t-on-click="() => this.openJob(job.id)">
                                <td style="font-weight:600" t-out="job.name"></td>
                                <td>
                                    <span class="sc-badge sc-badge-info" t-out="job.type"></span>
                                </td>
                                <td t-out="job.total"></td>
                                <td>
                                    <span t-att-class="'sc-badge ' + this.getBadgeClass(job.state)"
                                          t-out="this.getStateLabel(job.state)">
                                    </span>
                                </td>
                            </tr>
                        </t>
                    </tbody>
                </table>
            </div>

            <!-- Price Alerts -->
            <div class="sc-card">
                <div class="sc-card-header">
                    <span class="sc-card-title">
                        <i class="fa fa-bell" style="margin-right:6px;color:#f59e0b"></i>
                        Price Alerts
                    </span>
                    <button class="sc-card-action" t-on-click="openPriceIntel">View all →</button>
                </div>
                <table class="sc-table">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Our Price</th>
                            <th>Competitor</th>
                            <th>Diff</th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-if="state.data.price_alerts.length === 0">
                            <tr>
                                <td colspan="4">
                                    <div class="sc-empty">
                                        <i class="fa fa-check-circle"></i>
                                        No price alerts
                                    </div>
                                </td>
                            </tr>
                        </t>
                        <t t-foreach="state.data.price_alerts" t-as="alert" t-key="alert.id">
                            <tr t-on-click="() => this.openPriceRecord(alert.id)">
                                <td style="font-weight:600" t-out="alert.product"></td>
                                <td t-out="alert.our_price.toFixed(3) + ' KD'"></td>
                                <td t-out="alert.competitor_price.toFixed(3) + ' KD'"></td>
                                <td>
                                    <span t-att-class="'sc-badge ' + (alert.diff > 0 ? 'sc-badge-err' : 'sc-badge-ok')"
                                          t-out="(alert.diff > 0 ? '+' : '') + alert.diff.toFixed(1) + '%'">
                                    </span>
                                </td>
                            </tr>
                        </t>
                    </tbody>
                </table>
            </div>

        </div>

        <!-- Quick Actions -->
        <div class="sc-card">
            <div class="sc-card-header">
                <span class="sc-card-title">
                    <i class="fa fa-bolt" style="margin-right:6px;color:#1A7A6E"></i>
                    Quick Actions
                </span>
            </div>
            <div style="padding:16px;display:flex;gap:10px;flex-wrap:wrap">
                <button class="sc-btn-primary" t-on-click="openNewJob">
                    <i class="fa fa-upload"></i> Import from URL
                </button>
                <button class="sc-btn-outline" t-on-click="openNewJob">
                    <i class="fa fa-file-excel-o"></i> Import from Excel
                </button>
                <button class="sc-btn-outline" t-on-click="openPriceIntel">
                    <i class="fa fa-plus"></i> Monitor New Price
                </button>
                <button class="sc-btn-outline" t-on-click="openDeadStock">
                    <i class="fa fa-refresh"></i> Refresh Dead Stock
                </button>
            </div>
        </div>

    </t>
</div>
    `;
}

registry.category("actions").add("sc_dashboard_action", SmartConnectorDashboard);
