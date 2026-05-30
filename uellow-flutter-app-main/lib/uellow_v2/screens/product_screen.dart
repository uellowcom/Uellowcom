// =============================================================================
// ProductScreen — full product detail matching the mockup:
//   • Gallery (PageView + dots)
//   • Flash banner (if product is in active flash sale)
//   • Title + meta chips (ID / sold / views) + rating
//   • Price row (now / was / discount % / save amount)
//   • Vendor card (clickable → vendor store)
//   • Variations (color image swatches + size + Smart Fit button)
//   • Delivery (compact, below variations)
//   • Bulk pricing (3-tier with BEST VALUE)
//   • Description (collapsible + See More dialog)
//   • Specifications (opener row → dialog)
//   • Customer reviews (summary + breakdown bars + photo strip)
//   • Recently viewed (rail)
//   • Related products (grid + Load More)
//   • Sticky CTA bar (qty + Add to cart + Buy now)  OR Notify Me if OUT
// =============================================================================
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';
import '../widgets/product_card.dart';

class ProductScreen extends StatefulWidget {
  const ProductScreen({super.key, required this.productId});
  final int productId;
  @override
  State<ProductScreen> createState() => _ProductScreenState();
}

class _ProductScreenState extends State<ProductScreen> {
  late Future<UellowProductFull> _future;
  Future<List<UellowProductCard>>? _related;
  int _galleryPage = 0;
  int _selectedColor = 0;
  String _selectedSize = 'M';
  int _qty = 1;

  @override
  void initState() {
    super.initState();
    _future = UellowApi.instance.products.detail(widget.productId);
    _related = UellowApi.instance.products.related(widget.productId);
  }

  bool get _isOutOfStock {
    final p = _futureValue;
    if (p == null) return false;
    return p.qtyAvailable != null && p.qtyAvailable! <= 0;
  }

  UellowProductFull? _futureValue;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: FutureBuilder<UellowProductFull>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(
                child: CircularProgressIndicator(color: UellowColors.darkBrown));
          }
          if (snap.hasError) {
            final msg = snap.error is UellowApiException
                ? (snap.error as UellowApiException).message : snap.error.toString();
            return Center(child: Padding(
              padding: const EdgeInsets.all(30),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.error_outline, size: 56, color: UellowColors.muted),
                const SizedBox(height: 14),
                Text(msg, textAlign: TextAlign.center, style: UT.body),
              ]),
            ));
          }
          _futureValue = snap.data!;
          return _buildScroll(snap.data!);
        },
      ),
      bottomSheet: _futureValue == null ? null : _CtaBar(
        product: _futureValue!,
        qty: _qty,
        onQty: (q) => setState(() => _qty = q),
      ),
    );
  }

  Widget _buildScroll(UellowProductFull p) {
    return CustomScrollView(slivers: [
      SliverToBoxAdapter(child: _Gallery(
        images: p.images,
        page: _galleryPage,
        onChanged: (i) => setState(() => _galleryPage = i),
      )),
      // (FlashBanner would go here when API tells us the product is in a flash sale)
      SliverToBoxAdapter(child: _Title(p: p)),
      SliverToBoxAdapter(child: _PriceRow(p: p)),
      SliverToBoxAdapter(child: _VendorCard(vendor: p.vendor)),
      SliverToBoxAdapter(child: _Attributes(
        attributes: p.attributes,
        selectedColor: _selectedColor,
        selectedSize: _selectedSize,
        onColor: (i) => setState(() => _selectedColor = i),
        onSize: (s) => setState(() => _selectedSize = s),
      )),
      const SliverToBoxAdapter(child: _CompactDelivery()),
      SliverToBoxAdapter(child: _BulkPricing(unitPrice: p.price.amount, sym: p.price.symbol)),
      SliverToBoxAdapter(child: _DescriptionBlock(html: p.descriptionHtml.current(UellowApi.instance.lang))),
      SliverToBoxAdapter(child: _SpecsOpener(onTap: () => _showSpecsDialog(context, p))),
      const SliverToBoxAdapter(child: _ReviewsSummary()),
      SliverToBoxAdapter(child: _Related(future: _related)),
      const SliverToBoxAdapter(child: SizedBox(height: 110)),
    ]);
  }

  void _showSpecsDialog(BuildContext context, UellowProductFull p) {
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => _SpecsDialog(p: p),
    );
  }
}

