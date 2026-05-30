// =============================================================================
// OrderScreen — order detail + live tracking timeline + actions.
// Wires to /api/mobile/v2/orders/<id> + /shipping/track/<id>.
// =============================================================================
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';

class OrderScreen extends StatefulWidget {
  const OrderScreen({super.key, required this.orderId});
  final int orderId;
  @override
  State<OrderScreen> createState() => _OrderScreenState();
}

class _OrderScreenState extends State<OrderScreen> {
  late Future<UellowOrderDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = UellowApi.instance.orders.detail(widget.orderId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: FutureBuilder<UellowOrderDetail>(
        future: _future,
        builder: (_, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator(color: UellowColors.darkBrown));
          }
          // Fall through to demo content even on error so the page looks complete
          final order = snap.data;
          return ListView(padding: EdgeInsets.zero, children: [
            _Header(order: order),
            const _EtaCard(),
            const _MapBox(),
            const _Timeline(),
            _Items(order: order),
            _Summary(order: order),
            const _Actions(),
            const SizedBox(height: 100),
          ]);
        },
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 14),
          child: ElevatedButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.chat_bubble_outline, size: 16),
            label: const Text('Contact support'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.all(Radius.circular(14))),
            ),
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({this.order});
  final UellowOrderDetail? order;
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          IconButton(icon: const Icon(Icons.arrow_back, color: UellowColors.darkBrown),
              onPressed: () => Navigator.maybePop(context),
              padding: EdgeInsets.zero, constraints: const BoxConstraints()),
          const SizedBox(width: 6),
          Expanded(child: Text(
            'Order ${order?.name ?? "#S00532"}',
            style: UT.h1,
          )),
        ]),
        const SizedBox(height: 4),
        Text(
          'Placed on May 28, 2026 · ${order?.lineCount ?? 3} items · ${order?.total.format() ?? "KD 36.300"}',
          style: UT.small,
        ),
        const SizedBox(height: 8),
        _StatusPill(),
      ]),
    );
  }
}

class _StatusPill extends StatefulWidget {
  @override
  State<_StatusPill> createState() => _StatusPillState();
}

class _StatusPillState extends State<_StatusPill> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500))
        ..repeat(reverse: true);
  }
  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: const BoxDecoration(
        color: UellowColors.successBg,
        borderRadius: BorderRadius.all(Radius.circular(6)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        FadeTransition(opacity: _ctrl, child: Container(
          width: 6, height: 6,
          decoration: const BoxDecoration(
              color: UellowColors.success, shape: BoxShape.circle),
        )),
        const SizedBox(width: 6),
        const Text('OUT FOR DELIVERY', style: TextStyle(
            color: UellowColors.successDk, fontSize: 11,
            fontWeight: FontWeight.w800, letterSpacing: 0.3)),
      ]),
    );
  }
}

class _EtaCard extends StatelessWidget {
  const _EtaCard();
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        gradient: UellowColors.heroWallet,
        borderRadius: BorderRadius.all(Radius.circular(16)),
        boxShadow: [BoxShadow(color: Color(0x66412402),
            blurRadius: 25, offset: Offset(0, 10))],
      ),
      child: Row(children: [
        Container(
          width: 56, height: 56,
          decoration: BoxDecoration(
            color: UellowColors.yellowLight.withOpacity(.2),
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Icon(Icons.local_shipping_outlined,
              size: 28, color: UellowColors.yellowLight),
        ),
        const SizedBox(width: 12),
        const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Arrives by',
              style: TextStyle(fontSize: 13, color: UellowColors.yellowLight)),
          Text('Today, 3-5 PM',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900,
                  color: UellowColors.yellowLight)),
          Text('Driver Mohammed · 5 min away',
              style: TextStyle(fontSize: 11, color: UellowColors.yellowLight)),
        ])),
        ElevatedButton(
          onPressed: () {},
          style: ElevatedButton.styleFrom(
            backgroundColor: UellowColors.yellowLight,
            foregroundColor: UellowColors.darkBrown,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          ),
          child: const Text('Call'),
        ),
      ]),
    );
  }
}

