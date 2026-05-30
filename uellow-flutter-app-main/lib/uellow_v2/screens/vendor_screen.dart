// =============================================================================
// VendorScreen — vendor store with hero + stats + 7 tabs + internal
// flash sale + product sections. Wires to /api/mobile/v2/vendors/<id>.
// =============================================================================
import 'package:flutter/material.dart';

import '../theme/uellow_theme.dart';

class VendorScreen extends StatefulWidget {
  const VendorScreen({super.key, required this.vendorId});
  final int vendorId;
  @override
  State<VendorScreen> createState() => _VendorScreenState();
}

class _VendorScreenState extends State<VendorScreen> {
  int _tab = 0;
  static const _tabs = ['All','New','Best sellers','⚡ Flash','Categories','Reviews','About'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: NestedScrollView(
        headerSliverBuilder: (_, __) => [
          SliverToBoxAdapter(child: _Hero()),
          SliverToBoxAdapter(child: _Info()),
          SliverToBoxAdapter(child: _Stats()),
          SliverPersistentHeader(pinned: true, delegate: _StickyTabs(
            tab: _tab, onChange: (i) => setState(() => _tab = i),
          )),
        ],
        body: ListView(padding: EdgeInsets.zero, children: const [
          _InternalFlash(),
          _ProductsSection(title: 'New arrivals'),
          _ProductsSection(title: 'Best sellers'),
          SizedBox(height: 30),
        ]),
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 160,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft, end: Alignment.bottomRight,
          colors: [UellowColors.darkBrown, Color(0xFF7A4A08)],
        ),
      ),
      child: Stack(children: [
        Positioned(top: 14, left: 14,
          child: IconButton(
            onPressed: () => Navigator.maybePop(context),
            icon: const Icon(Icons.arrow_back, color: UellowColors.yellowLight),
            style: IconButton.styleFrom(
              backgroundColor: const Color(0x33000000),
              shape: const RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(10))),
            ),
          ),
        ),
        Positioned(top: 14, right: 14,
          child: IconButton(
            onPressed: () {},
            icon: const Icon(Icons.share_outlined, color: UellowColors.yellowLight),
            style: IconButton.styleFrom(
              backgroundColor: const Color(0x33000000),
              shape: const RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(10))),
            ),
          ),
        ),
      ]),
    );
  }
}

class _Info extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      transform: Matrix4.translationValues(0, -40, 0),
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 18),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20), topRight: Radius.circular(20),
        ),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          width: 78, height: 78,
          decoration: const BoxDecoration(
            color: UellowColors.yellowLight,
            borderRadius: BorderRadius.all(Radius.circular(18)),
            boxShadow: [BoxShadow(color: Color(0x4D000000), blurRadius: 18, offset: Offset(0, 8))],
          ),
          alignment: Alignment.center,
          child: const Text('U', style: TextStyle(
              fontSize: 30, fontWeight: FontWeight.w900, color: UellowColors.darkBrown)),
        ),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Padding(padding: EdgeInsets.only(top: 4),
              child: Text('Uellow Official', style: UT.h1)),
          const SizedBox(height: 4),
          const Text('Authorized seller · same-day shipping',
              style: TextStyle(fontSize: 11.5, color: UellowColors.muted)),
          const SizedBox(height: 2),
          Row(children: const [
            Text('★★★★★', style: TextStyle(color: UellowColors.yellow, fontSize: 11, letterSpacing: -1)),
            SizedBox(width: 4),
            Text('4.8 · 1.2k reviews',
                style: TextStyle(fontSize: 11, color: UellowColors.muted)),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            ElevatedButton(
              onPressed: () {},
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                shape: const RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(8))),
              ),
              child: const Text('+ Follow', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
            ),
            const SizedBox(width: 6),
            OutlinedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.chat_bubble_outline, size: 13),
              label: const Text('Chat'),
              style: OutlinedButton.styleFrom(
                foregroundColor: UellowColors.darkBrown,
                side: BorderSide.none,
                backgroundColor: UellowColors.border,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                shape: const RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(8))),
              ),
            ),
          ]),
        ])),
      ]),
    );
  }
}

class _Stats extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      transform: Matrix4.translationValues(0, -40, 0),
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
      child: Row(children: [
        for (final s in const [('248','Products'), ('1.2k','Orders'), ('4.8','Rating'), ('24h','Ships in')])
          Expanded(child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 3),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: UellowColors.yellowFaint,
                border: Border.all(color: UellowColors.warnBg),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(children: [
                Text(s.$1, style: const TextStyle(
                    fontSize: 16, fontWeight: FontWeight.w900, color: UellowColors.darkBrown)),
                Text(s.$2, style: const TextStyle(
                    fontSize: 10, color: UellowColors.text)),
              ]),
            ),
          )),
      ]),
    );
  }
}

