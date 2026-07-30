/** @odoo-module **/
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

// Add a "Print closing" button to the cashier close-register dialog, next to
// the "Sales report" button. It prints the 80mm cashier-closing receipt for
// the current POS session (same report available from the backend session form).
patch(ClosePosPopup.prototype, {
    async printClosingReceipt() {
        return this.report.doAction(
            "uellow_pos_closing.action_report_pos_closing_receipt",
            [this.pos.session.id]
        );
    },
});