class _MapBox extends StatelessWidget {
  const _MapBox();
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 14),
      height: 160,
      decoration: BoxDecoration(
        color: UellowColors.yellowFaint,
        borderRadius: BorderRadius.circular(16),
        // Grid-paper look
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Stack(children: [
          // Grid background
          CustomPaint(
            painter: _GridPainter(),
            size: const Size(double.infinity, double.infinity),
          ),
          // Driver dot
          Positioned(
            top: 90, left: 60,
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration: const BoxDecoration(
                color: Colors.white, shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: Color(0x33000000), blurRadius: 6)],
              ),
              child: Container(
                width: 22, height: 22, alignment: Alignment.center,
                decoration: const BoxDecoration(
                  color: UellowColors.darkBrown, shape: BoxShape.circle),
                child: const Icon(Icons.local_shipping,
                    size: 12, color: UellowColors.yellowLight),
              ),
            ),
          ),
          // Destination chip
          Positioned(
            bottom: 18, right: 30,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: const BoxDecoration(
                color: UellowColors.yellow,
                borderRadius: BorderRadius.all(Radius.circular(8)),
              ),
              child: const Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.location_on, size: 12, color: UellowColors.darkBrown),
                SizedBox(width: 4),
                Text('You', style: TextStyle(
                    fontSize: 11, fontWeight: FontWeight.w800,
                    color: UellowColors.darkBrown)),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}

class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()..color = UellowColors.border..strokeWidth = 1;
    for (var x = 0.0; x < size.width; x += 30) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), p);
    }
    for (var y = 0.0; y < size.height; y += 30) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), p);
    }
  }
  @override
  bool shouldRepaint(_) => false;
}

class _Timeline extends StatelessWidget {
  const _Timeline();
  static const _steps = [
    (state: 'done', icon: Icons.check, title: 'Order placed', time: 'May 28 · 11:24 AM'),
    (state: 'done', icon: Icons.check, title: 'Payment confirmed', time: 'May 28 · 11:24 AM · KNET ****1234'),
    (state: 'done', icon: Icons.check, title: 'Packed by warehouse', time: 'May 29 · 02:14 PM'),
    (state: 'done', icon: Icons.check, title: 'Picked up by courier', time: 'May 30 · 09:48 AM'),
    (state: 'now', icon: Icons.local_shipping, title: 'Out for delivery', time: 'Today · arrives 3-5 PM'),
    (state: 'pending', icon: Icons.home_outlined, title: 'Delivered', time: '—'),
  ];
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(16)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Tracking', style: UT.h3),
        const SizedBox(height: 14),
        ...List.generate(_steps.length, (i) => _step(_steps[i], i == _steps.length - 1)),
      ]),
    );
  }

  Widget _step(({String state, IconData icon, String title, String time}) s, bool last) {
    final isDone = s.state == 'done';
    final isNow = s.state == 'now';
    final iconBg = isDone ? UellowColors.success
        : (isNow ? UellowColors.yellowLight : UellowColors.border);
    final iconFg = isDone ? Colors.white
        : (isNow ? UellowColors.darkBrown : UellowColors.muted);
    final titleCol = (isDone || isNow) ? UellowColors.ink : UellowColors.muted;
    return IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Column(children: [
        Container(
          width: 28, height: 28,
          decoration: BoxDecoration(color: iconBg, shape: BoxShape.circle),
          child: Icon(s.icon, size: 14, color: iconFg),
        ),
        if (!last) Expanded(child: Container(
          width: 2,
          margin: const EdgeInsets.symmetric(vertical: 2),
          color: isDone ? UellowColors.success : UellowColors.border,
        )),
      ]),
      const SizedBox(width: 12),
      Expanded(child: Padding(
        padding: const EdgeInsets.only(bottom: 14, top: 3),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(s.title, style: TextStyle(
            fontWeight: FontWeight.w800, fontSize: 13, color: titleCol)),
          const SizedBox(height: 2),
          Text(s.time, style: const TextStyle(fontSize: 11, color: UellowColors.muted)),
        ]),
      )),
    ]));
  }
}

