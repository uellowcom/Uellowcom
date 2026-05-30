// =============================================================================
// HomeScreen — full mockup home with:
//   • Top bar (search + barcode + camera)
//   • Category strip (top, names only)
//   • Hero slider
//   • Features chips (Free delivery / Same-day / Returns / Warranty)
//   • Category icons row
//   • Flash sale block
//   • Product sections (rails) — one per mobile.product.slider
//
// All data comes from a single /api/mobile/v2/home call + parallel
// /products/section/{id} for each section's rail.
// =============================================================================
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';
import '../widgets/product_card.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
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
      backgroundColor: UellowColors.bg,
      body: RefreshIndicator(
        color: UellowColors.darkBrown,
        backgroundColor: UellowColors.yellowLight,
        onRefresh: _refresh,
        child: FutureBuilder<UellowHome>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const _LoadingState();
            }
            if (snap.hasError) {
              final e = snap.error;
              final msg = e is UellowApiException ? e.message : e.toString();
              return _ErrorState(message: msg, onRetry: _refresh);
            }
            final home = snap.data!;
            return CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                SliverToBoxAdapter(child: _TopBar()),
                SliverToBoxAdapter(child: _CategoryStrip()),
                SliverToBoxAdapter(child: _HeroSlider(sliders: home.sliders)),
                SliverToBoxAdapter(child: const _FeaturesChips()),
                SliverToBoxAdapter(child: _CategoryIcons(icons: home.categoryIcons)),
                if (home.sections.isNotEmpty)
                  ...home.sections.map(
                    (s) => SliverToBoxAdapter(child: _ProductRail(section: s)),
                  ),
                const SliverToBoxAdapter(child: SizedBox(height: 80)),
              ],
            );
          },
        ),
      ),
      bottomNavigationBar: const _BottomNav(active: 0),
    );
  }
}

// ─── Top bar ───────────────────────────────────────────────────────

class _TopBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: UellowColors.bg,
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      child: Row(
        children: [
          Expanded(
            child: Container(
              height: 40,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: const BoxDecoration(
                color: UellowColors.border,
                borderRadius: BorderRadius.all(Radius.circular(12)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.search, size: 18, color: UellowColors.muted),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'ابحث عن منتج، ماركة، أو ﺗﺎﺟﺮ…',
                      style: TextStyle(color: UellowColors.muted.withOpacity(.9),
                          fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 8),
          _IconButton(icon: Icons.qr_code_scanner_outlined, onTap: () {}),
          const SizedBox(width: 8),
          _IconButton(icon: Icons.camera_alt_outlined, onTap: () {}),
        ],
      ),
    );
  }
}

class _IconButton extends StatelessWidget {
  const _IconButton({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40, height: 40,
        decoration: const BoxDecoration(
          color: UellowColors.border,
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
        child: Icon(icon, size: 18, color: UellowColors.text),
      ),
    );
  }
}

// ─── Category strip (names only) ───────────────────────────────────

class _CategoryStrip extends StatelessWidget {
  static const _names = ['All','Phones','Fashion','Home','Beauty','Sports','Watches','Gaming'];
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 38,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        itemCount: _names.length,
        separatorBuilder: (_, __) => const SizedBox(width: 6),
        itemBuilder: (_, i) {
          final on = i == 0;
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
            decoration: BoxDecoration(
              color: on ? UellowColors.darkBrown : Colors.white,
              border: Border.all(
                  color: on ? UellowColors.darkBrown : UellowColors.border),
              borderRadius: BorderRadius.circular(999),
            ),
            alignment: Alignment.center,
            child: Text(_names[i],
                style: TextStyle(
                  color: on ? UellowColors.yellowLight : UellowColors.text,
                  fontWeight: FontWeight.w700, fontSize: 12,
                )),
          );
        },
      ),
    );
  }
}

// ─── Hero slider ───────────────────────────────────────────────────

class _HeroSlider extends StatelessWidget {
  const _HeroSlider({required this.sliders});
  final List<UellowSlider> sliders;
  @override
  Widget build(BuildContext context) {
    final items = sliders.isEmpty
        ? [const _DemoSlide()]
        : sliders.map((s) => _RealSlide(s: s)).toList();
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 14),
      child: SizedBox(
        height: 170,
        child: PageView.builder(
          controller: PageController(viewportFraction: 1),
          itemCount: items.length,
          itemBuilder: (_, i) => Padding(
            padding: const EdgeInsets.only(right: 4),
            child: items[i],
          ),
        ),
      ),
    );
  }
}

