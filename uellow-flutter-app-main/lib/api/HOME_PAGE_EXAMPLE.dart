// =============================================================================
// EXAMPLE — Refactored home page using UellowApi v2
// =============================================================================
//
// Drop into lib/pages/home/ (or wherever your home lives) and tweak the
// styling to match your design system. The point of this file is to show
// the MIGRATION PATTERN — one `.then((data) => setState(...))` becomes
// a single typed call, errors land in a typed exception, bilingual text
// is one line.
//
// Pattern recap:
//   • Load → `UellowApi.instance.home.get()` returns one typed object.
//   • Text → `t.title.current(api.lang)` picks ar/en based on app locale.
//   • Refresh → wrap in RefreshIndicator; just call load() again.
//   • Errors → catch UellowApiException, show e.message (already localized).
// =============================================================================

import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:carousel_slider/carousel_slider.dart' hide CarouselController;
import 'package:nyoba/api/uellow_api.dart';
import 'package:nyoba/api/uellow_models.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  late Future<UellowHome> _future;

  @override
  void initState() {
    super.initState();
    _future = UellowApi.instance.home.get();
  }

  Future<void> _refresh() async {
    setState(() => _future = UellowApi.instance.home.get());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Uellow')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<UellowHome>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              final e = snap.error;
              final msg = e is UellowApiException ? e.message : e.toString();
              return _ErrorView(message: msg, onRetry: _refresh);
            }
            final home = snap.data!;
            return ListView(
              children: [
                _SliderRail(sliders: home.sliders),
                _CategoryIconStrip(icons: home.categoryIcons),
                _FeatureBannerStrip(banners: home.featureBanners),
                ...home.sections.map((s) => _ProductSection(section: s)),
                const SizedBox(height: 24),
              ],
            );
          },
        ),
      ),
    );
  }
}

// ─── Slider rail (hero) ───────────────────────────────────────────────

class _SliderRail extends StatelessWidget {
  const _SliderRail({required this.sliders});
  final List<UellowSlider> sliders;