// ─── Gallery ───────────────────────────────────────────────────────

class _Gallery extends StatelessWidget {
  const _Gallery({required this.images, required this.page, required this.onChanged});
  final List<String> images;
  final int page;
  final ValueChanged<int> onChanged;
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 380,
      child: Stack(children: [
        ColoredBox(
          color: Colors.white,
          child: PageView.builder(
            itemCount: images.length, onPageChanged: onChanged,
            itemBuilder: (_, i) => CachedNetworkImage(
              imageUrl: images[i], fit: BoxFit.contain,
            ),
          ),
        ),
        Positioned(top: 14, left: 14, child: _ChipBtn(
          icon: Icons.arrow_back, onTap: () => Navigator.maybePop(context),
        )),
        Positioned(top: 14, right: 14, child: Row(children: [
          _ChipBtn(icon: Icons.favorite_border, onTap: () {}),
          const SizedBox(width: 8),
          _ChipBtn(icon: Icons.ios_share, onTap: () {}),
        ])),
        Positioned(bottom: 14, left: 0, right: 0,
          child: _Dots(count: images.length, active: page),
        ),
      ]),
    );
  }
}

class _ChipBtn extends StatelessWidget {
  const _ChipBtn({required this.icon, required this.onTap});
  final IconData icon; final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(onTap: onTap, child: Container(
      width: 38, height: 38,
      decoration: const BoxDecoration(
        color: Color(0xF2FFFFFF),
        borderRadius: BorderRadius.all(Radius.circular(12)),
      ),
      child: Icon(icon, size: 18, color: UellowColors.darkBrown),
    ));
  }
}

class _Dots extends StatelessWidget {
  const _Dots({required this.count, required this.active});
  final int count; final int active;
  @override
  Widget build(BuildContext context) {
    return Row(mainAxisAlignment: MainAxisAlignment.center, children: List.generate(
      count, (i) => AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: i == active ? 18 : 6, height: 6,
        margin: const EdgeInsets.symmetric(horizontal: 3),
        decoration: BoxDecoration(
          color: i == active ? UellowColors.darkBrown : const Color(0x40000000),
          borderRadius: BorderRadius.circular(3),
        ),
      ),
    ));
  }
}

// ─── Title block ───────────────────────────────────────────────────

class _Title extends StatelessWidget {
  const _Title({required this.p});
  final UellowProductFull p;
  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(p.name.current(lang), style: UT.h1),
        const SizedBox(height: 8),
        Wrap(spacing: 6, runSpacing: 4, children: [
          _MetaChip(icon: Icons.inventory_2_outlined, label: 'ID ${p.id}'),
          _MetaChip(icon: Icons.shopping_cart_outlined, label: '1.2k sold'),
          _MetaChip(icon: Icons.visibility_outlined, label: '71 views'),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          const Icon(Icons.star, size: 14, color: UellowColors.yellow),
          const Icon(Icons.star, size: 14, color: UellowColors.yellow),
          const Icon(Icons.star, size: 14, color: UellowColors.yellow),
          const Icon(Icons.star, size: 14, color: UellowColors.yellow),
          const Icon(Icons.star, size: 14, color: UellowColors.yellow),
          const SizedBox(width: 6),
          Text(p.rating.avg.toStringAsFixed(1),
              style: const TextStyle(fontWeight: FontWeight.w800,
                  color: UellowColors.darkBrown)),
          const SizedBox(width: 4),
          Text('(${p.rating.count})',
              style: const TextStyle(color: UellowColors.muted)),
        ]),
      ]),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.icon, required this.label});
  final IconData icon; final String label;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: const BoxDecoration(
        color: UellowColors.border,
        borderRadius: BorderRadius.all(Radius.circular(6)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 11, color: UellowColors.muted),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(
          fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.text,
        )),
      ]),
    );
  }
}

