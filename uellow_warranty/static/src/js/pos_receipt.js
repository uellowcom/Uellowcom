/** @odoo-module **/
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

// Repoint the receipt component to the Uellow bilingual template.
OrderReceipt.template = "uellow_warranty.OrderReceipt";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const data = super.export_for_printing(...arguments);
        // Attach bilingual product names (independent of POS language).
        const sorted = this.getSortedOrderlines();
        if (Array.isArray(data.orderlines)) {
            data.orderlines = data.orderlines.map((dl, i) => {
                const pl = sorted[i];
                const prod = pl && pl.product_id;
                return Object.assign({}, dl, {
                    uNameEn: (prod && prod.pos_name_en) || dl.productName,
                    uNameAr: (prod && prod.pos_name_ar) || "",
                });
            });
        }
        const c = this.company || {};
        const p = this.partner_id;
        data.uReceipt = {
            company: {
                id: c.id,
                name: c.name || "",
                nameAr: c.uellow_name_ar || "",
                street: c.street || "",
                city: c.city || "",
                phone: c.phone || "",
                email: c.email || "",
                website: c.website || "",
            },
            partner: p
                ? {
                      name: p.name || "",
                      street: p.street || "",
                      city: p.city || "",
                      phone: p.phone || "",
                      email: p.email || "",
                  }
                : null,
            register: (this.config && this.config.name) || "",
            showWarranty: !!(this.config && this.config.uellow_receipt_warranty),
            warrantyNote: (this.config && this.config.uellow_receipt_warranty_note) || "",
        };
        return data;
    },
});
