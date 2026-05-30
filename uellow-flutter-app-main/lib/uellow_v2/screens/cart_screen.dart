// =============================================================================
// CartScreen — list cart lines + delivery progress + coupon + totals + CTA.
// Pulls live data from /api/mobile/v2/cart. Supports guest cart (token in
// X-Cart-Token header is auto-managed by UellowApi).
// =============================================================================
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';

class CartScreen extends StatefulWidget {
  const CartScreen({super.key});
  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  late Future<UellowCart> _future;
  final _couponCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _future = UellowApi.instance.cart.get();
  }

  Future<void> _reload() async {
    setState(() => _future = UellowApi.instance.cart.get());
    await _future;
  }

  Future<void> _updateLine(int lineId, int qty) async {
    try {
      final c = await UellowApi.instance.cart.update(lineId: lineId, qty: qty);
      setState(() => _future = Future.value(c));
    } on UellowApiException catch (e) {
      _snack(e.message);
    }
  }

  Future<void> _remove(int lineId) async {
    final c = await UellowApi.instance.cart.remove(lineId);
    setState(() => _future = Future.value(c));
  }

  Future<void> _applyCoupon() async {
    if (_couponCtrl.text.trim().isEmpty) return;
    try {
      final c = await UellowApi.instance.cart.applyCoupon(_couponCtrl.text.trim());
      _couponCtrl.clear();
      setState(() => _future = Future.value(c));
    } on UellowApiException catch (e) {
      _snack(e.message);
    }
  }

  void _snack(String msg) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(msg)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: FutureBuilder<UellowCart>(
        future: _future,
        builder: (_, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator(color: UellowColors.darkBrown));
          }
          if (snap.hasError) return _ErrorPane(message: snap.error.toString(), onRetry: _reload);
          final cart = snap.data!;
          if (cart.lineCount == 0) return _EmptyCart();
          return _buildContent(cart);
        },
      ),
      bottomNavigationBar: FutureBuilder<UellowCart>(
        future: _future,
        builder: (_, snap) {
          if (snap.connectionState != ConnectionState.done || snap.hasError) {
            return const SizedBox.shrink();
          }
          final c = snap.data!;
          if (c.lineCount == 0) return const SizedBox.shrink();
          return _CheckoutCta(total: c.totals.total);
        },
      ),
    );
  }

  Widget _buildContent(UellowCart cart) {
    return CustomScrollView(slivers: [
      SliverToBoxAdapter(child: _Header(lineCount: cart.lineCount)),
      SliverList.builder(
        itemCount: cart.lines.length,
        itemBuilder: (_, i) => _LineCard(
          line: cart.lines[i],
          onUpdate: _updateLine, onRemove: _remove,
        ),
      ),
      const SliverToBoxAdapter(child: _DeliveryBar()),
      SliverToBoxAdapter(child: _CouponRow(
        controller: _couponCtrl, onApply: _applyCoupon,
      )),
      if (cart.coupons.isNotEmpty)
        SliverToBoxAdapter(child: _AppliedCoupon(code: cart.coupons.first)),
      SliverToBoxAdapter(child: _Totals(totals: cart.totals)),
      const SliverToBoxAdapter(child: SizedBox(height: 110)),
    ]);
  }
}

// ─── Sub-widgets ───────────────────────────────────────────────────

class _Header extends StatelessWidget {
  const _Header({required this.lineCount});
  final int lineCount;
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('My Cart', style: UT.h1),
        const SizedBox(height: 2),
        Text('$lineCount items · ready to checkout', style: UT.small),
      ]),
    );
  }
}

class _LineCard extends StatelessWidget {
  const _LineCard({required this.line, required this.onUpdate, required this.onRemove});
  final UellowCartLine line;
  final void Function(int, int) onUpdate;
  final void Function(int) onRemove;
  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
        boxShadow: [BoxShadow(color: Color(0x0D000000), blurRadius: 4, offset: Offset(0, 1))],
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        ClipRRect(
          borderRadius: const BorderRadius.all(Radius.circular(10)),
          child: CachedNetworkImage(
            imageUrl: line.image, width: 84, height: 84, fit: BoxFit.cover,
            placeholder: (_, __) => Container(color: UellowColors.border, width: 84, height: 84),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(line.name.current(lang), maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13, height: 1.4, color: UellowColors.ink)),
          const SizedBox(height: 8),
          Row(children: [
            Text(line.total.format(), style: const TextStyle(
                fontSize: 15, fontWeight: FontWeight.w900, color: UellowColors.darkBrown)),
            const Spacer(),
            _QtyBox(qty: line.qty.toInt(), onChange: (n) => onUpdate(line.id, n)),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            const Icon(Icons.favorite_border, size: 12, color: UellowColors.muted),
            const SizedBox(width: 4),
            const Text('Save for later', style: UT.small),
            const SizedBox(width: 14),
            GestureDetector(
              onTap: () => onRemove(line.id),
              child: const Text('Remove', style: TextStyle(
                  fontSize: 11, color: UellowColors.danger, fontWeight: FontWeight.w700)),
            ),
          ]),
        ])),
      ]),
    );
  }
}

class _QtyBox extends StatelessWidget {
  const _QtyBox({required this.qty, required this.onChange});
  final int qty;
  final ValueChanged<int> onChange;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: const BoxDecoration(
        color: UellowColors.border,
        borderRadius: BorderRadius.all(Radius.circular(10)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        _btn('−', () => qty > 1 ? onChange(qty - 1) : null),
        SizedBox(width: 24, child: Text('$qty',
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w800))),
        _btn('+', () => onChange(qty + 1)),
      ]),
    );
  }

  Widget _btn(String s, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 28, height: 28, alignment: Alignment.center,
        decoration: const BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.all(Radius.circular(6)),
        ),
        child: Text(s, style: const TextStyle(
            color: UellowColors.darkBrown, fontWeight: FontWeight.w900, fontSize: 14)),
      ),
    );
  }
}

