/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, xml } from "@odoo/owl";

class MarketplaceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, data: null });
        onMounted(() => this.loadData());
    }

    async loadData() {
        try {
            const data = await this.orm.call("uellow.marketplace.dashboard", "get_dashboard_data", []);
            this.state.data = data;
        } catch(e) {
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    go(action) {
        this.action.doAction(action);
    }

    goTo(model, domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
            target: "current",
        });
    }

    static template = xml`
<div style="padding:16px;background:#f4f6f8;min-height:100vh;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif">
    <t t-if="state.loading">
        <div style="display:flex;align-items:center;justify-content:center;padding:60px;color:#888;gap:8px">
            <i class="fa fa-spinner fa-spin"></i> Loading dashboard...
        </div>
    </t>
    <t t-elif="state.data">
        <t t-set="d" t-value="state.data"/>

        <!-- Header -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
            <div>
                <div style="font-size:20px;font-weight:700;color:#1a1a1a">Marketplace Dashboard</div>
                <div style="font-size:12px;color:#888;margin-top:2px">Real-time overview of all modules</div>
            </div>
            <button t-on-click="() => this.loadData()"
                    style="background:#1A7A6E;color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:12px;cursor:pointer;display:flex;align-items:center;gap:5px">
                <i class="fa fa-refresh"></i> Refresh
            </button>
        </div>

        <!-- Section: Marketplace -->
        <div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.06em;margin:0 0 8px;display:flex;align-items:center;gap:5px">
            <i class="fa fa-building" style="color:#1A7A6E"></i> Marketplace
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px">
            <div t-on-click="() => this.go('uellow_multivendor.action_sale_orders')"
                 style="background:#E1F5EE;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-money" style="color:#085041"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#085041"><t t-esc="d.gmv.toFixed(3)"/></div>
                <div style="font-size:11px;color:#0F6E56;margin-top:3px">GMV this month (KD)</div>
            </div>
            <div t-on-click="() => this.goTo('sale.order', [['state','in',['sale','done']]], 'Orders')"
                 style="background:#FAEEDA;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-shopping-bag" style="color:#633806"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#633806"><t t-esc="d.order_count"/></div>
                <div style="font-size:11px;color:#854F0B;margin-top:3px">Orders this month</div>
            </div>
            <div t-on-click="() => this.goTo('uellow.vendor', [['state','=','active']], 'Active Vendors')"
                 style="background:#E6F1FB;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-users" style="color:#0C447C"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#0C447C"><t t-esc="d.active_vendors"/></div>
                <div style="font-size:11px;color:#185FA5;margin-top:3px">Active vendors</div>
                <div t-if="d.pending_vendors > 0" style="font-size:10px;padding:1px 5px;border-radius:20px;background:#FAEEDA;color:#633806;display:inline-block;margin-top:3px">
                    <t t-esc="d.pending_vendors"/> pending
                </div>
            </div>
            <div t-on-click="() => this.goTo('uellow.vendor.commission', [], 'Commissions')"
                 style="background:#EAF3DE;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-percent" style="color:#27500A"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#27500A"><t t-esc="d.commission.toFixed(3)"/></div>
                <div style="font-size:11px;color:#3B6D11;margin-top:3px">Commissions (KD)</div>
                <div style="font-size:10px;color:#3B6D11;margin-top:2px">Take rate: <t t-esc="d.take_rate"/>%</div>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px">
            <div t-on-click="() => this.go('uellow_multivendor.action_vendor_product_approval')"
                 style="background:#EEEDFE;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-cube" style="color:#3C3489"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#3C3489"><t t-esc="d.approved_products"/></div>
                <div style="font-size:11px;color:#534AB7;margin-top:3px">Approved products</div>
                <div t-if="d.pending_products > 0" style="font-size:10px;padding:1px 5px;border-radius:20px;background:#FAEEDA;color:#633806;display:inline-block;margin-top:3px">
                    <t t-esc="d.pending_products"/> pending
                </div>
            </div>
            <div t-on-click="() => this.goTo('uellow.vendor.payout', [['state','=','pending']], 'Pending Payouts')"
                 style="background:#FBEAF0;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-download" style="color:#72243E"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#72243E"><t t-esc="d.pending_payout_amount.toFixed(3)"/></div>
                <div style="font-size:11px;color:#993556;margin-top:3px">Pending payouts (KD)</div>
                <div style="font-size:10px;color:#993556;margin-top:2px"><t t-esc="d.pending_payouts"/> requests</div>
            </div>
            <div style="background:#FCEBEB;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-times-circle" style="color:#791F1F"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#791F1F"><t t-esc="d.cancel_rate"/>%</div>
                <div style="font-size:11px;color:#A32D2D;margin-top:3px">Cancel rate</div>
            </div>
            <div style="background:#FAEEDA;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-star" style="color:#633806"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#633806"><t t-esc="d.avg_rating"/></div>
                <div style="font-size:11px;color:#854F0B;margin-top:3px">Avg vendor rating</div>
            </div>
        </div>

        <!-- Charts row -->
        <div style="display:grid;grid-template-columns:3fr 2fr;gap:10px;margin-bottom:14px">
            <div style="background:#fff;border:0.5px solid #eee;border-radius:12px;overflow:hidden">
                <div style="padding:10px 14px;border-bottom:0.5px solid #f0f0f0;font-size:13px;font-weight:700;color:#1a1a1a">
                    <i class="fa fa-bar-chart" style="color:#1A7A6E;margin-right:5px"></i>GMV — last 7 days
                </div>
                <div style="padding:14px">
                    <canvas id="gmvChart" style="width:100%;height:140px"></canvas>
                </div>
            </div>
            <div style="background:#fff;border:0.5px solid #eee;border-radius:12px;overflow:hidden">
                <div style="padding:10px 14px;border-bottom:0.5px solid #f0f0f0;font-size:13px;font-weight:700;color:#1a1a1a">
                    <i class="fa fa-trophy" style="color:#BA7517;margin-right:5px"></i>Top vendors
                </div>
                <div style="padding:10px 14px">
                    <t t-foreach="d.top_vendors" t-as="v" t-key="v.name">
                        <div t-on-click="() => this.goTo('uellow.vendor', [['store_name_en','=',v.name]], v.name)"
                             style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:0.5px solid #f5f5f5;cursor:pointer">
                            <span style="font-size:12px;font-weight:600;color:#1a1a1a"><t t-esc="v.name"/></span>
                            <span style="font-size:12px;font-weight:600;color:#085041"><t t-esc="v.gmv.toFixed(3)"/> KD</span>
                        </div>
                    </t>
                    <t t-if="!d.top_vendors.length">
                        <div style="text-align:center;padding:20px;color:#aaa;font-size:12px">No data</div>
                    </t>
                </div>
            </div>
        </div>

        <!-- Section: Smart Connector -->
        <div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.06em;margin:0 0 8px;display:flex;align-items:center;gap:5px">
            <i class="fa fa-plug" style="color:#534AB7"></i> Smart Connector
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px">
            <div t-on-click="() => this.go('uellow_smart_connector.action_import_job')"
                 style="background:#EEEDFE;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-download" style="color:#3C3489"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#3C3489"><t t-esc="d.sc_total"/></div>
                <div style="font-size:11px;color:#534AB7;margin-top:3px">Import jobs</div>
                <div t-if="d.sc_review > 0" style="font-size:10px;padding:1px 5px;border-radius:20px;background:#FAEEDA;color:#633806;display:inline-block;margin-top:3px">
                    <t t-esc="d.sc_review"/> to review
                </div>
            </div>
            <div t-on-click="() => this.go('uellow_smart_connector.action_import_job')"
                 style="background:#E1F5EE;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-cube" style="color:#085041"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#085041"><t t-esc="d.sc_imported"/></div>
                <div style="font-size:11px;color:#0F6E56;margin-top:3px">Products imported</div>
            </div>
            <div t-on-click="() => this.go('uellow_smart_connector.action_price_intel')"
                 style="background:#FCEBEB;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-line-chart" style="color:#791F1F"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#791F1F"><t t-esc="d.sc_price_alerts"/></div>
                <div style="font-size:11px;color:#A32D2D;margin-top:3px">Price alerts</div>
            </div>
            <div t-on-click="() => this.go('uellow_smart_connector.action_dead_stock')"
                 style="background:#FAEEDA;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-archive" style="color:#633806"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#633806"><t t-esc="d.sc_dead"/></div>
                <div style="font-size:11px;color:#854F0B;margin-top:3px">Dead stock items</div>
            </div>
        </div>

        <!-- Section: Reviews & Products -->
        <div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.06em;margin:0 0 8px;display:flex;align-items:center;gap:5px">
            <i class="fa fa-star" style="color:#BA7517"></i> Reviews
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px">
            <div style="background:#FAEEDA;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-comment" style="color:#633806"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#633806"><t t-esc="d.month_reviews"/></div>
                <div style="font-size:11px;color:#854F0B;margin-top:3px">Reviews this month</div>
            </div>
            <div style="background:#FBEAF0;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-star" style="color:#72243E"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#72243E"><t t-esc="d.avg_product_rating"/></div>
                <div style="font-size:11px;color:#993556;margin-top:3px">Avg product rating</div>
            </div>
            <div style="background:#FCEBEB;border-radius:12px;padding:14px;cursor:pointer">
                <div style="width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,0.5);display:flex;align-items:center;justify-content:center;margin-bottom:8px">
                    <i class="fa fa-clock-o" style="color:#791F1F"></i>
                </div>
                <div style="font-size:20px;font-weight:700;color:#791F1F"><t t-esc="d.pending_reviews"/></div>
                <div style="font-size:11px;color:#A32D2D;margin-top:3px">Pending reviews</div>
            </div>
        </div>

    </t>
</div>
    `;
}

registry.category("actions").add("marketplace_dashboard_action", MarketplaceDashboard);

MarketplaceDashboard.components = {};
