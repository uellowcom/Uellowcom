/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Component, useState, onMounted } from '@odoo/owl';
import { rpc } from '@web/core/network/rpc';

const STATE_COLORS = {
    idle:'#888780', talking:'#534AB7', thinking:'#EF9F27',
    happy:'#1D9E75', excited:'#F5C320', sad:'#E24B4A',
};
const STATE_LABELS = {
    idle:'استراحة', talking:'تتكلم', thinking:'تفكر',
    happy:'سعيدة', excited:'متحمسة', sad:'آسفة',
};
const LEVEL_COLORS = {
    starter:{bg:'#F5F4F2',text:'#888'},
    silver:{bg:'#E8E8E5',text:'#5F5E5A'},
    gold:{bg:'#FAEEDA',text:'#633806'},
    platinum:{bg:'#EEEDFE',text:'#3C3489'},
    elite:{bg:'#E1F5EE',text:'#085041'},
};

export class AnalyticsDashboard extends Component {
    static template = 'uellow_analytics.Dashboard';
    static props = ['*'];

    setup() {
        this.state = useState({ loading: true, period: 'month', data: null, error: null });
        onMounted(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        this.state.error   = null;
        try {
            const data = await rpc('/analytics/dashboard', { period: this.state.period });
            this.state.data    = data;
            this.state.loading = false;
        } catch(e) {
            console.error('Analytics error:', e);
            this.state.error   = 'فشل تحميل البيانات';
            this.state.loading = false;
        }
    }

    async setPeriod(period) {
        this.state.period = period;
        await this.loadData();
    }

    barHeight(val, max) { return Math.max(4, Math.round((val / (max||1)) * 70)); }
    maxVal(arr, key)    { return Math.max(...(arr||[]).map(d => d[key]||0), 1); }
    fmtDate(s)          { const d=new Date(s); return `${d.getDate()}/${d.getMonth()+1}`; }
    stateTotal(dist)    { return Object.values(dist||{}).reduce((a,b)=>a+b,0)||1; }
    statePct(dist, k)   { return Math.round(((dist[k]||0)/this.stateTotal(dist))*100); }
    stateColor(k)       { return STATE_COLORS[k]||'#ccc'; }
    stateLabel(k)       { return STATE_LABELS[k]||k; }
    levelBg(k)          { return (LEVEL_COLORS[k]||{}).bg||'#F5F4F2'; }
    levelText(k)        { return (LEVEL_COLORS[k]||{}).text||'#888'; }
    levelName(k)        { return {starter:'Starter',silver:'Silver',gold:'Gold',platinum:'Platinum',elite:'Elite'}[k]||k; }

    donutSVG(dist) {
        const total = this.stateTotal(dist);
        const entries = Object.entries(dist||{}).filter(([,v])=>v>0);
        if (!entries.length) return `<svg width="80" height="80"><text x="40" y="44" text-anchor="middle" font-size="11" fill="#aaa">لا بيانات</text></svg>`;
        const cx=40,cy=40,r=28,sw=12;
        let angle=-Math.PI/2;
        const paths = entries.map(([key,val]) => {
            const pct=val/total, end=angle+pct*2*Math.PI;
            const x1=cx+r*Math.cos(angle), y1=cy+r*Math.sin(angle);
            const x2=cx+r*Math.cos(end),   y2=cy+r*Math.sin(end);
            const d=`M${x1.toFixed(1)} ${y1.toFixed(1)} A${r} ${r} 0 ${pct>0.5?1:0} 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`;
            angle=end;
            return `<path d="${d}" fill="none" stroke="${STATE_COLORS[key]||'#ccc'}" stroke-width="${sw}" stroke-linecap="round"/>`;
        }).join('');
        return `<svg width="80" height="80" viewBox="0 0 80 80">${paths}<text x="${cx}" y="${cy+4}" text-anchor="middle" font-size="12" font-weight="bold" fill="#1A1A1A">${total}</text></svg>`;
    }
}

registry.category('actions').add('uellow_analytics.dashboard', AnalyticsDashboard);
