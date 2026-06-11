/** @odoo-module **/
/*
 * Taly POS payment terminal (v2.2.27)
 * The cashier selects "Taly", the POS opens an in-store checkout session;
 * Taly SMSes the customer a secure payment link (15 min). The POS then polls
 * the order status and validates the line once the customer pays (CONFIRMED).
 */
import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const POLL_INTERVAL = 4000; // 4s
const MAX_WAIT_MS = 15 * 60 * 1000; // SMS link validity = 15 min

export class PaymentTaly extends PaymentInterface {
    async send_payment_request(uuid) {
        await super.send_payment_request(...arguments);
        const order = this.pos.get_order();
        const line = order && order.get_selected_paymentline();
        if (!line) {
            return false;
        }
        const partner = order.get_partner && order.get_partner();
        const phone = partner && (partner.phone || partner.mobile);
        if (!partner || !phone) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Taly"),
                body: _t(
                    "Select a customer who has a phone number first — Taly sends them an SMS payment link."
                ),
            });
            line.set_payment_status("retry");
            return false;
        }

        // Unique merchant order id for this attempt.
        const reference =
            order.name.replace(/\s/g, "").replaceAll("-", "").toUpperCase() +
            "T" +
            Math.floor(Date.now() / 1000);
        this._merchantOrderId = reference;

        const nameParts = (partner.name || "Customer").trim().split(" ");
        const payload = {
            reference: reference,
            amount: line.get_amount ? line.get_amount() : line.amount,
            currency: (this.pos.currency && this.pos.currency.name) || "KWD",
            language: "ar",
            first_name: nameParts[0] || "Customer",
            last_name: nameParts.slice(1).join(" ") || ".",
            email: partner.email || "",
            phone: phone,
        };

        line.set_payment_status("waiting");
        let res;
        try {
            res = await this.pos.data.silentCall(
                "pos.payment.method",
                "taly_pos_create_session",
                [[this.payment_method_id.id], payload]
            );
        } catch (e) {
            res = { error: (e && e.message) || String(e) };
        }
        if (!res || res.error) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Taly"),
                body: (res && res.error) || _t("Failed to start the Taly session."),
            });
            line.set_payment_status("retry");
            return false;
        }

        this._paymentLink = res.securePaymentLink;
        // Let the cashier read the link to the customer / show a QR if needed.
        this.env.services.dialog.add(AlertDialog, {
            title: _t("Taly — SMS sent"),
            body: _t(
                "A payment link was sent by SMS to %s. Ask the customer to open it and complete the installment plan. Waiting for confirmation…",
                phone
            ),
        });
        line.set_payment_status("waitingCard");
        return await this._poll(reference);
    }

    _poll(reference) {
        const start = Date.now();
        return new Promise((resolve) => {
            const tick = async () => {
                const line = this.pos.get_order() && this.pos.get_order().get_selected_paymentline();
                if (!line || line.get_payment_status() === "retry") {
                    resolve(false);
                    return;
                }
                if (Date.now() - start > MAX_WAIT_MS) {
                    line.set_payment_status("retry");
                    resolve(false);
                    return;
                }
                let data;
                try {
                    data = await this.pos.data.silentCall(
                        "pos.payment.method",
                        "taly_pos_poll",
                        [[this.payment_method_id.id], reference]
                    );
                } catch (e) {
                    data = { state: "" };
                }
                if (data && data.state === "done") {
                    line.transaction_id = reference;
                    if (line.set_receipt_info) {
                        line.set_receipt_info(_t("Paid via Taly installments"));
                    }
                    resolve(true);
                    return;
                }
                if (data && data.state === "cancel") {
                    line.set_payment_status("retry");
                    resolve(false);
                    return;
                }
                this.pollTimeout = setTimeout(tick, POLL_INTERVAL);
            };
            tick();
        });
    }

    async send_payment_cancel(order, uuid) {
        await super.send_payment_cancel(...arguments);
        clearTimeout(this.pollTimeout);
        const line = this.pos.get_order() && this.pos.get_order().get_selected_paymentline();
        if (line) {
            line.set_payment_status("retry");
        }
        return true;
    }

    close() {
        clearTimeout(this.pollTimeout);
    }
}

register_payment_method("taly", PaymentTaly);