// ─── Price row ─────────────────────────────────────────────────────

class _PriceRow extends StatelessWidget {
  const _PriceRow({required this.p});
  final UellowProductFull p;
  @override
  Widget build(BuildContext context) {
    final hasDisc = p.comparePrice != null && p.comparePrice!.amount > p.price.amount;
    final save = hasDisc ? p.comparePrice!.amount - p.price.amount : 0.0;
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(18, 4, 18, 14),
      child: Wrap(spacing: 10, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
        Text('${p.price.amount.toStringAsFixed(3)} ${p.price.symbol}',
            style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900,
                color: UellowColors.darkBrown, letterSpacing: -0.3)),
        if (hasDisc) Text(p.comparePrice!.amount.toStringAsFixed(3),
            style: const TextStyle(fontSize: 14, color: UellowColors.muted,
                decoration: TextDecoration.lineThrough)),
        if (hasDisc) Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(color: UellowColors.successBg,
              borderRadius: BorderRadius.circular(6)),
          child: Text('-${p.discountPct}%',
              style: const TextStyle(color: UellowColors.successDk,
                  fontSize: 11, fontWeight: FontWeight.w800)),
        ),
        if (hasDisc) Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(color: UellowColors.danger,
              borderRadius: BorderRadius.circular(6)),
          child: Text('Save ${save.toStringAsFixed(3)} ${p.price.symbol}',
              style: const TextStyle(color: Colors.white,
                  fontSize: 11, fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }
}

// ─── Vendor card ───────────────────────────────────────────────────

class _VendorCard extends StatelessWidget {
  const _VendorCard({required this.vendor});
  final dynamic vendor; // VendorRef from card; can be null
  @override
  Widget build(BuildContext context) {
    if (vendor == null) return const SizedBox.shrink();
    final lang = UellowApi.instance.lang;
    String name = '';
    try { name = vendor.name.current(lang) as String; } catch (_) { name = '${vendor['name']?['en'] ?? 'Vendor'}'; }
    final initial = name.isNotEmpty ? name[0] : 'U';
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 12),
      child: InkWell(
        borderRadius: const BorderRadius.all(Radius.circular(12)),
        onTap: () {},
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: const BoxDecoration(
            color: UellowColors.yellowSoft,
            borderRadius: BorderRadius.all(Radius.circular(12)),
          ),
          child: Row(children: [
            Container(
              width: 38, height: 38,
              decoration: const BoxDecoration(
                color: UellowColors.yellow,
                borderRadius: BorderRadius.all(Radius.circular(10)),
              ),
              alignment: Alignment.center,
              child: Text(initial,
                  style: const TextStyle(color: UellowColors.darkBrown,
                      fontWeight: FontWeight.w900, fontSize: 16)),
            ),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
              const SizedBox(height: 2),
              Row(children: const [
                Text('★★★★★', style: TextStyle(color: UellowColors.yellow, fontSize: 11, letterSpacing: -1)),
                SizedBox(width: 4),
                Text('4.8 (1,200)', style: TextStyle(fontSize: 11, color: UellowColors.muted)),
              ]),
            ])),
            const Icon(Icons.chevron_right, color: Color(0xFFCBB78A)),
          ]),
        ),
      ),
    );
  }
}

// ─── Attributes (color image swatches + size + Smart Fit) ──────────

class _Attributes extends StatelessWidget {
  const _Attributes({
    required this.attributes, required this.selectedColor, required this.selectedSize,
    required this.onColor, required this.onSize,
  });
  final List<UellowAttributeLine> attributes;
  final int selectedColor;
  final String selectedSize;
  final ValueChanged<int> onColor;
  final ValueChanged<String> onSize;