class _DeliveryBar extends StatelessWidget {
  const _DeliveryBar();
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        color: UellowColors.yellowSoft,
        borderRadius: BorderRadius.all(Radius.circular(12)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text.rich(TextSpan(
          style: TextStyle(fontSize: 12, color: UellowColors.text), children: [
            TextSpan(text: 'Add '),
            TextSpan(text: 'KD 6.6', style: TextStyle(
                color: UellowColors.darkBrown, fontWeight: FontWeight.w800)),
            TextSpan(text: ' more for '),
            TextSpan(text: 'FREE delivery', style: TextStyle(
                color: UellowColors.darkBrown, fontWeight: FontWeight.w800)),
          ],
        )),
        const SizedBox(height: 6),
        Container(
          height: 6,
          decoration: BoxDecoration(color: Colors.white,
              borderRadius: BorderRadius.circular(999)),
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft, widthFactor: 0.67,
            child: const DecoratedBox(decoration: BoxDecoration(
              gradient: LinearGradient(colors: [UellowColors.yellowLight, UellowColors.yellow]),
              borderRadius: BorderRadius.all(Radius.circular(999)),
            )),
          ),
        ),
      ]),
    );
  }
}

class _CouponRow extends StatelessWidget {
  const _CouponRow({required this.controller, required this.onApply});
  final TextEditingController controller;
  final VoidCallback onApply;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 0),
      child: Row(children: [
        Expanded(child: TextField(
          controller: controller,
          decoration: InputDecoration(
            hintText: 'Got a promo code?',
            hintStyle: const TextStyle(color: UellowColors.muted),
            fillColor: Colors.white,
            filled: true,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Color(0xFFD6C79A), style: BorderStyle.solid),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Color(0xFFD6C79A)),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          ),
        )),
        const SizedBox(width: 8),
        ElevatedButton(
          onPressed: onApply,
          style: ElevatedButton.styleFrom(
            backgroundColor: UellowColors.yellowLight,
            foregroundColor: UellowColors.darkBrown,
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          ),
          child: const Text('Apply', style: TextStyle(fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }
}

class _AppliedCoupon extends StatelessWidget {
  const _AppliedCoupon({required this.code});
  final String code;
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: UellowColors.yellowSoft,
        border: Border.all(color: UellowColors.yellow, style: BorderStyle.solid, width: 1),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: const BoxDecoration(
            color: UellowColors.yellowLight,
            borderRadius: BorderRadius.all(Radius.circular(4)),
          ),
          child: Text(code, style: const TextStyle(
              color: UellowColors.darkBrown, fontWeight: FontWeight.w800, fontSize: 11)),
        ),
        const SizedBox(width: 8),
        const Expanded(child: Text('Applied — you saved 1.500 KD',
            style: TextStyle(fontSize: 12, color: UellowColors.text))),
        const Icon(Icons.close, size: 18, color: UellowColors.danger),
      ]),
    );
  }
}

class _Totals extends StatelessWidget {
  const _Totals({required this.totals});
  final UellowCartTotals totals;
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 14),
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 18),
      color: Colors.white,
      child: Column(children: [
        _row('Subtotal', totals.subtotal.format()),
        _row('Delivery', totals.shipping.amount == 0 ? 'FREE' : totals.shipping.format(),
            valueColor: totals.shipping.amount == 0 ? UellowColors.successDk : UellowColors.text),
        if (totals.discount.amount != 0)
          _row('Discount', '− ${totals.discount.format()}', valueColor: UellowColors.successDk),
        const Divider(height: 24),
        _row('Total', totals.total.format(), big: true),
      ]),
    );
  }

  Widget _row(String label, String value, {Color? valueColor, bool big = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Expanded(child: Text(label, style: big
            ? const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: UellowColors.darkBrown)
            : UT.body)),
        Text(value, style: big
            ? const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: UellowColors.darkBrown)
            : TextStyle(color: valueColor ?? UellowColors.text,
                fontWeight: FontWeight.w700, fontSize: 13)),
      ]),
    );
  }
}

class _CheckoutCta extends StatelessWidget {
  const _CheckoutCta({required this.total});
  final UellowMoney total;
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
        child: SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: () {},
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.all(Radius.circular(14))),
            ),
            child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text('Checkout · ${total.format()}',
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900)),
              const Icon(Icons.arrow_forward, size: 18),
            ]),
          ),
        ),
      ),
    );
  }
}

class _EmptyCart extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ListView(children: [
      const SizedBox(height: 100),
      const Center(child: Icon(Icons.shopping_cart_outlined,
          size: 80, color: UellowColors.muted)),
      const SizedBox(height: 18),
      const Center(child: Text('Your cart is empty', style: UT.h2)),
      const SizedBox(height: 6),
      const Center(child: Text('Browse the latest deals and add to cart',
          style: UT.body)),
      const SizedBox(height: 20),
      Center(child: ElevatedButton(
        onPressed: () => Navigator.maybePop(context),
        child: const Text('Continue shopping'),
      )),
    ]);
  }
}

class _ErrorPane extends StatelessWidget {
  const _ErrorPane({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) {
    return Center(child: Padding(
      padding: const EdgeInsets.all(30),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.cloud_off_outlined, size: 56, color: UellowColors.muted),
        const SizedBox(height: 14),
        Text(message, textAlign: TextAlign.center, style: UT.body),
        const SizedBox(height: 16),
        ElevatedButton(onPressed: onRetry, child: const Text('Retry')),
      ]),
    ));
  }
}
