// =============================================================================
// CategoryScreen — SHEIN/Banggood pattern: sidebar of main categories
// (left) + content (right). Content shows:
//   1. Sub-categories grid (if any)
//   2. Latest products in the selected main category — horizontal slider
//   3. All products grid
// =============================================================================
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';
import '../widgets/product_card.dart';

class CategoryScreen extends StatefulWidget {
  const CategoryScreen({super.key});
  @override
  State<CategoryScreen> createState() => _CategoryScreenState();
}

class _CategoryScreenState extends State<CategoryScreen> {
  late Future<List<UellowCategory>> _tree;
  int _selectedRoot = 0;

  @override
  void initState() {
    super.initState();
    _tree = UellowApi.instance.categories.tree();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: Column(children: [
        const _CatTopBar(),
        Expanded(
          child: FutureBuilder<List<UellowCategory>>(
            future: _tree,
            builder: (_, snap) {
              if (snap.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator(color: UellowColors.darkBrown));
              }
              if (snap.hasError || (snap.data?.isEmpty ?? true)) {
                return const Center(child: Text('No categories yet.', style: UT.body));
              }
              final roots = snap.data!;
              final current = roots[_selectedRoot.clamp(0, roots.length - 1)];
              return Row(children: [
                _Sidebar(roots: roots, selected: _selectedRoot,
                    onSelect: (i) => setState(() => _selectedRoot = i)),
                Expanded(child: _Content(category: current)),
              ]);
            },
          ),
        ),
      ]),
    );
  }
}

// ─── Top bar ──────────────────────────────────────────────────────

class _CatTopBar extends StatelessWidget {
  const _CatTopBar();
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      child: Row(children: [
        Expanded(child: Container(
          height: 38,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: const BoxDecoration(
            color: UellowColors.border,
            borderRadius: BorderRadius.all(Radius.circular(12)),
          ),
          child: const Row(children: [
            Icon(Icons.search, size: 18, color: UellowColors.muted),
            SizedBox(width: 10),
            Text('Search categories…',
                style: TextStyle(fontSize: 13, color: UellowColors.muted)),
          ]),
        )),
        const SizedBox(width: 8),
        _topIcon(Icons.qr_code_scanner_outlined),
        const SizedBox(width: 8),
        _topIcon(Icons.camera_alt_outlined),
      ]),
    );
  }

  Widget _topIcon(IconData icon) => Container(
        width: 38, height: 38,
        decoration: const BoxDecoration(
          color: UellowColors.border,
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
        child: Icon(icon, size: 18, color: UellowColors.text),
      );
}

// ─── Left sidebar ──────────────────────────────────────────────────

class _Sidebar extends StatelessWidget {
  const _Sidebar({required this.roots, required this.selected, required this.onSelect});
  final List<UellowCategory> roots;
  final int selected;
  final ValueChanged<int> onSelect;
  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    return Container(
      width: 90, color: Colors.white,
      decoration: const BoxDecoration(
        border: Border(right: BorderSide(color: UellowColors.border)),
      ),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(vertical: 4),
        itemCount: roots.length,
        itemBuilder: (_, i) {
          final c = roots[i];
          final on = i == selected;
          return GestureDetector(
            onTap: () => onSelect(i),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
              decoration: BoxDecoration(
                color: on ? UellowColors.yellowFaint : null,
                border: Border(left: BorderSide(
                  color: on ? UellowColors.yellow : Colors.transparent, width: 3,
                )),
              ),
              child: Column(children: [
                Container(
                  width: 42, height: 42,
                  decoration: BoxDecoration(
                    color: c.image == null ? UellowColors.yellowSoft : null,
                    borderRadius: BorderRadius.circular(12),
                    image: c.image != null
                        ? DecorationImage(image: CachedNetworkImageProvider(c.image!),
                            fit: BoxFit.cover)
                        : null,
                  ),
                  alignment: Alignment.center,
                  child: c.image == null
                      ? Text(_emoji(c.name.current(lang)),
                          style: const TextStyle(fontSize: 22))
                      : null,
                ),
                const SizedBox(height: 5),
                Text(c.name.current(lang), maxLines: 2,
                    overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 10.5, height: 1.3,
                      color: on ? UellowColors.darkBrown : UellowColors.text,
                      fontWeight: on ? FontWeight.w800 : FontWeight.w600,
                    )),
              ]),
            ),
          );
        },
      ),
    );
  }

  String _emoji(String name) {
    final n = name.toLowerCase();
    if (n.contains('phone') || n.contains('mobile')) return '📱';
    if (n.contains('fashion') || n.contains('cloth')) return '👗';
    if (n.contains('home')) return '🏠';
    if (n.contains('beauty')) return '💄';
    if (n.contains('watch')) return '⌚';
    if (n.contains('game') || n.contains('toy')) return '🎮';
    if (n.contains('shoe')) return '👟';
    if (n.contains('food')) return '🛒';
    if (n.contains('baby')) return '👶';
    return '📦';
  }
}

// ─── Right content ─────────────────────────────────────────────────

class _Content extends StatefulWidget {
  const _Content({required this.category});
  final UellowCategory category;
  @override
  State<_Content> createState() => _ContentState();
}