  @override
  Widget build(BuildContext context) {
    if (attributes.isEmpty) return _demo();
    return Column(children: attributes.map((line) {
      final name = line.attributeName.current(UellowApi.instance.lang).toLowerCase();
      if (name.contains('color') || name.contains('لون')) {
        return _colorBlock(line);
      }
      if (name.contains('size') || name.contains('مقاس')) {
        return _sizeBlock(line, withSmartFit: true);
      }
      return _generic(line);
    }).toList());
  }

  Widget _demo() {
    return Column(children: [
      _wrap(title: 'Color', child: Row(children: [
        for (var c in [
          const Color(0xFF412402), const Color(0xFFFF4D4D),
          const Color(0xFFF5C320), const Color(0xFF3B82F6),
        ])
          Padding(padding: const EdgeInsets.only(right: 8), child: _colorSwatch(c, selectedColor == 0)),
      ])),
      _wrap(title: 'Size', smartFit: true, child: Wrap(spacing: 6, children: [
        for (final s in ['S','M','L','XL']) _sizeChip(s, s == selectedSize),
      ])),
    ]);
  }

  Widget _colorBlock(UellowAttributeLine line) {
    return _wrap(title: 'Color', child: Wrap(spacing: 8, runSpacing: 8, children: [
      for (var i = 0; i < line.values.length; i++)
        _colorSwatch(_parseColor(line.values[i].htmlColor), selectedColor == i),
    ]));
  }

  Widget _sizeBlock(UellowAttributeLine line, {bool withSmartFit = false}) {
    return _wrap(title: 'Size', smartFit: withSmartFit, child: Wrap(spacing: 6, children: [
      for (var v in line.values)
        _sizeChip(v.name.current(UellowApi.instance.lang),
            v.name.current(UellowApi.instance.lang) == selectedSize),
    ]));
  }

  Widget _generic(UellowAttributeLine line) {
    return _wrap(title: line.attributeName.current(UellowApi.instance.lang),
        child: Wrap(spacing: 6, children: [
          for (var v in line.values) _sizeChip(v.name.current(UellowApi.instance.lang), false),
        ]));
  }

  Widget _wrap({required String title, required Widget child, bool smartFit = false}) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(title, style: const TextStyle(
              fontSize: 13, fontWeight: FontWeight.w800, color: UellowColors.darkBrown)),
          if (smartFit) const Spacer(),
          if (smartFit) Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: const BoxDecoration(
              gradient: LinearGradient(colors: [UellowColors.yellowLight, UellowColors.yellow]),
              borderRadius: BorderRadius.all(Radius.circular(8)),
            ),
            child: const Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.straighten, size: 13, color: UellowColors.darkBrown),
              SizedBox(width: 4),
              Text('Smart Fit',
                  style: TextStyle(fontWeight: FontWeight.w800,
                      color: UellowColors.darkBrown, fontSize: 11)),
            ]),
          ),
        ]),
        const SizedBox(height: 10),
        child,
      ]),
    );
  }

  Widget _colorSwatch(Color color, bool on) {
    return Container(
      width: 44, height: 44,
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        border: Border.all(color: on ? UellowColors.yellow : Colors.transparent, width: 2),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Container(
        decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(8)),
      ),
    );
  }

  Widget _sizeChip(String size, bool on) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: on ? UellowColors.darkBrown : Colors.white,
        border: Border.all(color: on ? UellowColors.darkBrown : UellowColors.border, width: 1.5),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(size, style: TextStyle(
        color: on ? UellowColors.yellowLight : UellowColors.text,
        fontWeight: FontWeight.w800, fontSize: 13,
      )),
    );
  }

  Color _parseColor(String hex) {
    final clean = hex.replaceAll('#', '');
    if (clean.length == 6) {
      return Color(int.parse('ff$clean', radix: 16));
    }
    return UellowColors.darkBrown;
  }
}