class _RealSlide extends StatelessWidget {
  const _RealSlide({required this.s});
  final UellowSlider s;
  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    return ClipRRect(
      borderRadius: const BorderRadius.all(Radius.circular(18)),
      child: Stack(fit: StackFit.expand, children: [
        CachedNetworkImage(imageUrl: s.imageUrl, fit: BoxFit.cover),
        DecoratedBox(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter, end: Alignment.bottomCenter,
              colors: [Colors.transparent, Color(0x8C000000)],
              stops: [0.4, 1.0],
            ),
          ),
        ),
        Positioned(
          left: 18, right: 18, bottom: 16,
          child: Text(s.title.current(lang),
              maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: UellowColors.yellowLight,
                fontSize: 18, fontWeight: FontWeight.w800,
              )),
        ),
      ]),
    );
  }
}

class _DemoSlide extends StatelessWidget {
  const _DemoSlide();
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.all(Radius.circular(18)),
        gradient: LinearGradient(colors: [UellowColors.darkBrown, Color(0xFF6E3D05)]),
      ),
      padding: const EdgeInsets.all(18),
      alignment: Alignment.bottomLeft,
      child: const Text('Big Sale — Up to 70% off · Free delivery KD 10+',
          style: TextStyle(color: UellowColors.yellowLight,
              fontSize: 18, fontWeight: FontWeight.w800)),
    );
  }
}

// ─── Features chips ────────────────────────────────────────────────

class _FeaturesChips extends StatelessWidget {
  const _FeaturesChips();
  static const _features = [
    (Icons.local_shipping_outlined, 'Free delivery KD 10+'),
    (Icons.bolt_outlined, 'Same-day delivery'),
    (Icons.replay_outlined, '30-day returns'),
    (Icons.shield_outlined, 'Original products'),
  ];
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        itemCount: _features.length,
        separatorBuilder: (_, __) => const SizedBox(width: 6),
        itemBuilder: (_, i) {
          final (icon, label) = _features[i];
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
            decoration: BoxDecoration(
              color: UellowColors.yellowSoft,
              border: Border.all(color: UellowColors.warnBg),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(icon, size: 14, color: UellowColors.warn),
              const SizedBox(width: 6),
              Text(label, style: const TextStyle(
                color: UellowColors.darkBrown, fontWeight: FontWeight.w700, fontSize: 11.5,
              )),
            ]),
          );
        },
      ),
    );
  }
}

// ─── Category icons row ────────────────────────────────────────────

class _CategoryIcons extends StatelessWidget {
  const _CategoryIcons({required this.icons});
  final List<UellowCategoryIcon> icons;
  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    final list = icons.isEmpty
        ? const [
            ('📱','Phones'),('💻','Laptops'),('👗','Fashion'),('🏠','Home'),
            ('👶','Baby'),('🎮','Gaming'),('💄','Beauty'),('⚽','Sports'),
          ]
        : icons.map((ic) => (ic.iconUrl, ic.label.current(lang))).toList();
    return Padding(
      padding: const EdgeInsets.only(bottom: 18, top: 4),
      child: SizedBox(
        height: 92,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          itemCount: list.length,
          separatorBuilder: (_, __) => const SizedBox(width: 14),
          itemBuilder: (_, i) {
            final item = list[i];
            final isEmoji = item.$1.length <= 4;
            return SizedBox(
              width: 64,
              child: Column(children: [
                Container(
                  width: 60, height: 60,
                  decoration: BoxDecoration(
                    color: isEmoji ? UellowColors.yellowSoft : null,
                    borderRadius: BorderRadius.circular(18),
                    image: isEmoji ? null : DecorationImage(
                      image: CachedNetworkImageProvider(item.$1), fit: BoxFit.cover,
                    ),
                    boxShadow: const [BoxShadow(
                      color: Color(0x40412402), blurRadius: 10, offset: Offset(0, 4),
                    )],
                  ),
                  alignment: Alignment.center,
                  child: isEmoji ? Text(item.$1,
                      style: const TextStyle(fontSize: 26)) : null,
                ),
                const SizedBox(height: 6),
                Text(item.$2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 11, color: UellowColors.darkBrown, fontWeight: FontWeight.w600,
                    )),
              ]),
            );
          },
        ),
      ),
    );
  }
}

// ─── Product rail (horizontal section of cards) ────────────────────

