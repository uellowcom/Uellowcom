/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, xml } from "@odoo/owl";

class ProfitManager extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            data: null,
            search: "",
            filt: "all",
            sort: "margin_asc",
            offset: 0,
            limit: 40,
            editId: null,
            editValue: "",
        });
        onMounted(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("uellow.sc.profit", "get_profit_data", [], {
                search: this.state.search,
                filt: this.state.filt,
                sort: this.state.sort,
                offset: this.state.offset,
                limit: this.state.limit,
            });
        } catch (e) {
            this.notification.add("Failed to load profit data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    setFilter(f) { this.state.filt = f; this.state.offset = 0; this.load(); }
    setSort(s) { this.state.sort = s; this.state.offset = 0; this.load(); }
    onSearchKey(ev) { if (ev.key === "Enter") { this.state.offset = 0; this.load(); } }
    doSearch() { this.state.offset = 0; this.load(); }

    next() {
        if (this.state.offset + this.state.limit < this.state.data.total) {
            this.state.offset += this.state.limit;
            this.load();
        }
    }
    prev() {
        if (this.state.offset > 0) {
            this.state.offset = Math.max(0, this.state.offset - this.state.limit);
            this.load();
        }
    }

    startEdit(row) {
        this.state.editId = row.id;
        this.state.editValue = String(row.price);
    }
    cancelEdit() { this.state.editId = null; this.state.editValue = ""; }

    async saveEdit(row) {
        try {
            const updated = await this.orm.call("uellow.sc.profit", "set_price", [
                row.id, parseFloat(this.state.editValue),
            ]);
            Object.assign(row, updated);
            this.notification.add("Price updated", { type: "success" });
        } catch (e) {
            this.notification.add(e.data?.message || "Update failed", { type: "danger" });
        } finally {
            this.cancelEdit();
            this.load();
        }
    }

    async toggleAvail(row) {
        try {
            const updated = await this.orm.call("uellow.sc.profit", "toggle_available", [row.id]);
            Object.assign(row, updated);
        } catch (e) {
            this.notification.add("Failed to change availability", { type: "danger" });
        }
    }

    marginClass(m) {
        if (m < 0) return "sc-badge-err";
        if (m < 10) return "sc-badge-warn";
        if (m >= 40) return "sc-badge-ok";
        return "sc-badge-info";
    }
    fmt(v) { return (v ?? 0).toFixed(3); }

    static template = xml`
<div class="sc-dashboard">
    <!-- Header -->
    <div class="sc-header">
        <div>
            <div class="sc-header-title">Profit <span>Margins</span></div>
            <div class="sc-header-sub">Cost · Sale · Profit · Margin % · Installments · Availability · هوامش الربح</div>
        </div>
        <div class="sc-header-actions">
            <input type="text" class="sc-search" placeholder="Search product / SKU…"
                   t-model="state.search" t-on-keydown="onSearchKey"
                   style="padding:8px 12px;border:1px solid #d8e0dd;border-radius:8px;min-width:220px"/>
            <button class="sc-btn-primary" t-on-click="doSearch"><i class="fa fa-search"></i> Search</button>
        </div>
    </div>

    <t t-if="state.data">
        <!-- KPI stats -->
        <div class="sc-kpi-grid">
            <div class="sc-kpi-card green">
                <div class="sc-kpi-icon green"><i class="fa fa-cubes"></i></div>
                <div class="sc-kpi-value" t-out="state.data.stats.count"></div>
                <div class="sc-kpi-label">Products in view · منتجات</div>
                <div class="sc-kpi-sub"><t t-out="state.data.stats.available"/> available for sale</div>
            </div>
            <div class="sc-kpi-card blue">
                <div class="sc-kpi-icon blue"><i class="fa fa-percent"></i></div>
                <div class="sc-kpi-value"><t t-out="state.data.stats.avg_margin"/>%</div>
                <div class="sc-kpi-label">Avg Margin · متوسط الهامش</div>
                <div class="sc-kpi-sub">across the current view</div>
            </div>
            <div class="sc-kpi-card amber">
                <div class="sc-kpi-icon amber"><i class="fa fa-money"></i></div>
                <div class="sc-kpi-value"><t t-out="this.fmt(state.data.stats.total_profit)"/> <span style="font-size:14px">KD</span></div>
                <div class="sc-kpi-label">Total Profit Spread · إجمالي الربح</div>
                <div class="sc-kpi-sub">sale <t t-out="this.fmt(state.data.stats.total_sale)"/> − cost <t t-out="this.fmt(state.data.stats.total_cost)"/></div>
            </div>
            <div class="sc-kpi-card red">
                <div class="sc-kpi-icon red"><i class="fa fa-exclamation-triangle"></i></div>
                <div class="sc-kpi-value" t-out="state.data.stats.negative"></div>
                <div class="sc-kpi-label">Losing / Negative · خسارة</div>
                <div class="sc-kpi-sub">
                    <t t-if="state.data.stats.low > 0"><span class="sc-kpi-badge warn"><t t-out="state.data.stats.low"/> thin (&lt;10%)</span></t>
                    <t t-else="">no thin-margin items</t>
                </div>
            </div>
            <div class="sc-kpi-card blue">
                <div class="sc-kpi-icon blue"><i class="fa fa-credit-card"></i></div>
                <div class="sc-kpi-value" t-out="state.data.stats.installment"></div>
                <div class="sc-kpi-label">Installment-eligible · أقساط</div>
                <div class="sc-kpi-sub">
                    <t t-if="state.data.stats.bnpl_on">min <t t-out="state.data.stats.bnpl_min"/> KD</t>
                    <t t-else=""><span class="sc-kpi-badge danger">installments OFF</span></t>
                </div>
            </div>
        </div>

        <!-- Filter + sort chips -->
        <div class="sc-card" style="padding:12px 16px;display:flex;gap:14px;flex-wrap:wrap;align-items:center">
            <div style="display:flex;gap:6px;flex-wrap:wrap">
                <span style="font-weight:700;color:#6b7280;font-size:12px;align-self:center">FILTER:</span>
                <t t-foreach="[['all','All'],['negative','Losing'],['low','Thin &lt;10%'],['high','High ≥40%'],['installment','Installments'],['available','Available'],['unavailable','Hidden']]" t-as="f" t-key="f[0]">
                    <button t-att-class="'sc-chip ' + (state.filt === f[0] ? 'sc-chip-on' : '')"
                            t-on-click="() => this.setFilter(f[0])" t-out="f[1]"
                            style="padding:5px 12px;border-radius:999px;border:1px solid #d8e0dd;background:#fff;cursor:pointer;font-size:12px"/>
                </t>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-left:auto">
                <span style="font-weight:700;color:#6b7280;font-size:12px;align-self:center">SORT:</span>
                <t t-foreach="[['margin_asc','Lowest margin'],['margin_desc','Highest margin'],['profit_asc','Lowest profit'],['profit_desc','Highest profit'],['price_desc','Priciest']]" t-as="o" t-key="o[0]">
                    <button t-att-class="'sc-chip ' + (state.sort === o[0] ? 'sc-chip-on' : '')"
                            t-on-click="() => this.setSort(o[0])" t-out="o[1]"
                            style="padding:5px 12px;border-radius:999px;border:1px solid #d8e0dd;background:#fff;cursor:pointer;font-size:12px"/>
                </t>
            </div>
        </div>

        <!-- Table -->
        <div class="sc-card">
            <table class="sc-table" style="table-layout:fixed;width:100%">
                <thead>
                    <tr>
                        <th style="width:34%">Product · المنتج</th>
                        <th style="width:10%">Cost</th>
                        <th style="width:10%">Sale</th>
                        <th style="width:11%">Profit</th>
                        <th style="width:9%">Margin</th>
                        <th style="width:9%">Install.</th>
                        <th style="width:8%">Sale?</th>
                        <th style="width:auto">Price</th>
                    </tr>
                </thead>
                <tbody>
                    <t t-if="state.loading">
                        <tr><td colspan="8"><div class="sc-empty"><i class="fa fa-spinner fa-spin"></i> Loading…</div></td></tr>
                    </t>
                    <t t-elif="state.data.rows.length === 0">
                        <tr><td colspan="8"><div class="sc-empty"><i class="fa fa-inbox"></i> No products match</div></td></tr>
                    </t>
                    <t t-foreach="state.data.rows" t-as="row" t-key="row.id">
                        <tr t-att-style="row.profit &lt; 0 ? 'background:#fdeaea' : (row.margin &lt; 10 ? 'background:#fff8ec' : '')">
                            <td style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                                <span style="font-weight:600" t-out="row.name"></span>
                                <span t-if="row.code" class="text-muted" style="font-size:11px"> · <t t-out="row.code"/></span>
                            </td>
                            <td t-out="this.fmt(row.cost)"></td>
                            <td style="font-weight:600" t-out="this.fmt(row.price)"></td>
                            <td t-att-style="row.profit &lt; 0 ? 'color:#c62828;font-weight:700' : 'color:#067a55;font-weight:600'"
                                t-out="this.fmt(row.profit)"></td>
                            <td><span t-att-class="'sc-badge ' + this.marginClass(row.margin)" t-out="row.margin + '%'"></span></td>
                            <td>
                                <span t-if="row.installment" class="sc-badge sc-badge-ok">✓</span>
                                <span t-else="" class="sc-badge sc-badge-gray">—</span>
                            </td>
                            <td>
                                <span t-att-class="'sc-badge ' + (row.available ? 'sc-badge-ok' : 'sc-badge-gray')"
                                      style="cursor:pointer" t-on-click="() => this.toggleAvail(row)"
                                      t-out="row.available ? 'On' : 'Off'"/>
                            </td>
                            <td>
                                <t t-if="state.editId === row.id">
                                    <div style="display:flex;gap:4px;align-items:center">
                                        <input type="number" step="0.001" t-model="state.editValue"
                                               style="width:80px;padding:3px 6px;border:1px solid #1A7A6E;border-radius:6px"/>
                                        <button class="sc-icon-btn" t-on-click="() => this.saveEdit(row)" title="Save"><i class="fa fa-check" style="color:#067a55"></i></button>
                                        <button class="sc-icon-btn" t-on-click="cancelEdit" title="Cancel"><i class="fa fa-times" style="color:#c62828"></i></button>
                                    </div>
                                </t>
                                <t t-else="">
                                    <button class="sc-btn-outline" style="padding:4px 10px;font-size:12px"
                                            t-on-click="() => this.startEdit(row)">
                                        <i class="fa fa-pencil"></i> Change
                                    </button>
                                </t>
                            </td>
                        </tr>
                    </t>
                </tbody>
            </table>
            <!-- pagination -->
            <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-top:1px solid #eef0f3">
                <span class="text-muted" style="font-size:12px">
                    <t t-out="state.data.total === 0 ? 0 : (state.data.offset + 1)"/>–<t t-out="Math.min(state.data.offset + state.data.limit, state.data.total)"/>
                    of <t t-out="state.data.total"/>
                </span>
                <div style="display:flex;gap:8px">
                    <button class="sc-btn-outline" t-on-click="prev" t-att-disabled="state.data.offset === 0">
                        <i class="fa fa-chevron-left"></i> Prev
                    </button>
                    <button class="sc-btn-outline" t-on-click="next"
                            t-att-disabled="state.data.offset + state.data.limit >= state.data.total">
                        Next <i class="fa fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        </div>
    </t>
</div>
    `;
}

registry.category("actions").add("sc_profit_action", ProfitManager);