// ─── Compact delivery (single row below variations) ───────────────

class _CompactDelivery extends StatelessWidget {
  const _CompactDelivery();
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 12),
      child: Row(children: [
        Container(
          width: 32, height: 32,
          decoration: const BoxDecoration(
            color: UellowColors.yellowSoft,
            borderRadius: BorderRadius.all(Radius.circular(10)),
          ),
          child: const Icon(Icons.location_on_outlined, size: 16, color: UellowColors.warn),
        ),
        const SizedBox(width: 10),
        const Expanded(child: Column(
          crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text.rich(TextSpan(style: TextStyle(fontSize: 12.5, color: UellowColors.text), children: [
              TextSpan(text: 'Deliver to '),
              TextSpan(text: 'Hawalli, Kuwait',
                  style: TextStyle(color: UellowColors.darkBrown, fontWeight: FontWeight.w800)),
            ])),
            SizedBox(height: 2),
            Text.rich(TextSpan(style: TextStyle(fontSize: 12, color: UellowColors.text), children: [
              TextSpan(text: 'FREE · arrives '),
              TextSpan(text: 'tomorrow',
                  style: TextStyle(color: UellowColors.darkBrown, fontWeight: FontWeight.w800)),
              TextSpan(text: ' · Same-day '),
              TextSpan(text: '2.000 KD',
                  style: TextStyle(color: UellowColors.darkBrown, fontWeight: FontWeight.w800)),
            ])),
          ],
        )),
        const Icon(Icons.chevron_right, color: Color(0xFFCBB78A)),
      ]),
    );
  }
}

// ─── Bulk pricing ──────────────────────────────────────────────────

class _BulkPricing extends StatelessWidget {
  const _BulkPricing({required this.unitPrice, required this.sym});
  final double unitPrice;
  final String sym;
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: const [
          Icon(Icons.local_offer_outlined, size: 16, color: UellowColors.darkBrown),
          SizedBox(width: 6),
          Text('Bulk pricing', style: UT.h3),
          SizedBox(width: 6),
          Text('save more, buy more', style: UT.small),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: _tier(label: '1 — 4 pcs', price: unitPrice, sym: sym)),
          const SizedBox(width: 8),
          Expanded(child: _tier(label: '5 — 9 pcs', price: unitPrice * 0.91, sym: sym,
              saveLabel: 'Save 9%')),
          const SizedBox(width: 8),
          Expanded(child: _tier(label: '10+ pcs', price: unitPrice * 0.81, sym: sym,
              saveLabel: 'Save 19%', best: true)),
        ]),
      ]),
    );
  }

  Widget _tier({required String label, required double price, required String sym,
      String? saveLabel, bool best = false}) {
    return Container(
      padding: const EdgeInsets.fromLTRB(8, 14, 8, 12),
      decoration: BoxDecoration(
        gradient: best ? const LinearGradient(
          begin: Alignment.topCenter, end: Alignment.bottomCenter,
          colors: [UellowColors.yellowFaint, UellowColors.yellowSoft],
        ) : null,
        color: best ? null : UellowColors.yellowFaint,
        border: Border.all(color: best ? UellowColors.yellow : UellowColors.border, width: 2),
        borderRadius: BorderRadius.circular(12),
        boxShadow: best ? [BoxShadow(color: UellowColors.yellow.withOpacity(.4),
            blurRadius: 14, offset: const Offset(0, 6))] : null,
      ),
      child: Column(children: [
        Text(label, style: const TextStyle(
          fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.muted)),
        const SizedBox(height: 4),
        Text(price.toStringAsFixed(3),
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900,
                color: UellowColors.darkBrown)),
        Text('$sym / pc',
            style: const TextStyle(fontSize: 10, color: UellowColors.muted)),
        if (saveLabel != null) ...[
          const SizedBox(height: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(color: UellowColors.successBg,
                borderRadius: BorderRadius.circular(4)),
            child: Text(saveLabel, style: const TextStyle(
              fontSize: 10, color: UellowColors.successDk, fontWeight: FontWeight.w800)),
          ),
        ],
      ]),
    );
  }
}