class _ProductRail extends StatefulWidget {
  const _ProductRail({required this.section});
  final UellowSection section;
  @override
  State<_ProductRail> createState() => _ProductRailState();
}

class _ProductRailState extends State<_ProductRail> {
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
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
          child: Row(children: [
            Expanded(child: Text(widget.section.title.current(lang),
                style: UT.h2)),
            if (widget.section.showViewMore)
              Text('See all  →',
                  style: TextStyle(color: UellowColors.text.withOpacity(.85),
                      fontWeight: FontWeight.w700, fontSize: 12)),
          ]),
        ),
        SizedBox(
          height: 270,
          child: FutureBuilder<List<UellowProductCard>>(
            future: _future,
            builder: (_, snap) {
              if (snap.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snap.hasError || (snap.data?.isEmpty ?? true)) {
                return Center(child: Text('No products', style: UT.small));
              }
              final items = snap.data!;
              return ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 14),
                itemCount: items.length,
                separatorBuilder: (_, __) => const SizedBox(width: 10),
                itemBuilder: (_, i) =>
                  SizedBox(width: 150, child: ProductCard(product: items[i])),
              );
            },
          ),
        ),
      ]),
    );
  }
}

// ─── Bottom nav (visible on all logged-in screens) ─────────────────

class _BottomNav extends StatelessWidget {
  const _BottomNav({required this.active});
  final int active;
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: UellowColors.border, width: .5)),
      ),
      padding: const EdgeInsets.only(top: 6, bottom: 8),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 56,
          child: Row(children: [
            _NavTab(icon: Icons.home_filled, label: 'Home', on: active == 0),
            _NavTab(icon: Icons.grid_view, label: 'Shop', on: active == 1),
            _BeenaTab(),
            _NavTab(icon: Icons.shopping_cart_outlined, label: 'Cart', badge: 2, on: active == 3),
            _NavTab(icon: Icons.person_outline, label: 'Account', on: active == 4),
          ]),
        ),
      ),
    );
  }
}

class _NavTab extends StatelessWidget {
  const _NavTab({required this.icon, required this.label, this.badge, this.on = false});
  final IconData icon;
  final String label;
  final int? badge;
  final bool on;
  @override
  Widget build(BuildContext context) {
    final col = on ? UellowColors.darkBrown : const Color(0xFF9D8A60);
    return Expanded(
      child: Stack(alignment: Alignment.center, children: [
        Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, size: 22, color: col),
          const SizedBox(height: 3),
          Text(label,
              style: TextStyle(fontSize: 10.5, color: col, fontWeight: FontWeight.w600)),
        ]),
        if (badge != null) Positioned(
          top: 6, right: 28,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
            decoration: BoxDecoration(
              color: UellowColors.danger,
              borderRadius: BorderRadius.circular(9),
            ),
            constraints: const BoxConstraints(minWidth: 18),
            child: Text('$badge', textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white,
                    fontSize: 10, fontWeight: FontWeight.w800)),
          ),
        ),
      ]),
    );
  }
}

class _BeenaTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        Container(
          width: 44, height: 44,
          margin: const EdgeInsets.only(top: -16),
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              center: Alignment(-0.4, -0.5),
              colors: [Color(0xFFFFE45E), UellowColors.yellow, Color(0xFFC99000)],
            ),
            boxShadow: [BoxShadow(
              color: Color(0xA6F5C320), blurRadius: 18, offset: Offset(0, 6),
            )],
          ),
          alignment: Alignment.center,
          child: const Text('✨', style: TextStyle(fontSize: 20)),
        ),
        const SizedBox(height: 4),
        const Text('Beena',
            style: TextStyle(color: UellowColors.darkBrown,
                fontWeight: FontWeight.w800, fontSize: 10.5)),
      ]),
    );
  }
}

// ─── Loading + Error states ────────────────────────────────────────

class _LoadingState extends StatelessWidget {
  const _LoadingState();
  @override
  Widget build(BuildContext context) {
    return const Center(
      child: CircularProgressIndicator(color: UellowColors.darkBrown),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 80),
        const Center(child: Icon(Icons.cloud_off_outlined,
            size: 56, color: UellowColors.muted)),
        const SizedBox(height: 14),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 30),
          child: Text(message,
              textAlign: TextAlign.center, style: UT.body),
        ),
        const SizedBox(height: 18),
        Center(child: ElevatedButton(
          onPressed: onRetry, child: const Text('Retry'),
        )),
      ],
    );
  }
}
