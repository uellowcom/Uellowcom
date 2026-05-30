// =============================================================================
// CheckoutScreen — native, NOT a webview. Three steps: address, shipping,
// payment, summary, place order.
// Wires to /api/mobile/v2/orders/checkout/summary + /confirm.
// =============================================================================
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';

class CheckoutScreen extends StatefulWidget {
  const CheckoutScreen({super.key});
  @override
  State<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends State<CheckoutScreen> {
  int _step = 1; // 0 = done, 1 = current, 2 = future (visual only)
  int _carrierIdx = 0;
  int _paymentIdx = 0;
  Future<UellowCheckoutSummary>? _summary;

  @override
  void initState() {
    super.initState();
    _summary = UellowApi.instance.orders.checkoutSummary();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      appBar: AppBar(
        leading: const BackButton(color: UellowColors.darkBrown),
        title: const Text('Checkout', style: UT.h1),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(8),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 0, 18, 8),
            child: Row(children: [
              for (var i = 0; i < 3; i++) Padding(
                padding: const EdgeInsets.only(right: 4),
                child: SizedBox(width: 90, child: _stepBar(i)),
              ),
            ]),
          ),
        ),
      ),
      body: FutureBuilder<UellowCheckoutSummary>(
        future: _summary,
        builder: (_, snap) {
          // Even before backend resolves, show structure with placeholders
          return _buildContent(snap.data);
        },
      ),
      bottomNavigationBar: _PlaceOrderBar(
        onPress: _placeOrder, total: 38.300,
      ),
    );
  }

  Widget _stepBar(int i) {
    Color c;
    if (i < _step) c = UellowColors.success;
    else if (i == _step) c = UellowColors.yellow;
    else c = UellowColors.border;
    return Container(
      height: 4,
      decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(999)),
    );
  }

  Widget _buildContent(UellowCheckoutSummary? sum) {
    return ListView(padding: const EdgeInsets.symmetric(vertical: 0), children: [
      _section(num: 1, title: 'DELIVERY ADDRESS', child: _AddressCard()),
      _section(num: 2, title: 'SHIPPING METHOD', child: Column(children: [
        for (var i = 0; i < _shippingOpts.length; i++)
          _ShipOpt(opt: _shippingOpts[i], on: _carrierIdx == i,
              onTap: () => setState(() => _carrierIdx = i)),
      ])),
      _section(num: 3, title: 'PAYMENT METHOD', child: _PaymentGrid(
        selected: _paymentIdx, onChange: (i) => setState(() => _paymentIdx = i),
      )),
      _section(num: null, title: 'ORDER SUMMARY', child: _SumBlock(summary: sum)),
      const SizedBox(height: 100),
    ]);
  }

  Widget _section({required int? num, required String title, required Widget child}) {
    return Container(
      color: Colors.white,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          if (num != null) Container(
            width: 22, height: 22, alignment: Alignment.center,
            decoration: const BoxDecoration(
              color: UellowColors.yellowLight, shape: BoxShape.circle,
            ),
            child: Text('$num', style: const TextStyle(
                color: UellowColors.darkBrown, fontWeight: FontWeight.w900, fontSize: 12)),
          ),
          if (num != null) const SizedBox(width: 8),
          Text(title, style: const TextStyle(
              fontSize: 13, fontWeight: FontWeight.w800, color: UellowColors.darkBrown,
              letterSpacing: 0.5)),
        ]),
        const SizedBox(height: 12),
        child,
      ]),
    );
  }

  Future<void> _placeOrder() async {
    setState(() => _step = 2);
    try {
      final result = await UellowApi.instance.orders.checkoutConfirm(
        carrierId: _carrierIdx + 1,
        paymentMethod: _paymentIdx == 3 ? 'cod' : 'card',
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Order ${result.orderName} placed!')),
      );
    } on UellowApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }
}

// ─── Shipping opts (demo data) ────────────────────────────────────

class _ShipOptModel {
  final String label, meta, price; final IconData icon; final Color iconColor;
  final bool isFree;
  const _ShipOptModel(this.label, this.meta, this.price, this.icon, this.iconColor, {this.isFree = false});
}
const _shippingOpts = [
  _ShipOptModel('Same-day delivery', 'Order before 2 PM · Arrives today', '2.000 KD',
      Icons.bolt, UellowColors.darkBrown),
  _ShipOptModel('Standard delivery', '1-3 business days', 'Free',
      Icons.local_shipping_outlined, UellowColors.muted, isFree: true),
  _ShipOptModel('Pickup from store', 'Uellow Salmiya branch · Ready in 2h', 'Free',
      Icons.storefront_outlined, UellowColors.muted, isFree: true),
];

class _ShipOpt extends StatelessWidget {
  const _ShipOpt({required this.opt, required this.on, required this.onTap});
  final _ShipOptModel opt;
  final bool on;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: EdgeInsets.all(on ? 11 : 12),
        decoration: BoxDecoration(
          color: on ? UellowColors.yellowFaint : Colors.white,
          border: Border.all(
            color: on ? UellowColors.yellow : UellowColors.border,
            width: on ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(children: [
          Container(
            width: 20, height: 20,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: on ? UellowColors.yellow : const Color(0xFFE5D8B2), width: 2,
              ),
              gradient: on ? const RadialGradient(
                colors: [UellowColors.yellow, Colors.transparent], stops: [0.4, 0.5],
              ) : null,
            ),
          ),
          const SizedBox(width: 12),
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: on ? UellowColors.yellowLight : UellowColors.border,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(opt.icon, size: 18,
                color: on ? UellowColors.darkBrown : UellowColors.muted),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(opt.label, style: const TextStyle(
                fontSize: 13, fontWeight: FontWeight.w700, color: UellowColors.ink)),
            const SizedBox(height: 2),
            Text(opt.meta, style: const TextStyle(fontSize: 11, color: UellowColors.muted)),
          ])),
          Text(opt.price, style: TextStyle(
            fontSize: 14, fontWeight: FontWeight.w800,
            color: opt.isFree ? UellowColors.successDk : UellowColors.darkBrown,
          )),
        ]),
      ),
    );
  }
}

