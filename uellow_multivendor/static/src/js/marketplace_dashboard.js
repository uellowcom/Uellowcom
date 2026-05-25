/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState, xml } from "@odoo/owl";

class MarketplaceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            stats: {
                vendor_active: 0,
                vendor_pending: 0,
                vendor_total: 0,
                order_today: 0,
                revenue_today: 0.0,
                commission_today: 0.0,
                flash_active: 0,
                fraud_open: 0,
                loyalty_accounts: 0,
                abandoned_pending: 0,
            }
        });
        onMounted(() => this.loadStats());
    }

    async loadStats() {
        try {
            // Vendors
            const active = await this.orm.searchCount("uellow.vendor", [["state","=","active"]]);
            const pending = await this.orm.searchCount("uellow.vendor", [["state","=","pending"]]);
            const total = await this.orm.searchCount("uellow.vendor", []);

            // Orders today
            const today = new Date().toISOString().split('T')[0];
            const orders = await this.orm.searchCount("sale.order", [
                ["state","in",["sale","done"]],
                ["date_order",">=", today + " 00:00:00"],
            ]);

            // Flash sales active
            let flash = 0;
            try {
                flash = await this.orm.searchCount("uellow.flash.sale", [["state","=","active"]]);
            } catch(e) {}

            // Fraud cases open
            let fraud = 0;
            try {
                fraud = await this.orm.searchCount("uellow.fraud.case", [["state","in",["open","reviewing"]]]);
            } catch(e) {}

            // Loyalty accounts
            let loyalty = 0;
            try {
                loyalty = await this.orm.searchCount("uellow.loyalty.account", []);
            } catch(e) {}

            // Abandoned carts pending
            let abandoned = 0;
            try {
                abandoned = await this.orm.searchCount("uellow.abandoned.cart", [["state","=","pending"]]);
            } catch(e) {}

            this.state.stats = {
                vendor_active: active,
                vendor_pending: pending,
                vendor_total: total,
                order_today: orders,
                flash_active: flash,
                fraud_open: fraud,
                loyalty_accounts: loyalty,
                abandoned_pending: abandoned,
            };
        } catch(e) {
            console.error("Dashboard stats error:", e);
        }
        this.state.loading = false;
    }

    openVendors(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Vendors",
            res_model: "uellow.vendor",
            view_mode: "list,form",
            domain: state ? [["state","=",state]] : [],
        });
    }

    openAction(model, domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: model,
            view_mode: "list,form",
            domain: domain || [],
        });
    }
}

