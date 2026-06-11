/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, xml } from "@odoo/owl";

class BrainDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, error: null, d: null, t: "" });
        onMounted(() => this.load());
    }
    async load() {
        try {
            this.state.d = await this.orm.call(
                "uellow.brain.dashboard", "get_dashboard_data", []);
            this.state.t = new Date().toLocaleTimeString();
            this.state.loading = false;
        } catch (e) {
            this.state.error = (e && e.message) || "Failed to load";
            this.state.loading = false;
        }
    }
    async recompute() {
        this.state.loading = true;
        try {
            await this.orm.call("product.template",
                "_brain_compute_scores_ui", []);
        } catch (e) { /* ignore */ }
        await this.load();
    }
    openSettings() {
        this.action.doAction("uellow_brain.action_brain_config");
    }
    openTop() {
        this.action.doAction("uellow_brain.action_brain_top_products");
    }
    fmt(n) {
        n = Number(n || 0);
        if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
        if (n >= 1000) return (n / 1000).toFixed(1) + "k";
        return n.toLocaleString();
    }
    // bar height % for a series
    barPct(v, series) {
        const mx = Math.max(1, ...series.map((x) => x.value || 0));
        return Math.round(((v || 0) / mx) * 100);
    }
    // score-distribution bucket height %
    bucketPct(i) {
        const b = this.state.d.score_buckets || [];
        const mx = Math.max(1, ...b);
        return Math.round(((b[i] || 0) / mx) * 100);
    }
    // conic-gradient string for the margin donut
    donut() {
        const m = this.state.d.margin;
        const tot = (m.healthy + m.low + m.below + m.unknown) || 1;
        const h = (m.healthy / tot) * 360;
        const l = (m.low / tot) * 360;
        const b = (m.below / tot) * 360;
        const a = h, c = a + l, e = c + b;
        return `conic-gradient(#16a34a 0 ${a}deg, #f5c320 ${a}deg ${c}deg, ` +
               `#e63946 ${c}deg ${e}deg, #d8d8d8 ${e}deg 360deg)`;
    }
}