// ─── Payment grid ────────────────────────────────────────────────

class _PaymentGrid extends StatelessWidget {
  const _PaymentGrid({required this.selected, required this.onChange});
  final int selected;
  final ValueChanged<int> onChange;
  static const _opts = [
    (Icons.credit_card, 'Credit / Debit card'),
    (Icons.account_balance_outlined, 'KNET'),
    (Icons.phone_iphone_outlined, 'Apple Pay'),
    (Icons.payments_outlined, 'Cash on delivery'),
  ];
  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2, crossAxisSpacing: 8, mainAxisSpacing: 8, childAspectRatio: 1.9,
      ),
      itemCount: _opts.length,
      itemBuilder: (_, i) {
        final on = i == selected;
        final (icon, label) = _opts[i];
        return GestureDetector(
          onTap: () => onChange(i),
          child: Container(
            decoration: BoxDecoration(
              color: on ? UellowColors.yellowFaint : Colors.white,
              border: Border.all(
                color: on ? UellowColors.yellow : UellowColors.border,
                width: on ? 2 : 1,
              ),
              borderRadius: BorderRadius.circular(12),
            ),
            alignment: Alignment.center,
            padding: const EdgeInsets.all(10),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(icon, size: 22, color: on ? UellowColors.darkBrown : UellowColors.muted),
              const SizedBox(height: 6),
              Text(label, textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700,
                      color: on ? UellowColors.darkBrown : UellowColors.text)),
            ]),
          ),
        );
      },
    );
  }
}

// ─── Address card (demo data — wire to /addresses/list when available) ─

class _AddressCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: UellowColors.yellowFaint,
        border: Border.all(color: UellowColors.yellow, width: 2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Padding(
          padding: EdgeInsets.only(top: 2),
          child: Icon(Icons.location_on_outlined, size: 20, color: UellowColors.warn),
        ),
        const SizedBox(width: 10),
        const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Ali Mohammed', style: TextStyle(
              fontWeight: FontWeight.w800, fontSize: 13, color: UellowColors.ink)),
          SizedBox(height: 4),
          Text('Block 5, Street 12, House 47\nHawalli, Kuwait · +965 9999 0000',
              style: TextStyle(fontSize: 12, color: UellowColors.text, height: 1.5)),
        ])),
        const Text('Change ›', style: TextStyle(
            fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.text)),
      ]),
    );
  }
}

// ─── Summary block ────────────────────────────────────────────────

class _SumBlock extends StatelessWidget {
  const _SumBlock({this.summary});
  final UellowCheckoutSummary? summary;
  @override
  Widget build(BuildContext context) {
    final t = summary?.cart.totals;
    return Column(children: [
      _r('3 items', t?.subtotal.format() ?? '38.300 KD'),
      _r('Delivery (Same-day)', '2.000 KD'),
      _r('SAVE15 coupon', '− 1.500 KD', success: true),
      _r('Loyalty (-150 pts)', '− 0.500 KD', success: true),
      const Divider(height: 24),
      Row(children: [
        const Expanded(child: Text('You pay', style: TextStyle(
            fontWeight: FontWeight.w900, fontSize: 16, color: UellowColors.darkBrown))),
        Text(t?.total.format() ?? '38.300 KD', style: const TextStyle(
            fontWeight: FontWeight.w900, fontSize: 18, color: UellowColors.darkBrown)),
      ]),
      const SizedBox(height: 12),
      Container(
        padding: const EdgeInsets.all(12),
        decoration: const BoxDecoration(
          color: UellowColors.yellowSoft,
          borderRadius: BorderRadius.all(Radius.circular(10)),
        ),
        child: const Row(children: [
          Icon(Icons.chat_bubble_outline, size: 16, color: UellowColors.darkBrown),
          SizedBox(width: 8),
          Expanded(child: Text.rich(TextSpan(style: TextStyle(
              fontSize: 12, color: UellowColors.text), children: [
            TextSpan(text: 'Delivery instructions ',
                style: TextStyle(fontWeight: FontWeight.w800, color: UellowColors.darkBrown)),
            TextSpan(text: '— Leave at door · Call when arrived'),
          ]))),
        ]),
      ),
    ]);
  }

  Widget _r(String l, String v, {bool success = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Expanded(child: Text(l, style: const TextStyle(
            fontSize: 13, color: UellowColors.text))),
        Text(v, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700,
            color: success ? UellowColors.successDk : UellowColors.text)),
      ]),
    );
  }
}

// ─── Place order bar (sticky) ─────────────────────────────────────

class _PlaceOrderBar extends StatelessWidget {
  const _PlaceOrderBar({required this.onPress, required this.total});
  final VoidCallback onPress;
  final double total;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 18),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: UellowColors.border)),
      ),
      child: SafeArea(
        top: false,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          SizedBox(width: double.infinity, child: ElevatedButton(
            onPressed: onPress,
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.all(Radius.circular(14))),
            ),
            child: Text('Place order · ${total.toStringAsFixed(3)} KD',
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900)),
          )),
          const SizedBox(height: 8),
          const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(Icons.lock_outline, size: 12, color: UellowColors.muted),
            SizedBox(width: 4),
            Text('Secure checkout · Your data is encrypted',
                style: TextStyle(fontSize: 11, color: UellowColors.muted)),
          ]),
        ]),
      ),
    );
  }
}
