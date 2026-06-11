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
    openTranslation() {
        this.action.doAction("uellow_smart_connector.action_translate_job");
    }
    openPublishStudio() {
        this.action.doAction("uellow_smart_connector.action_publish_studio");
    }
    openProfit() {
        this.action.doAction("uellow_smart_connector.action_profit_manager");
    }
    openReorder() {
        this.action.doAction("uellow_smart_connector.action_reorder_forecast");
    }
    openScorecard() {
        this.action.doAction("uellow_smart_connector.action_supplier_scorecard");
    }
    openDiscovery() {
        this.action.doAction("uellow_smart_connector.action_discovery");
    }
    openMarket() {
        this.action.doAction("uellow_smart_connector.action_market_pricer");
    }
    openGlossary() {
        this.action.doAction("uellow_smart_connector.action_glossary");
    }
    openCopilot() {
        this.action.doAction("uellow_smart_connector.action_copilot");
    }
    openSettings() {
        this.action.doAction("uellow_smart_connector.action_connector_settings");
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
                    Import · Publish Studio · Pricing · Reorder · Suppliers · Discovery · Dead Stock
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
        <t t-if="state.data.studio.ready > 0">
            <div class="sc-alert sc-alert-warn">
                <i class="fa fa-paint-brush"></i>
                <strong t-out="state.data.studio.ready"/> new product(s) ready to publish.
                <button class="sc-card-action" style="margin-left:auto" t-on-click="openPublishStudio">
                    Open Publish Studio →
                </button>
            </div>
        </t>
        <t t-if="state.data.reorder.urgent > 0">
            <div class="sc-alert sc-alert-danger">
                <i class="fa fa-refresh"></i>
                <strong t-out="state.data.reorder.urgent"/> product(s) need urgent restock.
                <button class="sc-card-action" style="margin-left:auto" t-on-click="openReorder">
                    View →
                </button>
            </div>
        </t>
        <t t-if="state.data.profit.negative > 0">
            <div class="sc-alert sc-alert-danger">
                <i class="fa fa-percent"></i>
                <strong t-out="state.data.profit.negative"/> product(s) sold below cost (losing money).
                <button class="sc-card-action" style="margin-left:auto" t-on-click="openProfit">
                    Fix prices →
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
                <div class="sc-kpi-label">Dead Stock · مخزون راكد</div>
                <div class="sc-kpi-sub">
                    <t t-if="state.data.dead_stock.critical > 0">
                        <span class="sc-kpi-badge danger"><t t-out="state.data.dead_stock.critical"/> critical</span>
                    </t>
                    <t t-else="">No critical items</t>
                    <t t-if="state.data.dead_stock.seasonal > 0">
                        · <t t-out="state.data.dead_stock.seasonal"/> seasonal
                    </t>
                </div>
            </div>

            <!-- Idle Capital (dead-stock value) -->
            <div class="sc-kpi-card red" t-on-click="openDeadStock">
                <div class="sc-kpi-icon red"><i class="fa fa-money"></i></div>
                <div class="sc-kpi-value"><t t-out="state.data.dead_stock.value_kd"/> <span style="font-size:14px">KD</span></div>
                <div class="sc-kpi-label">Idle Capital · رأس مال مجمّد</div>
                <div class="sc-kpi-sub">
                    <t t-if="state.data.dead_stock.promote > 0">
                        <span class="sc-kpi-badge warn"><t t-out="state.data.dead_stock.promote"/> via Beena</span>
                    </t>
                    <t t-else="">tied up in stale stock</t>
                </div>
            </div>

            <!-- Translation Coverage -->
            <div class="sc-kpi-card blue" t-on-click="openTranslation">
                <div class="sc-kpi-icon blue"><i class="fa fa-language"></i></div>
                <div class="sc-kpi-value"><t t-out="state.data.translation.coverage"/>%</div>
                <div class="sc-kpi-label">Arabic Coverage · تغطية الترجمة</div>
                <div class="sc-kpi-sub">
                    <t t-if="state.data.translation.pending > 0">
                        <span class="sc-kpi-badge warn"><t t-out="state.data.translation.pending"/> pending</span>
                    </t>
                    <t t-else="">catalog translated</t>
                </div>
            </div>

            <!-- Publish Studio -->
            <div class="sc-kpi-card green" t-on-click="openPublishStudio">
                <div class="sc-kpi-icon green"><i class="fa fa-paint-brush"></i></div>
                <div class="sc-kpi-value" t-out="state.data.studio.pending"></div>
                <div class="sc-kpi-label">Publish Studio · استوديو النشر</div>
                <div class="sc-kpi-sub">
                    <t t-out="state.data.studio.published"/> published ·
                    <t t-if="state.data.studio.ready > 0">
                        <span class="sc-kpi-badge ok"><t t-out="state.data.studio.ready"/> ready</span>
                    </t>
                    <t t-else="">new products to prepare</t>
                </div>
            </div>

            <!-- Reorder Forecast -->
            <div class="sc-kpi-card amber" t-on-click="openReorder">
                <div class="sc-kpi-icon amber"><i class="fa fa-refresh"></i></div>
                <div class="sc-kpi-value" t-out="state.data.reorder.total"></div>
                <div class="sc-kpi-label">Reorder Needed · إعادة طلب</div>
                <div class="sc-kpi-sub">
                    <t t-if="state.data.reorder.urgent > 0">
                        <span class="sc-kpi-badge danger"><t t-out="state.data.reorder.urgent"/> urgent</span>
                    </t>
                    <t t-else="">stock levels healthy</t>
                    · <t t-out="state.data.reorder.reorder"/> soon
                </div>
            </div>

            <!-- Supplier Scorecard -->
            <div class="sc-kpi-card blue" t-on-click="openScorecard">
                <div class="sc-kpi-icon blue"><i class="fa fa-star"></i></div>
                <div class="sc-kpi-value" t-out="state.data.scorecard.vendors"></div>
                <div class="sc-kpi-label">Suppliers Scored · تقييم الموردين</div>
                <div class="sc-kpi-sub">
                    <span class="sc-kpi-badge ok"><t t-out="state.data.scorecard.grade_a"/> grade A</span>
                    <t t-if="state.data.scorecard.poor > 0">
                        · <span class="sc-kpi-badge warn"><t t-out="state.data.scorecard.poor"/> weak</span>
                    </t>
                </div>
            </div>

            <!-- Competitor Discovery -->
            <div class="sc-kpi-card green" t-on-click="openDiscovery">
                <div class="sc-kpi-icon green"><i class="fa fa-binoculars"></i></div>
                <div class="sc-kpi-value" t-out="state.data.discovery.opportunities"></div>
                <div class="sc-kpi-label">Opportunities · فرص منتجات</div>
                <div class="sc-kpi-sub">
                    <t t-out="state.data.discovery.sources"/> competitor sources
                    <t t-if="state.data.discovery.opportunities > 0">
                        <span class="sc-kpi-badge ok">new to sell</span>
                    </t>
                </div>
            </div>

            <!-- Profit Margins -->
            <div class="sc-kpi-card green" t-on-click="openProfit">
                <div class="sc-kpi-icon green"><i class="fa fa-percent"></i></div>
                <div class="sc-kpi-value"><t t-out="state.data.profit.avg_margin"/>%</div>
                <div class="sc-kpi-label">Avg Profit Margin · متوسط الربح</div>
                <div class="sc-kpi-sub">
                    <t t-out="state.data.profit.count"/> products ·
                    <t t-if="state.data.profit.negative > 0">
                        <span class="sc-kpi-badge danger"><t t-out="state.data.profit.negative"/> losing</span>
                    </t>
                    <t t-else="">all profitable</t>
                </div>
            </div>

            <!-- Market Pricing + Glossary -->
            <div class="sc-kpi-card amber" t-on-click="openMarket">
                <div class="sc-kpi-icon amber"><i class="fa fa-globe"></i></div>
                <div class="sc-kpi-value" t-out="state.data.market.factors"></div>
                <div class="sc-kpi-label">Market Factors · التسعير حسب السوق</div>
                <div class="sc-kpi-sub">
                    <t t-out="state.data.market.runs"/> pricing runs ·
                    <t t-out="state.data.glossary"/> glossary terms
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
                                <td t-out="(alert.our_price ?? 0).toFixed(3) + ' KD'"></td>
                                <td t-out="(alert.competitor_price ?? 0).toFixed(3) + ' KD'"></td>
                                <td>
                                    <span t-att-class="'sc-badge ' + ((alert.diff ?? 0) > 0 ? 'sc-badge-err' : 'sc-badge-ok')"
                                          t-out="((alert.diff ?? 0) > 0 ? '+' : '') + (alert.diff ?? 0).toFixed(1) + '%'">
                                    </span>
                                </td>
                            </tr>
                        </t>
                    </tbody>
                </table>
            </div>

        </div>

        <!-- Section Grid 2 -->
        <div class="sc-section-grid">

            <!-- Urgent Reorders -->
            <div class="sc-card">
                <div class="sc-card-header">
                    <span class="sc-card-title">
                        <i class="fa fa-refresh" style="margin-right:6px;color:#f59e0b"></i>
                        Urgent Reorders · إعادة طلب عاجلة
                    </span>
                    <button class="sc-card-action" t-on-click="openReorder">View all →</button>
                </div>
                <table class="sc-table">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Days Left</th>
                            <th>Suggested Qty</th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-if="state.data.urgent_reorders.length === 0">
                            <tr><td colspan="3">
                                <div class="sc-empty"><i class="fa fa-check-circle"></i> Stock levels healthy</div>
                            </td></tr>
                        </t>
                        <t t-foreach="state.data.urgent_reorders" t-as="r" t-key="r.id">
                            <tr>
                                <td style="font-weight:600" t-out="r.product"></td>
                                <td>
                                    <span t-att-class="'sc-badge ' + (r.state === 'urgent' ? 'sc-badge-err' : 'sc-badge-warn')"
                                          t-out="r.days + ' d'"></span>
                                </td>
                                <td t-out="r.qty"></td>
                            </tr>
                        </t>
                    </tbody>
                </table>
            </div>

            <!-- New Competitor Opportunities -->
            <div class="sc-card">
                <div class="sc-card-header">
                    <span class="sc-card-title">
                        <i class="fa fa-binoculars" style="margin-right:6px;color:#1A7A6E"></i>
                        New Opportunities · فرص جديدة
                    </span>
                    <button class="sc-card-action" t-on-click="openDiscovery">View all →</button>
                </div>
                <table class="sc-table">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Source</th>
                            <th>Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-if="state.data.opportunities.length === 0">
                            <tr><td colspan="3">
                                <div class="sc-empty"><i class="fa fa-binoculars"></i> No new opportunities</div>
                            </td></tr>
                        </t>
                        <t t-foreach="state.data.opportunities" t-as="o" t-key="o.id">
                            <tr>
                                <td style="font-weight:600" t-out="o.title"></td>
                                <td t-out="o.source"></td>
                                <td t-out="(o.price ?? 0).toFixed(3) + ' KD'"></td>
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
                    Quick Actions · إجراءات سريعة
                </span>
            </div>
            <div style="padding:16px;display:flex;gap:10px;flex-wrap:wrap">
                <button class="sc-btn-primary" t-on-click="openNewJob">
                    <i class="fa fa-upload"></i> New Import
                </button>
                <button class="sc-btn-outline" t-on-click="openPublishStudio">
                    <i class="fa fa-paint-brush"></i> Publish Studio
                </button>
                <button class="sc-btn-outline" t-on-click="openProfit">
                    <i class="fa fa-percent"></i> Profit Margins
                </button>
                <button class="sc-btn-outline" t-on-click="openPriceIntel">
                    <i class="fa fa-line-chart"></i> Price Intelligence
                </button>
                <button class="sc-btn-outline" t-on-click="openReorder">
                    <i class="fa fa-refresh"></i> Reorder Forecast
                </button>
                <button class="sc-btn-outline" t-on-click="openScorecard">
                    <i class="fa fa-star"></i> Supplier Scorecard
                </button>
                <button class="sc-btn-outline" t-on-click="openDiscovery">
                    <i class="fa fa-binoculars"></i> Competitor Radar
                </button>
                <button class="sc-btn-outline" t-on-click="openMarket">
                    <i class="fa fa-globe"></i> Market Pricing
                </button>
                <button class="sc-btn-outline" t-on-click="openTranslation">
                    <i class="fa fa-language"></i> Translation
                </button>
                <button class="sc-btn-outline" t-on-click="openCopilot">
                    <i class="fa fa-comments"></i> Ops Copilot
                </button>
                <button class="sc-btn-outline" t-on-click="openGlossary">
                    <i class="fa fa-book"></i> Glossary
                </button>
                <button class="sc-btn-outline" t-on-click="openDeadStock">
                    <i class="fa fa-archive"></i> Dead Stock
                </button>
                <button class="sc-btn-outline" t-on-click="openSettings">
                    <i class="fa fa-cog"></i> Settings
                </button>
            </div>
        </div>

    </t>
</div>
    `;
}

registry.category("actions").add("sc_dashboard_action", SmartConnectorDashboard);