BrainDashboard.template = xml`
<div class="brain_dash">
  <t t-if="state.loading">
    <div class="bd_load"><div class="spinner-border text-warning"/><p>Loading Brain…</p></div>
  </t>
  <t t-elif="state.error">
    <div class="alert alert-danger m-4"><t t-esc="state.error"/></div>
  </t>
  <t t-else="">
    <!-- header -->
    <div class="bd_head">
      <div class="bd_logo">🧠</div>
      <div class="bd_htxt">
        <h1><span class="bd_y">Uellow</span> Brain</h1>
        <p>Personalization &amp; Merchandising — cost-driven, margin-guarded</p>
      </div>
      <div class="bd_state" t-att-class="state.d.engine.on ? 'on' : 'off'">
        <t t-esc="state.d.engine.on ? 'ENGINE ON' : 'ENGINE OFF'"/>
        <span> · <t t-esc="state.d.engine.mode"/></span>
      </div>
      <div class="bd_actions">
        <button class="btn btn-sm btn-light" t-on-click="() => this.recompute()">♻️ Recompute</button>
        <button class="btn btn-sm btn-light" t-on-click="() => this.openSettings()">⚙️ Settings</button>
        <span class="bd_upd">↻ <t t-esc="state.t"/></span>
      </div>
    </div>

    <!-- KPI cards -->
    <div class="bd_kpis">
      <div class="kc kc-y"><div class="kl">Avg Best-Match score</div><div class="kv"><t t-esc="state.d.kpis.avg_score"/></div></div>
      <div class="kc"><div class="kl">Published products</div><div class="kv"><t t-esc="this.fmt(state.d.kpis.published)"/></div></div>
      <div class="kc kc-g"><div class="kl">Revenue (30d)</div><div class="kv"><t t-esc="this.fmt(state.d.kpis.revenue_30d)"/></div></div>
      <div class="kc"><div class="kl">Orders (30d)</div><div class="kv"><t t-esc="this.fmt(state.d.kpis.orders_30d)"/></div></div>
      <div class="kc"><div class="kl">AOV (30d)</div><div class="kv"><t t-esc="this.fmt(state.d.kpis.aov)"/></div></div>
      <div class="kc"><div class="kl">Units (30d)</div><div class="kv"><t t-esc="this.fmt(state.d.kpis.units_30d)"/></div></div>
      <div class="kc kc-b"><div class="kl">Open carts</div><div class="kv"><t t-esc="this.fmt(state.d.kpis.open_carts)"/></div><div class="ks"><t t-esc="this.fmt(state.d.kpis.open_cart_value)"/> KD</div></div>
      <div class="kc"><div class="kl">Taste profiles</div><div class="kv"><t t-esc="this.fmt(state.d.kpis.profiles)"/></div></div>
      <div class="kc"><div class="kl">Searches (30d)</div><div class="kv"><t t-esc="this.fmt(state.d.kpis.searches_30d)"/></div></div>
      <div class="kc kc-r"><div class="kl">Zero-result searches</div><div class="kv"><t t-esc="this.fmt(state.d.kpis.zero_res)"/></div></div>
    </div>

    <!-- charts row 1 -->
    <div class="bd_row">
      <div class="bd_card bd_grow">
        <div class="bd_ct">💰 Revenue — last 14 days</div>
        <div class="bd_bars">
          <t t-foreach="state.d.rev_series" t-as="p" t-key="p.label">
            <div class="bar"><div class="bfill" t-attf-style="height:{{ this.barPct(p.value, state.d.rev_series) }}%"/><span class="blab" t-esc="p.label"/></div>
          </t>
          <t t-if="!state.d.rev_series.length"><div class="bd_empty">No sales yet</div></t>
        </div>
      </div>
      <div class="bd_card">
        <div class="bd_ct">🛡️ Margin health</div>
        <div class="bd_donutwrap">
          <div class="bd_donut" t-attf-style="background:{{ this.donut() }}"><div class="bd_donut_c"><t t-esc="state.d.margin.healthy"/></div></div>
          <div class="bd_leg">
            <div><span class="dot" style="background:#16a34a"/> Healthy <b t-esc="state.d.margin.healthy"/></div>
            <div><span class="dot" style="background:#f5c320"/> Low margin <b t-esc="state.d.margin.low"/></div>
            <div><span class="dot" style="background:#e63946"/> Below cost <b t-esc="state.d.margin.below"/></div>
            <div><span class="dot" style="background:#d8d8d8"/> Unknown cost <b t-esc="state.d.margin.unknown"/></div>
          </div>
        </div>
      </div>
    </div>

    <!-- charts row 2 -->
    <div class="bd_row">
      <div class="bd_card">
        <div class="bd_ct">📊 Score distribution</div>
        <div class="bd_bars">
          <t t-foreach="[0,1,2,3,4]" t-as="i" t-key="i">
            <div class="bar"><div class="bfill bg-purple" t-attf-style="height:{{ this.bucketPct(i) }}%"/><span class="blab" t-esc="(i*20)+'-'+((i+1)*20)"/></div>
          </t>
        </div>
      </div>
      <div class="bd_card bd_grow">
        <div class="bd_ct">🗂️ Top eCommerce categories by score</div>
        <div class="bd_hbars">
          <t t-foreach="state.d.top_cats" t-as="c" t-key="c.name">
            <div class="hb"><span class="hbl" t-esc="c.name"/><div class="hbt"><div class="hbf" t-attf-style="width:{{ this.barPct(c.value, state.d.top_cats) }}%"/></div><span class="hbv" t-esc="c.value"/></div>
          </t>
          <t t-if="!state.d.top_cats.length"><div class="bd_empty">No data</div></t>
        </div>
      </div>
    </div>

    <!-- lists row -->
    <div class="bd_row">
      <div class="bd_card bd_grow">
        <div class="bd_ct">🏆 Top products by Brain score <button class="btn btn-sm btn-link" t-on-click="() => this.openTop()">open ›</button></div>
        <table class="bd_tbl">
          <t t-foreach="state.d.top_products" t-as="p" t-key="p.name">
            <tr><td class="nm" t-esc="p.name"/><td t-esc="p.price + ' KD'"/><td class="sc" t-esc="p.score"/></tr>
          </t>
        </table>
      </div>
      <div class="bd_card">
        <div class="bd_ct">🔎 Top searches (30d)</div>
        <div class="bd_hbars">
          <t t-foreach="state.d.top_searches" t-as="s" t-key="s.name">
            <div class="hb"><span class="hbl" t-esc="s.name"/><div class="hbt"><div class="hbf bg-blue" t-attf-style="width:{{ this.barPct(s.value, state.d.top_searches) }}%"/></div><span class="hbv" t-esc="s.value"/></div>
          </t>
          <t t-if="!state.d.top_searches.length"><div class="bd_empty">No searches</div></t>
        </div>
      </div>
    </div>

    <!-- extra KPIs -->
    <div class="bd_kpis">
      <div class="kc kc-g"><div class="kl">Catalogue value</div><div class="kv"><t t-esc="this.fmt(state.d.extra.catalog_value)"/></div></div>
      <div class="kc"><div class="kl">Stock cost value</div><div class="kv"><t t-esc="this.fmt(state.d.extra.stock_cost_value)"/></div></div>
      <div class="kc kc-y"><div class="kl">Scored %</div><div class="kv"><t t-esc="state.d.extra.scored_pct"/>%</div></div>
      <div class="kc"><div class="kl">With image</div><div class="kv"><t t-esc="this.fmt(state.d.extra.with_image)"/></div></div>
      <div class="kc kc-b"><div class="kl">Members</div><div class="kv"><t t-esc="this.fmt(state.d.extra.members)"/></div></div>
      <div class="kc"><div class="kl">Guests</div><div class="kv"><t t-esc="this.fmt(state.d.extra.guests)"/></div></div>
      <div class="kc kc-g"><div class="kl">Active now</div><div class="kv"><t t-esc="this.fmt(state.d.extra.active_now)"/></div></div>
      <div class="kc"><div class="kl">Wishlist items</div><div class="kv"><t t-esc="this.fmt(state.d.extra.wishlist)"/></div></div>
      <div class="kc"><div class="kl">Reviews</div><div class="kv"><t t-esc="this.fmt(state.d.extra.reviews)"/></div><div class="ks">★ <t t-esc="state.d.extra.avg_rating"/></div></div>
      <div class="kc kc-r"><div class="kl">Abandoned 24h</div><div class="kv"><t t-esc="this.fmt(state.d.extra.abandoned_24h)"/></div></div>
      <div class="kc"><div class="kl">Flash live</div><div class="kv"><t t-esc="state.d.extra.flash_active"/></div></div>
      <div class="kc"><div class="kl">Promotions</div><div class="kv"><t t-esc="state.d.extra.promos_active"/></div></div>
      <div class="kc kc-b"><div class="kl">Bundles</div><div class="kv"><t t-esc="state.d.extra.bundles_pub"/></div></div>
      <div class="kc"><div class="kl">Free-ship rules</div><div class="kv"><t t-esc="state.d.extra.freeship_rules"/></div></div>
      <div class="kc kc-y"><div class="kl">Automation rules</div><div class="kv"><t t-esc="state.d.extra.merch_rules"/></div><div class="ks"><t t-esc="state.d.extra.merch_fired_30d"/> fired 30d</div></div>
    </div>

    <!-- charts row 3 -->
    <div class="bd_row">
      <div class="bd_card bd_grow">
        <div class="bd_ct">🧾 Orders — last 14 days</div>
        <div class="bd_bars">
          <t t-foreach="state.d.extra.ord14" t-as="p" t-key="p.label">
            <div class="bar"><div class="bfill bg-blue2" t-attf-style="height:{{ this.barPct(p.value, state.d.extra.ord14) }}%"/><span class="blab" t-esc="p.label"/></div>
          </t>
          <t t-if="!state.d.extra.ord14.length"><div class="bd_empty">No orders</div></t>
        </div>
      </div>
      <div class="bd_card">
        <div class="bd_ct">❤️ Top customer interests</div>
        <div class="bd_hbars">
          <t t-foreach="state.d.extra.taste_int" t-as="c" t-key="c.name">
            <div class="hb"><span class="hbl" t-esc="c.name"/><div class="hbt"><div class="hbf bg-pink" t-attf-style="width:{{ this.barPct(c.value, state.d.extra.taste_int) }}%"/></div><span class="hbv" t-esc="c.value"/></div>
          </t>
          <t t-if="!state.d.extra.taste_int.length"><div class="bd_empty">No taste data yet</div></t>
        </div>
      </div>
    </div>

    <!-- services -->
    <div class="bd_card">
      <div class="bd_ct">🔌 Services</div>
      <div class="bd_chips">
        <t t-foreach="state.d.services" t-as="s" t-key="s.name">
          <span class="bd_chip" t-att-class="s.on ? 'on' : 'off'"><t t-esc="(s.on ? '● ' : '○ ') + s.name"/></span>
        </t>
      </div>
    </div>

    <!-- ALL settings / capabilities -->
    <div class="bd_card">
      <div class="bd_ct">⚙️ All capabilities &amp; options <button class="btn btn-sm btn-link" t-on-click="() => this.openSettings()">edit ›</button></div>
      <div class="bd_cfg">
        <t t-foreach="state.d.config" t-as="g" t-key="g.title">
          <div class="cfg_grp">
            <div class="cfg_t" t-esc="g.title"/>
            <t t-foreach="g.items" t-as="it" t-key="it.k">
              <div class="cfg_row"><span t-esc="it.k"/><b t-esc="it.v"/></div>
            </t>
          </div>
        </t>
      </div>
    </div>
  </t>
</div>`;

registry.category("actions").add("uellow_brain_dashboard", BrainDashboard);