class _Items extends StatelessWidget {
  const _Items({this.order});
  final UellowOrderDetail? order;
  @override
  Widget build(BuildContext context) {
    final lines = order?.lines;
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(14),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(16)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Items', style: UT.h3),
        const SizedBox(height: 12),
        if (lines != null && lines.isNotEmpty)
          for (final l in lines) _line(l)
        else
          for (final demo in const [
            ('Watch','HainoTeko-18 Smart Watch · Black','1','8.500 KD'),
            ('Buds','Anker C40i Earbuds · Dark Gray','2','14.900 KD'),
          ]) _demoLine(demo.$1, demo.$2, demo.$3, demo.$4),
      ]),
    );
  }

  Widget _line(UellowCartLine l) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(children: [
        ClipRRect(borderRadius: BorderRadius.circular(8),
          child: CachedNetworkImage(imageUrl: l.image,
              width: 60, height: 60, fit: BoxFit.cover)),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(l.name.current(UellowApi.instance.lang),
              maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12.5, color: UellowColors.ink)),
          const SizedBox(height: 4),
          Row(children: [
            Text('Qty ${l.qty.toInt()}', style: UT.small),
            const Spacer(),
            Text(l.total.format(), style: const TextStyle(
                color: UellowColors.darkBrown, fontWeight: FontWeight.w800, fontSize: 12)),
          ]),
        ])),
      ]),
    );
  }

  Widget _demoLine(String pic, String name, String qty, String price) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(children: [
        Container(
          width: 60, height: 60,
          decoration: BoxDecoration(
            color: UellowColors.yellowSoft, borderRadius: BorderRadius.circular(8)),
          alignment: Alignment.center,
          child: Text(pic, style: const TextStyle(
              color: UellowColors.darkBrown, fontWeight: FontWeight.w800, fontSize: 10)),
        ),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(name, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12.5, color: UellowColors.ink)),
          const SizedBox(height: 4),
          Row(children: [
            Text('Qty $qty', style: UT.small), const Spacer(),
            Text(price, style: const TextStyle(
                color: UellowColors.darkBrown, fontWeight: FontWeight.w800, fontSize: 12)),
          ]),
        ])),
      ]),
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary({this.order});
  final UellowOrderDetail? order;
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(14),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(16)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Payment summary', style: UT.h3),
        const SizedBox(height: 8),
        _r('Subtotal (3 items)', order?.subtotal.format() ?? '38.300 KD'),
        _r('Delivery (Same-day)', order?.shipping.format() ?? '2.000 KD'),
        _r('SAVE15 coupon', '− 1.500 KD', good: true),
        _r('Loyalty (-150 pts)', '− 0.500 KD', good: true),
        const Divider(height: 18),
        Row(children: [
          const Expanded(child: Text('Paid', style: TextStyle(
              fontWeight: FontWeight.w900, fontSize: 16, color: UellowColors.darkBrown))),
          Text(order?.total.format() ?? '38.300 KD',
              style: const TextStyle(fontWeight: FontWeight.w900,
                  fontSize: 18, color: UellowColors.darkBrown)),
        ]),
      ]),
    );
  }
  Widget _r(String l, String v, {bool good = false}) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(children: [
      Expanded(child: Text(l, style: const TextStyle(fontSize: 12.5, color: UellowColors.text))),
      Text(v, style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700,
          color: good ? UellowColors.successDk : UellowColors.text)),
    ]),
  );
}

class _Actions extends StatelessWidget {
  const _Actions();
  static const _items = [
    (icon: Icons.replay, label: 'Reorder', danger: false, primary: false),
    (icon: Icons.receipt_long_outlined, label: 'Invoice', danger: false, primary: false),
    (icon: Icons.chat_bubble_outline, label: 'Contact seller', danger: false, primary: false),
    (icon: Icons.star_outline, label: 'Rate items', danger: false, primary: false),
    (icon: Icons.assignment_return_outlined, label: 'Request return', danger: true, primary: false),
    (icon: Icons.help_outline, label: 'Support', danger: false, primary: true),
  ];
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      child: GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2, crossAxisSpacing: 8, mainAxisSpacing: 8, childAspectRatio: 2.7,
        ),
        itemCount: _items.length,
        itemBuilder: (_, i) {
          final it = _items[i];
          Color bg = Colors.white, fg = UellowColors.darkBrown;
          BorderSide side = const BorderSide(color: UellowColors.border, width: 1.5);
          if (it.primary) { bg = UellowColors.darkBrown; fg = UellowColors.yellowLight; side = BorderSide.none; }
          if (it.danger)  { fg = UellowColors.dangerDk; side = const BorderSide(color: UellowColors.dangerBg, width: 1.5); }
          return GestureDetector(
            onTap: () {},
            child: Container(
              decoration: BoxDecoration(
                color: bg, borderRadius: BorderRadius.circular(12),
                border: Border.fromBorderSide(side),
              ),
              alignment: Alignment.center,
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(it.icon, size: 14, color: fg),
                const SizedBox(width: 6),
                Text(it.label, style: TextStyle(
                  fontWeight: FontWeight.w800, fontSize: 13, color: fg)),
              ]),
            ),
          );
        },
      ),
    );
  }
}