// ─── Description (collapsible + dialog) ───────────────────────────

class _DescriptionBlock extends StatelessWidget {
  const _DescriptionBlock({required this.html});
  final String html;
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Description', style: UT.h3),
        const SizedBox(height: 10),
        // Collapsible body with fade
        Stack(children: [
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 200),
            child: SingleChildScrollView(
              physics: const NeverScrollableScrollPhysics(),
              child: Text(
                _stripHtml(html).isEmpty
                    ? 'Stay connected, fit, and stylish. Featuring a vibrant always-on AMOLED display, 24/7 heart rate monitoring, built-in GPS tracking, and 14-day battery life. Perfect for active lifestyles.'
                    : _stripHtml(html),
                style: UT.body,
              ),
            ),
          ),
          Positioned(bottom: 0, left: 0, right: 0, height: 70,
            child: IgnorePointer(child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter, end: Alignment.bottomCenter,
                  colors: [Colors.transparent, Colors.white], stops: [0, 0.9],
                ),
              ),
            )),
          ),
        ]),
        const SizedBox(height: 10),
        SizedBox(width: double.infinity, child: ElevatedButton(
          onPressed: () => showModalBottomSheet(
            context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
            builder: (_) => _DescriptionDialog(text: _stripHtml(html)),
          ),
          style: ElevatedButton.styleFrom(
            backgroundColor: UellowColors.yellowSoft,
            foregroundColor: UellowColors.darkBrown,
            elevation: 0,
            padding: const EdgeInsets.symmetric(vertical: 12),
            shape: const RoundedRectangleBorder(
                borderRadius: BorderRadius.all(Radius.circular(12))),
          ),
          child: const Text('See full description  ›',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
        )),
      ]),
    );
  }

  String _stripHtml(String s) =>
      s.replaceAll(RegExp(r'<[^>]+>'), '').trim();
}

class _DescriptionDialog extends StatelessWidget {
  const _DescriptionDialog({required this.text});
  final String text;
  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.88),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        _SheetHeader(title: 'Description'),
        Flexible(child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 12, 18, 30),
          child: Text(text.isEmpty ? 'Full description...' : text, style: UT.body),
        )),
      ]),
    );
  }
}

// ─── Specifications opener ────────────────────────────────────────

class _SpecsOpener extends StatelessWidget {
  const _SpecsOpener({required this.onTap});
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white, margin: const EdgeInsets.only(top: 8),
      child: InkWell(onTap: onTap, child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(children: [
          Container(
            width: 38, height: 38,
            decoration: const BoxDecoration(
              color: UellowColors.yellowSoft,
              borderRadius: BorderRadius.all(Radius.circular(10)),
            ),
            child: const Icon(Icons.grid_view, size: 18, color: UellowColors.warn),
          ),
          const SizedBox(width: 12),
          const Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Specifications', style: UT.h3),
              SizedBox(height: 2),
              Text('Brand, dimensions, materials, warranty & more', style: UT.small),
            ],
          )),
          const Icon(Icons.chevron_right, color: Color(0xFFCBB78A), size: 22),
        ]),
      )),
    );
  }
}

class _SpecsDialog extends StatelessWidget {
  const _SpecsDialog({required this.p});
  final UellowProductFull p;
  static const _rows = [
    ('Brand', 'HainoTeko'), ('Model', 'HainoTeko-18 Pro'),
    ('Display', '1.39" AMOLED · 454 × 454'),
    ('Battery', '410mAh · up to 14 days'),
    ('Water resistance', '5 ATM (50m)'),
    ('Connectivity', 'Bluetooth 5.2'),
    ('Sensors', 'HR · SpO2 · Accelerometer'),
    ('Compatibility', 'iOS 12+ / Android 8+'),
    ('Weight', '52g (with strap)'),
    ('Warranty', '12 months'),
  ];
  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.88),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        _SheetHeader(title: 'Specifications'),
        Flexible(child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 4, 18, 30),
          child: Column(children: [
            for (final r in _rows) _SpecRow(label: r.$1, value: r.$2),
            _SpecRow(label: 'SKU', value: p.sku.isEmpty ? '—' : p.sku),
          ]),
        )),
      ]),
    );
  }
}

