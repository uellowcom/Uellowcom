/** @odoo-module **/

import PaymentForm from "@payment/js/payment_form";

PaymentForm.include({
    init() {
        this._super(...arguments);
    },
    async _selectPaymentOption(ev) {
        await this._super(...arguments);
        var sale_order_id = Number(document.getElementById('sale_order_id').value);
        var checkedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');
        var paymentMethodCode = checkedRadio.dataset['paymentMethodCode'];
        if (paymentMethodCode == 'cod'){
            var cod_fee_amount = await this.orm.call(
                'sale.order',
                'get_cod_fee_amount_str',
                [sale_order_id],
            );
        };
        document.getElementById('cod_fee_amount').innerText = cod_fee_amount;
    },
    async _submitForm(ev) {
        await this._super(...arguments);
    },
});
