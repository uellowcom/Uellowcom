/** @odoo-module **/
// Embeds the لمّة يلو dashboard inside the Odoo backend so it keeps the top
// navbar / breadcrumbs instead of opening as a bare standalone page.
import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";

export class LammaDashboardAction extends Component {}
LammaDashboardAction.template = xml`
    <div class="o_lamma_dashboard_wrap" style="position:relative; width:100%; height:calc(100vh - var(--o-navbar-height, 46px)); overflow:hidden;">
        <iframe src="/lamma/dashboard?embed=1"
                title="لوحة تحكّم لمّة يلو"
                style="width:100%; height:100%; border:0; display:block; background:#fff;"/>
    </div>`;

registry.category("actions").add("lamma_dashboard_action", LammaDashboardAction);