MarketplaceDashboard.template = xml`
<div class="o_marketplace_dashboard" style="padding:24px;background:#f8f9fa;min-height:100vh">

  <!-- Header -->
  <div style="margin-bottom:24px">
    <h2 style="font-weight:700;margin:0;color:#1A7A6E">
      <i class="fa fa-store me-2"/>Marketplace Dashboard
    </h2>
    <p style="color:#666;margin:4px 0 0">Uellow Multi-Vendor Platform</p>
  </div>

  <t t-if="state.loading">
    <div class="text-center py-5">
      <i class="fa fa-spinner fa-spin fa-2x text-muted"/>
      <p class="text-muted mt-2">Loading stats...</p>
    </div>
  </t>

  <t t-else="">

    <!-- Row 1: Vendor Stats -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px">

      <div class="o_dashboard_card" style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;border-left:4px solid #1A7A6E"
           t-on-click="() => this.openVendors('active')">
        <div style="font-size:32px;font-weight:700;color:#1A7A6E"><t t-esc="state.stats.vendor_active"/></div>
        <div style="color:#666;font-size:13px;margin-top:4px"><i class="fa fa-check-circle me-1"/>Active Vendors</div>
      </div>

      <div class="o_dashboard_card" style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;border-left:4px solid #f59e0b"
           t-on-click="() => this.openVendors('pending')">
        <div style="font-size:32px;font-weight:700;color:#f59e0b"><t t-esc="state.stats.vendor_pending"/></div>
        <div style="color:#666;font-size:13px;margin-top:4px"><i class="fa fa-clock me-1"/>Pending Approval</div>
      </div>

      <div class="o_dashboard_card" style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;border-left:4px solid #6366f1"
           t-on-click="() => this.openVendors(false)">
        <div style="font-size:32px;font-weight:700;color:#6366f1"><t t-esc="state.stats.vendor_total"/></div>
        <div style="color:#666;font-size:13px;margin-top:4px"><i class="fa fa-users me-1"/>Total Vendors</div>
      </div>

      <div class="o_dashboard_card" style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;border-left:4px solid #10b981"
           t-on-click="() => this.openAction('sale.order',[['state','in',['sale','done']]],'Orders Today')">
        <div style="font-size:32px;font-weight:700;color:#10b981"><t t-esc="state.stats.order_today"/></div>
        <div style="color:#666;font-size:13px;margin-top:4px"><i class="fa fa-shopping-cart me-1"/>Orders Today</div>
      </div>

    </div>

    <!-- Row 2: Operations -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px">

      <div class="o_dashboard_card" style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;border-left:4px solid #ef4444"
           t-on-click="() => this.openAction('uellow.flash.sale',[['state','=','active']],'Active Flash Sales')">
        <div style="font-size:32px;font-weight:700;color:#ef4444"><t t-esc="state.stats.flash_active"/></div>
        <div style="color:#666;font-size:13px;margin-top:4px"><i class="fa fa-bolt me-1"/>Flash Sales Active</div>
      </div>

      <div class="o_dashboard_card" style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;border-left:4px solid #dc2626"
           t-on-click="() => this.openAction('uellow.fraud.case',[['state','in',['open','reviewing']]],'Open Fraud Cases')">
        <div style="font-size:32px;font-weight:700;color:#dc2626"><t t-esc="state.stats.fraud_open"/></div>
        <div style="color:#666;font-size:13px;margin-top:4px"><i class="fa fa-shield-alt me-1"/>Fraud Cases Open</div>
      </div>

      <div class="o_dashboard_card" style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;border-left:4px solid #8b5cf6"
           t-on-click="() => this.openAction('uellow.loyalty.account',[],'Loyalty Accounts')">
        <div style="font-size:32px;font-weight:700;color:#8b5cf6"><t t-esc="state.stats.loyalty_accounts"/></div>
        <div style="color:#666;font-size:13px;margin-top:4px"><i class="fa fa-star me-1"/>Loyalty Members</div>
      </div>

      <div class="o_dashboard_card" style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);cursor:pointer;border-left:4px solid #f97316"
           t-on-click="() => this.openAction('uellow.abandoned.cart',[['state','=','pending']],'Abandoned Carts')">
        <div style="font-size:32px;font-weight:700;color:#f97316"><t t-esc="state.stats.abandoned_pending"/></div>
        <div style="color:#666;font-size:13px;margin-top:4px"><i class="fa fa-shopping-basket me-1"/>Abandoned Carts</div>
      </div>

    </div>

    <!-- Quick Actions -->
    <div style="background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
      <h5 style="font-weight:600;margin-bottom:16px;color:#374151">Quick Actions</h5>
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <button class="btn btn-primary btn-sm" t-on-click="() => this.openVendors('pending')">
          <i class="fa fa-user-check me-1"/>Review Pending Vendors
        </button>
        <button class="btn btn-success btn-sm" t-on-click="() => this.openAction('uellow.vendor.commission',[['state','=','released']],'Released Commissions')">
          <i class="fa fa-money-bill me-1"/>Process Payouts
        </button>
        <button class="btn btn-warning btn-sm" t-on-click="() => this.openAction('uellow.fraud.case',[['state','=','open']],'Open Fraud Cases')">
          <i class="fa fa-exclamation-triangle me-1"/>Review Fraud Cases
        </button>
        <button class="btn btn-info btn-sm" t-on-click="() => this.openAction('uellow.flash.sale',[],'Flash Sales')">
          <i class="fa fa-bolt me-1"/>Manage Flash Sales
        </button>
      </div>
    </div>

  </t>
</div>
`;

registry.category("actions").add("marketplace_dashboard", MarketplaceDashboard);