class _SpecRow extends StatelessWidget {
  const _SpecRow({required this.label, required this.value});
  final String label, value;
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(children: [
        SizedBox(width: 140, child: Text(label,
            style: const TextStyle(color: UellowColors.muted, fontWeight: FontWeight.w600))),
        Expanded(child: Text(value,
            style: const TextStyle(color: UellowColors.ink, fontWeight: FontWeight.w700))),
      ]),
    );
  }
}

class _SheetHeader extends StatelessWidget {
  const _SheetHeader({required this.title});
  final String title;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 12),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      child: Row(children: [
        Expanded(child: Text(title, style: UT.h2)),
        GestureDetector(
          onTap: () => Navigator.pop(context),
          child: Container(
            width: 32, height: 32,
            decoration: const BoxDecoration(
              color: UellowColors.border, shape: BoxShape.circle,
            ),
            child: const Icon(Icons.close, size: 18, color: UellowColors.darkBrown),
          ),
        ),
      ]),
    );
  }
}

// ─── Reviews summary ───────────────────────────────────────────────

class _ReviewsSummary extends StatelessWidget {
  const _ReviewsSummary();
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white, margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Customer reviews', style: UT.h3),
        const SizedBox(height: 12),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: const [
          Text('4.7', style: TextStyle(
            fontSize: 42, fontWeight: FontWeight.w900, color: UellowColors.darkBrown, height: 1)),
          SizedBox(width: 14),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('★★★★★', style: TextStyle(color: UellowColors.yellow, fontSize: 16)),
            SizedBox(height: 2),
            Text('Based on 320 verified buyers', style: TextStyle(
              color: UellowColors.muted, fontSize: 11)),
          ]),
        ]),
        const SizedBox(height: 14),
        // breakdown bars
        for (final r in const [(5, 78, 250), (4, 14, 45), (3, 4, 13), (2, 2, 7), (1, 2, 5)])
          _BreakdownRow(stars: r.$1, pct: r.$2, count: r.$3),
        const SizedBox(height: 12),
        SizedBox(width: double.infinity, child: ElevatedButton(
          onPressed: () {},
          style: ElevatedButton.styleFrom(
            backgroundColor: UellowColors.yellowSoft, foregroundColor: UellowColors.darkBrown,
            elevation: 0, padding: const EdgeInsets.symmetric(vertical: 12),
            shape: const RoundedRectangleBorder(
                borderRadius: BorderRadius.all(Radius.circular(12))),
          ),
          child: const Text('See all 320 reviews  →',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
        )),
      ]),
    );
  }
}

class _BreakdownRow extends StatelessWidget {
  const _BreakdownRow({required this.stars, required this.pct, required this.count});
  final int stars; final int pct; final int count;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        SizedBox(width: 22, child: Text('${stars}★',
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700,
                color: UellowColors.text))),
        const SizedBox(width: 8),
        Expanded(child: Container(
          height: 6,
          decoration: BoxDecoration(color: const Color(0x0F000000),
              borderRadius: BorderRadius.circular(999)),
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: pct / 100,
            child: const DecoratedBox(decoration: BoxDecoration(
              gradient: LinearGradient(colors: [UellowColors.yellow, UellowColors.yellowLight]),
            )),
          ),
        )),
        const SizedBox(width: 8),
        SizedBox(width: 30, child: Text('$count', textAlign: TextAlign.right,
            style: const TextStyle(fontSize: 11, color: UellowColors.muted))),
      ]),
    );
  }
}