  @override
  Widget build(BuildContext context) {
    if (sliders.isEmpty) return const SizedBox.shrink();
    final lang = UellowApi.instance.lang;
    return CarouselSlider.builder(
      itemCount: sliders.length,
      options: CarouselOptions(
        autoPlay: true, viewportFraction: 1, aspectRatio: 16 / 9,
      ),
      itemBuilder: (context, i, _) {
        final s = sliders[i];
        return GestureDetector(
          onTap: () => _handleAction(context, s.actionType, s.actionValue),
          child: Stack(
            fit: StackFit.expand,
            children: [
              CachedNetworkImage(imageUrl: s.imageUrl, fit: BoxFit.cover),
              if (s.title.current(lang).isNotEmpty)
                Align(
                  alignment: Alignment.bottomLeft,
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    color: Colors.black54,
                    child: Text(
                      s.title.current(lang),
                      style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}

// ─── Category icon strip ──────────────────────────────────────────────

class _CategoryIconStrip extends StatelessWidget {
  const _CategoryIconStrip({required this.icons});
  final List<UellowCategoryIcon> icons;

  @override
  Widget build(BuildContext context) {
    if (icons.isEmpty) return const SizedBox.shrink();
    final lang = UellowApi.instance.lang;
    return SizedBox(
      height: 96,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        itemCount: icons.length,
        separatorBuilder: (_, __) => const SizedBox(width: 12),
        itemBuilder: (context, i) {
          final ic = icons[i];
          return InkWell(
            onTap: () => _handleAction(context, ic.actionType, ic.actionValue),
            child: Column(
              children: [
                ClipOval(
                  child: CachedNetworkImage(
                    imageUrl: ic.iconUrl, width: 56, height: 56, fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(height: 4),
                Text(ic.label.current(lang), style: const TextStyle(fontSize: 12)),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ─── Feature banners (e.g. "Free delivery", "30-day returns") ─────────

class _FeatureBannerStrip extends StatelessWidget {
  const _FeatureBannerStrip({required this.banners});
  final List<UellowFeatureBanner> banners;

  @override
  Widget build(BuildContext context) {
    if (banners.isEmpty) return const SizedBox.shrink();
    final lang = UellowApi.instance.lang;
    return SizedBox(
      height: 72,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        itemCount: banners.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final b = banners[i];
          return Container(
            width: 200,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: _color(b.backgroundColor, const Color(0xFFF8F4E3)),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              children: [
                if (b.iconType == 'emoji')
                  Text(b.iconEmoji, style: const TextStyle(fontSize: 28))
                else if (b.iconUrl != null)
                  CachedNetworkImage(imageUrl: b.iconUrl!, width: 36, height: 36),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(b.title.current(lang),
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      Text(b.subtitle.current(lang),
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 11)),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Color _color(String? hex, Color fallback) {
    if (hex == null) return fallback;
    final v = hex.replaceAll('#', '');
    if (v.length != 6) return fallback;
    return Color(int.parse('ff$v', radix: 16));
  }
}

// ─── Product section (rail of cards) ──────────────────────────────────

class _ProductSection extends StatefulWidget {
  const _ProductSection({required this.section});
  final UellowSection section;

  @override
  State<_ProductSection> createState() => _ProductSectionState();
}

class _ProductSectionState extends State<_ProductSection> {
  late Future<List<UellowProductCard>> _future;

  @override
  void initState() {
    super.initState();
    _future = UellowApi.instance.products.bySection(widget.section.id);
  }

  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                Expanded(
                  child: Text(widget.section.title.current(lang),
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                ),
                if (widget.section.showViewMore)
                  TextButton(
                    onPressed: () => _viewMore(context),
                    child: Text(lang == 'ar' ? 'عرض الكل' : 'See all'),
                  ),
              ],
            ),
          ),
          SizedBox(
            height: 240,
            child: FutureBuilder<List<UellowProductCard>>(
              future: _future,
              builder: (context, snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snap.hasError || (snap.data?.isEmpty ?? true)) {
                  return Center(
                    child: Text(lang == 'ar' ? 'لا توجد منتجات' : 'No products'),
                  );
                }
                final items = snap.data!;
                return ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, i) => _ProductCard(product: items[i]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _viewMore(BuildContext context) {
    // Hook up your existing navigator; section.moreActionValue carries
    // the destination (category id / search string / url).
  }
}

class _ProductCard extends StatelessWidget {
  const _ProductCard({required this.product});
  final UellowProductCard product;

  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    return SizedBox(
      width: 140,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Stack(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: CachedNetworkImage(
                  imageUrl: product.image, width: 140, height: 140, fit: BoxFit.cover,
                ),
              ),
              if (product.discountPct > 0)
                Positioned(
                  top: 6, left: 6,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.red, borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text('-${product.discountPct}%',
                        style: const TextStyle(color: Colors.white, fontSize: 11)),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Text(product.name.current(lang),
              maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13)),
          const SizedBox(height: 2),
          Row(
            children: [
              Text(product.price.format(),
                  style: const TextStyle(fontWeight: FontWeight.w800)),
              if (product.comparePrice != null) ...[
                const SizedBox(width: 6),
                Text(product.comparePrice!.format(),
                    style: const TextStyle(
                        fontSize: 11, decoration: TextDecoration.lineThrough)),
              ],
            ],
          ),
          if (product.rating.count > 0)
            Row(children: [
              const Icon(Icons.star, size: 13, color: Colors.amber),
              Text(' ${product.rating.avg.toStringAsFixed(1)} (${product.rating.count})',
                  style: const TextStyle(fontSize: 11)),
            ]),
        ],
      ),
    );
  }
}

// ─── Error view ───────────────────────────────────────────────────────

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 80),
        Center(child: Icon(Icons.error_outline, size: 56, color: Colors.red[300])),
        const SizedBox(height: 12),
        Center(child: Text(message, textAlign: TextAlign.center)),
        const SizedBox(height: 16),
        Center(child: ElevatedButton(onPressed: onRetry, child: const Text('Retry'))),
      ],
    );
  }
}

// ─── Action handler — translate (type,value) into a Navigator route ──

void _handleAction(BuildContext context, String type, dynamic value) {
  // Wire to your existing router:
  //   product   → push ProductPage(id: value)
  //   category  → push CategoryPage(id: value)
  //   url       → open in webview / external browser
  //   search    → push SearchPage(query: value)
  //
  // Centralizing this here keeps every slider / icon / banner / popup
  // using the same routing logic — no duplicated switch-statements.
}
