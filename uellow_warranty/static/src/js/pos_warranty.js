/** @odoo-module **/
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    async printWarrantyCertificate() {
        const order = this.currentOrder;
        const orderId = order && order.id;
        if (!orderId || typeof orderId !== "number") {
            this.env.services.notification.add("Warranty available after the order is saved", {
                type: "warning",
            });
            return;
        }
        const cards = await this.env.services.orm.searchRead(
            "uellow.warranty.card",
            [["pos_order_id", "=", orderId]],
            ["id"]
        );
        if (!cards.length) {
            this.env.services.notification.add("No warranty for this order", {
                type: "warning",
            });
            return;
        }
        const ids = cards.map((c) => c.id).join(",");
        window.open(`/report/pdf/uellow_warranty.warranty_certificate/${ids}`, "_blank");
    },
});