class _StickyTabs extends SliverPersistentHeaderDelegate {
  _StickyTabs({required this.tab, required this.onChange});
  final int tab;
  final ValueChanged<int> onChange;
  static const _tabs = ['All','New','Best sellers','⚡ Flash','Categories','Reviews','About'];

  @override
  Widget build(BuildContext c, double s, bool o) {
    return Container(
      color: Colors.white,
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      child: SizedBox(height: 46, child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: _tabs.length,
        itemBuilder: (_, i) {
          final on = i == tab;
          return GestureDetector(
            onTap: () => onChange(i),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(
                  color: on ? UellowColors.yellow : Colors.transparent, width: 2,
                )),
              ),
              alignment: Alignment.center,
              child: Text(_tabs[i], style: TextStyle(
                color: on ? UellowColors.darkBrown : UellowColors.muted,
                fontWeight: FontWeight.w700, fontSize: 13)),
            ),
          );
        },
      )),
    );
  }
  @override double get maxExtent => 46;
  @override double get minExtent => 46;
  @override bool shouldRebuild(_StickyTabs old) => old.tab != tab;
}

class _InternalFlash extends StatelessWidget {
  const _InternalFlash();
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      padding: const EdgeInsets.all(14),
      decoration: const BoxDecoration(
        gradient: UellowColors.heroFlash,
        borderRadius: BorderRadius.all(Radius.circular(16)),
        boxShadow: [BoxShadow(color: Color(0x4DC81212), blurRadius: 25, offset: Offset(0, 10))],
      ),
      child: Column(children: [
        Row(children: [
          const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('⚡ Vendor Flash · Uellow', style: TextStyle(
                color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
            Text('Exclusive deals from this store',
                style: TextStyle(color: Colors.white70, fontSize: 11)),
          ])),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(.25),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Text('02:14:37', style: TextStyle(
                color: Colors.white, fontFamily: 'monospace',
                fontWeight: FontWeight.w800, fontSize: 13, letterSpacing: 1)),
          ),
        ]),
        const SizedBox(height: 12),
        SizedBox(height: 130, child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: 5,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (_, i) => Container(
            width: 120, padding: const EdgeInsets.all(6),
            decoration: const BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.all(Radius.circular(10)),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(
                width: double.infinity, height: 70,
                decoration: BoxDecoration(
                  color: UellowColors.border, borderRadius: BorderRadius.circular(6),
                ),
              ),
              const Padding(padding: EdgeInsets.only(top: 4), child: Text('14.9',
                  style: TextStyle(color: UellowColors.danger,
                      fontWeight: FontWeight.w900, fontSize: 13))),
              Container(height: 3, margin: const EdgeInsets.only(top: 3),
                decoration: BoxDecoration(
                  color: UellowColors.dangerBg, borderRadius: BorderRadius.circular(999),
                ),
                child: FractionallySizedBox(
                  alignment: Alignment.centerLeft, widthFactor: 0.7,
                  child: const DecoratedBox(decoration: BoxDecoration(
                    color: UellowColors.danger,
                    borderRadius: BorderRadius.all(Radius.circular(999)),
                  )),
                ),
              ),
            ]),
          ),
        )),
      ]),
    );
  }
}

class _ProductsSection extends StatelessWidget {
  const _ProductsSection({required this.title});
  final String title;
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      color: Colors.white,
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(title, style: UT.h3)),
          const Text('See all →', style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.text)),
        ]),
        const SizedBox(height: 12),
        GridView.builder(
          shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2, crossAxisSpacing: 10, mainAxisSpacing: 10, childAspectRatio: 0.65,
          ),
          itemCount: 4,
          itemBuilder: (_, i) => Container(
            decoration: BoxDecoration(
              color: Colors.white, border: Border.all(color: UellowColors.border),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              AspectRatio(aspectRatio: 1, child: Container(
                  decoration: BoxDecoration(
                    color: UellowColors.border,
                    borderRadius: BorderRadius.circular(11),
                  ),
                  alignment: Alignment.center,
                  child: const Icon(Icons.image_outlined,
                      size: 32, color: UellowColors.muted))),
              const Padding(
                padding: EdgeInsets.fromLTRB(8, 8, 8, 4),
                child: Text('Product name', style: TextStyle(
                    fontSize: 12, color: UellowColors.ink)),
              ),
              const Padding(
                padding: EdgeInsets.fromLTRB(8, 0, 8, 8),
                child: Text('14.900 KD', style: TextStyle(
                    fontWeight: FontWeight.w900, fontSize: 15, color: UellowColors.darkBrown)),
              ),
            ]),
          ),
        ),
      ]),
    );
  }
}
