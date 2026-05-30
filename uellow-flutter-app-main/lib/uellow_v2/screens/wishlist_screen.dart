// =============================================================================
// WishlistScreen — grid of wishlist items with stock/price-drop alerts.
// =============================================================================
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';

class WishlistScreen extends StatefulWidget {
  const WishlistScreen({super.key});
  @override
  State<WishlistScreen> createState() => _WishlistScreenState();
}

class _WishlistScreenState extends State<WishlistScreen> {
  Future<List<UellowProductCard>>? _future;
  int _filter = 0;

  @override
  void initState() {
    super.initState();
    _future = UellowApi.instance.wishlist.list();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: Column(children: [
        Container(
          color: Colors.white, padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: UellowColors.border)),
          ),
          child: Row(children: [
            IconButton(onPressed: () => Navigator.maybePop(context),
                icon: const Icon(Icons.arrow_back, color: UellowColors.darkBrown),
                padding: EdgeInsets.zero, constraints: const BoxConstraints()),
            const SizedBox(width: 6),
            const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('My Wishlist', style: UT.h1),
              SizedBox(height: 2),
              Text('12 items · 2 on sale · 1 price dropped', style: UT.small),
            ])),
          ]),
        ),
        // Filters
        Container(
          color: Colors.white,
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: UellowColors.border)),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: SizedBox(
            height: 28,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: _filters.length,
              separatorBuilder: (_, __) => const SizedBox(width: 6),
              itemBuilder: (_, i) => GestureDetector(
                onTap: () => setState(() => _filter = i),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: i == _filter ? UellowColors.darkBrown : UellowColors.border,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(_filters[i], style: TextStyle(
                    color: i == _filter ? UellowColors.yellowLight : UellowColors.text,
                    fontSize: 11.5, fontWeight: FontWeight.w700,
                  )),
                ),
              ),
            ),
          ),
        ),
        Expanded(child: FutureBuilder<List<UellowProductCard>>(
          future: _future,
          builder: (_, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator(color: UellowColors.darkBrown));
            }
            final items = snap.data ?? [];
            if (items.isEmpty) return _empty();
            return GridView.builder(
              padding: const EdgeInsets.all(12),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2, crossAxisSpacing: 10, mainAxisSpacing: 10, childAspectRatio: 0.6,
              ),
              itemCount: items.length,
              itemBuilder: (_, i) => _WishCard(p: items[i], alertIdx: i),
            );
          },
        )),
      ]),
    );
  }

  static const _filters = ['All','In stock','On sale','Price drop','Recently added'];

  Widget _empty() {
    return ListView(children: [
      const SizedBox(height: 100),
      const Center(child: Icon(Icons.favorite_border, size: 80, color: UellowColors.muted)),
      const SizedBox(height: 18),
      const Center(child: Text('Your wishlist is empty', style: UT.h2)),
      const SizedBox(height: 6),
      const Center(child: Text('Tap the heart on any product to add it', style: UT.body)),
    ]);
  }
}

class _WishCard extends StatelessWidget {
  const _WishCard({required this.p, required this.alertIdx});
  final UellowProductCard p;
  final int alertIdx;
  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    Widget? alert;
    if (alertIdx == 0) alert = _alert('⬇  Price dropped 12% since added', UellowColors.successBg, UellowColors.successDk);
    if (alertIdx == 1) alert = _alert('⚠  Only 3 left in stock', UellowColors.warnBg, UellowColors.warn);
    if (alertIdx == 2) alert = _alert('⚡  On flash sale now', UellowColors.danger, Colors.white);

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
        boxShadow: [BoxShadow(color: Color(0x0D000000), blurRadius: 4, offset: Offset(0, 1))],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        AspectRatio(aspectRatio: 1, child: Stack(fit: StackFit.expand, children: [
          ColoredBox(color: const Color(0xFFFAFAFA), child: CachedNetworkImage(
            imageUrl: p.image, fit: BoxFit.cover,
            placeholder: (_, __) => const ColoredBox(color: UellowColors.border),
            errorWidget: (_, __, ___) => const ColoredBox(color: UellowColors.border),
          )),
          Positioned(top: 8, right: 8, child: Container(
            width: 30, height: 30,
            decoration: const BoxDecoration(color: Color(0xF2FFFFFF), shape: BoxShape.circle),
            child: const Icon(Icons.favorite, color: UellowColors.danger, size: 14),
          )),
        ])),
        Padding(
          padding: const EdgeInsets.all(10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(p.name.current(lang), maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12.5, color: UellowColors.ink, height: 1.35)),
            const SizedBox(height: 6),
            Text(p.price.format(), style: const TextStyle(
                fontSize: 16, fontWeight: FontWeight.w900, color: UellowColors.darkBrown)),
            if (alert != null) ...[
              const SizedBox(height: 4),
              alert,
            ],
            const SizedBox(height: 6),
            SizedBox(width: double.infinity, child: ElevatedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.shopping_cart_outlined, size: 12),
              label: const Text('Add to cart',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
              style: ElevatedButton.styleFrom(
                backgroundColor: UellowColors.yellowLight,
                foregroundColor: UellowColors.darkBrown, elevation: 0,
                padding: const EdgeInsets.symmetric(vertical: 8),
                shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.all(Radius.circular(8))),
              ),
            )),
          ]),
        ),
      ]),
    );
  }

  Widget _alert(String text, Color bg, Color fg) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(5)),
      child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis,
          style: TextStyle(color: fg, fontSize: 10, fontWeight: FontWeight.w700)),
    );
  }
}
