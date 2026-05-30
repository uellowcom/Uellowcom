// =============================================================================
// FlashScreen — flash-sale full page: banner + countdown + cat/vendor
// filters + sort/filter + 2-col products grid.
// =============================================================================
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';
import '../widgets/product_card.dart';

class FlashScreen extends StatefulWidget {
  const FlashScreen({super.key});
  @override
  State<FlashScreen> createState() => _FlashScreenState();
}

class _FlashScreenState extends State<FlashScreen> {
  int _catIdx = 0;
  Future<UellowPage<UellowProductCard>>? _future;

  @override
  void initState() {
    super.initState();
    _future = UellowApi.instance.products.list(onSale: true, perPage: 24);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: CustomScrollView(slivers: [
        SliverToBoxAdapter(child: _Hero()),
        SliverToBoxAdapter(child: _Filters(
          catIdx: _catIdx, onCat: (i) => setState(() => _catIdx = i),
        )),
        SliverToBoxAdapter(child: _SortBar()),
        SliverToBoxAdapter(child: _Grid(future: _future)),
        const SliverToBoxAdapter(child: SizedBox(height: 30)),
      ]),
    );
  }
}

class _Hero extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 22),
      decoration: const BoxDecoration(
        gradient: UellowColors.heroFlash,
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          IconButton(
            onPressed: () => Navigator.maybePop(context),
            icon: const Icon(Icons.arrow_back, color: Colors.white),
            padding: EdgeInsets.zero, constraints: const BoxConstraints(),
          ),
          const SizedBox(width: 8),
          const Text('⚡', style: TextStyle(fontSize: 22)),
          const SizedBox(width: 4),
          const Expanded(child: Text('Mega Flash Sale',
              style: TextStyle(color: Colors.white,
                  fontSize: 22, fontWeight: FontWeight.w900))),
        ]),
        const SizedBox(height: 4),
        const Padding(padding: EdgeInsets.only(left: 48),
            child: Text('Up to 70% off · ends in 2h 14m',
                style: TextStyle(color: Color(0xD9FFFFFF), fontSize: 13))),
        const SizedBox(height: 14),
        Row(children: const [
          Expanded(child: _Cell(num: '02', lbl: 'HOURS')),
          SizedBox(width: 8),
          Expanded(child: _Cell(num: '14', lbl: 'MINUTES')),
          SizedBox(width: 8),
          Expanded(child: _Cell(num: '37', lbl: 'SECONDS')),
        ]),
      ]),
    );
  }
}

class _Cell extends StatelessWidget {
  const _Cell({required this.num, required this.lbl});
  final String num, lbl;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(.25),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(children: [
        Text(num, style: const TextStyle(
            color: Colors.white, fontSize: 24, fontWeight: FontWeight.w900)),
        Text(lbl, style: const TextStyle(
            color: Color(0xB3FFFFFF), fontSize: 10, letterSpacing: 0.5)),
      ]),
    );
  }
}

class _Filters extends StatelessWidget {
  const _Filters({required this.catIdx, required this.onCat});
  final int catIdx;
  final ValueChanged<int> onCat;
  static const _cats = ['All','Phones','Fashion','Beauty','Home','Sports'];
  static const _vendors = [
    ('U', Color(0xFF412402), 'Uellow'),
    ('A', Color(0xFFFF4D4D), 'Anker'),
    ('S', Color(0xFF3B82F6), 'Samsung'),
    ('H', Color(0xFF10B981), 'Huawei'),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('FILTER BY CATEGORY', style: TextStyle(
            fontSize: 11, color: UellowColors.muted,
            fontWeight: FontWeight.w800, letterSpacing: 0.5)),
        const SizedBox(height: 8),
        SizedBox(height: 30, child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: _cats.length,
          separatorBuilder: (_, __) => const SizedBox(width: 6),
          itemBuilder: (_, i) => GestureDetector(
            onTap: () => onCat(i),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              decoration: BoxDecoration(
                color: i == catIdx ? UellowColors.darkBrown : UellowColors.border,
                borderRadius: BorderRadius.circular(999),
              ),
              alignment: Alignment.center,
              child: Text(_cats[i], style: TextStyle(
                color: i == catIdx ? UellowColors.yellowLight : UellowColors.text,
                fontWeight: FontWeight.w700, fontSize: 12,
              )),
            ),
          ),
        )),
        const SizedBox(height: 14),
        const Text('FILTER BY VENDOR', style: TextStyle(
            fontSize: 11, color: UellowColors.muted,
            fontWeight: FontWeight.w800, letterSpacing: 0.5)),
        const SizedBox(height: 8),
        SizedBox(height: 38, child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: _vendors.length,
          separatorBuilder: (_, __) => const SizedBox(width: 6),
          itemBuilder: (_, i) {
            final v = _vendors[i];
            return Container(
              padding: const EdgeInsets.fromLTRB(4, 4, 12, 4),
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(color: UellowColors.border),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(children: [
                Container(
                  width: 28, height: 28,
                  decoration: BoxDecoration(color: v.$2, shape: BoxShape.circle),
                  alignment: Alignment.center,
                  child: Text(v.$1, style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.w900, fontSize: 11)),
                ),
                const SizedBox(width: 6),
                Text(v.$3, style: const TextStyle(
                    fontSize: 12, color: UellowColors.darkBrown)),
              ]),
            );
          },
        )),
      ]),
    );
  }
}

class _SortBar extends StatelessWidget {
  const _SortBar();
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      child: Row(children: [
        Text.rich(TextSpan(style: const TextStyle(fontSize: 12, color: UellowColors.muted), children: [
          const TextSpan(text: '', style: TextStyle()),
          TextSpan(text: '248', style: const TextStyle(
              fontWeight: FontWeight.w900, color: UellowColors.darkBrown)),
          const TextSpan(text: ' deals · in stock'),
        ])),
        const Spacer(),
        Row(children: const [
          Icon(Icons.swap_vert, size: 14, color: UellowColors.darkBrown),
          SizedBox(width: 3),
          Text('Sort', style: TextStyle(
              fontSize: 12, fontWeight: FontWeight.w700, color: UellowColors.darkBrown)),
          SizedBox(width: 14),
          Icon(Icons.tune, size: 14, color: UellowColors.darkBrown),
          SizedBox(width: 3),
          Text('Filters', style: TextStyle(
              fontSize: 12, fontWeight: FontWeight.w700, color: UellowColors.darkBrown)),
        ]),
      ]),
    );
  }
}

class _Grid extends StatelessWidget {
  const _Grid({required this.future});
  final Future<UellowPage<UellowProductCard>>? future;
  @override
  Widget build(BuildContext context) {
    return FutureBuilder<UellowPage<UellowProductCard>>(
      future: future,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const SizedBox(height: 300, child: Center(
              child: CircularProgressIndicator(color: UellowColors.darkBrown)));
        }
        final items = snap.data?.items ?? [];
        if (items.isEmpty) {
          return const SizedBox(height: 200, child: Center(
              child: Text('No deals available right now', style: UT.body)));
        }
        return Padding(
          padding: const EdgeInsets.all(12),
          child: GridView.builder(
            shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2, crossAxisSpacing: 8, mainAxisSpacing: 8, childAspectRatio: 0.58,
            ),
            itemCount: items.length,
            itemBuilder: (_, i) => ProductCard(product: items[i], inFlashSale: true),
          ),
        );
      },
    );
  }
}