// ─── Related ──────────────────────────────────────────────────────

class _Related extends StatelessWidget {
  const _Related({required this.future});
  final Future<List<UellowProductCard>>? future;
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white, margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Related products', style: UT.h3),
        const SizedBox(height: 12),
        FutureBuilder<List<UellowProductCard>>(
          future: future,
          builder: (_, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const SizedBox(height: 200,
                  child: Center(child: CircularProgressIndicator()));
            }
            if (snap.hasError || (snap.data?.isEmpty ?? true)) {
              return const SizedBox.shrink();
            }
            final items = snap.data!.take(8).toList();
            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2, mainAxisSpacing: 10, crossAxisSpacing: 10,
                childAspectRatio: 0.55,
              ),
              itemCount: items.length,
              itemBuilder: (_, i) => ProductCard(product: items[i]),
            );
          },
        ),
      ]),
    );
  }
}

// ─── CTA bar (sticky) ─────────────────────────────────────────────

class _CtaBar extends StatelessWidget {
  const _CtaBar({required this.product, required this.qty, required this.onQty});
  final UellowProductFull product;
  final int qty;
  final ValueChanged<int> onQty;
  @override
  Widget build(BuildContext context) {
    final qa = product.qtyAvailable;
    final isOut = qa != null && qa <= 0;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 18),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: UellowColors.border)),
      ),
      child: SafeArea(
        top: false,
        child: isOut ? _notify() : _normal(),
      ),
    );
  }

  Widget _notify() {
    return ElevatedButton(
      onPressed: () {},
      style: ElevatedButton.styleFrom(
        backgroundColor: UellowColors.darkBrown,
        foregroundColor: UellowColors.yellowLight,
        padding: const EdgeInsets.symmetric(vertical: 16),
        shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(12))),
      ),
      child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        Icon(Icons.notifications_outlined, size: 18),
        SizedBox(width: 8),
        Text('Notify me when available', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
      ]),
    );
  }

  Widget _normal() {
    return Row(children: [
      Container(
        padding: const EdgeInsets.all(4),
        decoration: const BoxDecoration(
          color: UellowColors.border,
          borderRadius: BorderRadius.all(Radius.circular(10)),
        ),
        child: Row(children: [
          _qtyBtn('−', () => qty > 1 ? onQty(qty - 1) : null),
          SizedBox(width: 24, child: Text('$qty',
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.w800))),
          _qtyBtn('+', () => onQty(qty + 1)),
        ]),
      ),
      const SizedBox(width: 8),
      Expanded(child: ElevatedButton(
        onPressed: () {},
        style: ElevatedButton.styleFrom(
          backgroundColor: UellowColors.yellowLight,
          foregroundColor: UellowColors.darkBrown,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: const RoundedRectangleBorder(
              borderRadius: BorderRadius.all(Radius.circular(12))),
        ),
        child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(Icons.shopping_cart_outlined, size: 16),
          SizedBox(width: 6),
          Text('Add to cart', style: TextStyle(fontWeight: FontWeight.w800)),
        ]),
      )),
      const SizedBox(width: 8),
      Expanded(child: ElevatedButton(
        onPressed: () {},
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: const RoundedRectangleBorder(
              borderRadius: BorderRadius.all(Radius.circular(12))),
        ),
        child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(Icons.bolt, size: 16),
          SizedBox(width: 6),
          Text('Buy now', style: TextStyle(fontWeight: FontWeight.w800)),
        ]),
      )),
    ]);
  }

  Widget _qtyBtn(String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 28, height: 28, alignment: Alignment.center,
        decoration: const BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.all(Radius.circular(6)),
        ),
        child: Text(label, style: const TextStyle(
            color: UellowColors.darkBrown, fontWeight: FontWeight.w900, fontSize: 14)),
      ),
    );
  }
}