class _ContentState extends State<_Content> {
  Future<List<UellowProductCard>>? _products;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant _Content old) {
    super.didUpdateWidget(old);
    if (old.category.id != widget.category.id) _load();
  }

  void _load() {
    setState(() => _products = UellowApi.instance.products.list(
        categoryId: widget.category.id, perPage: 20,
      ).then((page) => page.items));
  }

  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    final subs = widget.category.children;
    return ListView(padding: EdgeInsets.zero, children: [
      // Featured banner
      Container(
        margin: const EdgeInsets.fromLTRB(10, 10, 10, 0),
        padding: const EdgeInsets.all(14),
        decoration: const BoxDecoration(
          gradient: LinearGradient(colors: [UellowColors.yellow, UellowColors.yellowLight]),
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
        child: Row(children: [
          Container(
            width: 44, height: 44,
            decoration: const BoxDecoration(
              color: UellowColors.darkBrown,
              borderRadius: BorderRadius.all(Radius.circular(10)),
            ),
            child: const Icon(Icons.bolt, size: 22, color: UellowColors.yellowLight),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(widget.category.name.current(lang),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14,
                    color: UellowColors.darkBrown)),
            const SizedBox(height: 2),
            const Text('Up to 50% off · today only',
                style: TextStyle(color: Color(0xCC412402), fontSize: 11)),
          ])),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
            decoration: const BoxDecoration(
              color: UellowColors.darkBrown,
              borderRadius: BorderRadius.all(Radius.circular(8)),
            ),
            child: const Text('Shop →', style: TextStyle(
                color: UellowColors.yellowLight, fontWeight: FontWeight.w800, fontSize: 11)),
          ),
        ]),
      ),
      // Sub-categories (only if any)
      if (subs.isNotEmpty) _SubCatsGrid(subs: subs, lang: lang),
      // Latest products slider
      _LatestSlider(category: widget.category, products: _products),
      // All products grid
      Padding(
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
        child: Row(children: [
          Expanded(child: Text(subs.isEmpty ? 'Products in ${widget.category.name.current(lang)}' : 'All products',
              style: UT.h3)),
          Row(children: const [
            Icon(Icons.swap_vert, size: 14, color: UellowColors.darkBrown),
            SizedBox(width: 3),
            Text('Sort', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            SizedBox(width: 12),
            Icon(Icons.tune, size: 14, color: UellowColors.darkBrown),
            SizedBox(width: 3),
            Text('Filter', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
          ]),
        ]),
      ),
      _ProductsGrid(future: _products),
      const SizedBox(height: 30),
    ]);
  }
}

class _SubCatsGrid extends StatelessWidget {
  const _SubCatsGrid({required this.subs, required this.lang});
  final List<UellowCategory> subs;
  final String lang;
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(10, 10, 10, 0),
      padding: const EdgeInsets.fromLTRB(12, 14, 12, 14),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(children: [
            const Text('Sub-categories', style: UT.h3),
            const Spacer(),
            Text('${subs.length} items', style: UT.tiny),
          ]),
        ),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 3, crossAxisSpacing: 8, mainAxisSpacing: 12, childAspectRatio: 0.78,
          ),
          itemCount: subs.length,
          itemBuilder: (_, i) {
            final c = subs[i];
            return Column(children: [
              Expanded(child: Container(
                decoration: BoxDecoration(
                  color: c.image == null ? UellowColors.yellowSoft : null,
                  borderRadius: BorderRadius.circular(12),
                  image: c.image != null
                      ? DecorationImage(image: CachedNetworkImageProvider(c.image!),
                          fit: BoxFit.cover)
                      : null,
                  boxShadow: const [BoxShadow(color: Color(0x0D000000),
                      blurRadius: 6, offset: Offset(0, 2))],
                ),
                alignment: Alignment.center,
                child: c.image == null
                    ? const Text('📦', style: TextStyle(fontSize: 32))
                    : null,
              )),
              const SizedBox(height: 6),
              Text(c.name.current(lang), maxLines: 2,
                  overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700,
                      color: UellowColors.ink)),
              Text('${c.productCount} items',
                  style: UT.tiny),
            ]);
          },
        ),
      ]),
    );
  }
}

class _LatestSlider extends StatelessWidget {
  const _LatestSlider({required this.category, required this.products});
  final UellowCategory category;
  final Future<List<UellowProductCard>>? products;
  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    return Container(
      margin: const EdgeInsets.fromLTRB(10, 10, 10, 0),
      padding: const EdgeInsets.fromLTRB(12, 14, 12, 14),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(children: [
            const Icon(Icons.bolt, size: 14, color: UellowColors.warn),
            const SizedBox(width: 4),
            Expanded(child: Text('Latest in ${category.name.current(lang)}',
                style: UT.h3)),
            const Text('See all →', style: TextStyle(
                fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.text)),
          ]),
        ),
        SizedBox(
          height: 245,
          child: FutureBuilder<List<UellowProductCard>>(
            future: products,
            builder: (_, snap) {
              if (snap.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snap.hasError || (snap.data?.isEmpty ?? true)) {
                return const Center(child: Text('No products', style: UT.small));
              }
              final items = snap.data!.take(10).toList();
              return ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: items.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, i) => SizedBox(
                  width: 140, child: ProductCard(product: items[i])),
              );
            },
          ),
        ),
      ]),
    );
  }
}

class _ProductsGrid extends StatelessWidget {
  const _ProductsGrid({required this.future});
  final Future<List<UellowProductCard>>? future;
  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<UellowProductCard>>(
      future: future,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const SizedBox(height: 200, child: Center(child: CircularProgressIndicator()));
        }
        if (snap.hasError || (snap.data?.isEmpty ?? true)) {
          return const SizedBox.shrink();
        }
        final items = snap.data!;
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2, crossAxisSpacing: 8, mainAxisSpacing: 8, childAspectRatio: 0.58,
            ),
            itemCount: items.length,
            itemBuilder: (_, i) => ProductCard(product: items[i]),
          ),
        );
      },
    );
  }
}
