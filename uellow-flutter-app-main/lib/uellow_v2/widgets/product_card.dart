// =============================================================================
// ProductCard — the foundation tile used in home rails, category grids,
// wishlist, vendor store, related products, search results.
//
// Matches the mockup exactly: discount badge on image, share/heart on
// bottom-right of image, flash banner under image when in flash sale,
// price + discount %, was-price, rating + count in parens, delivery
// badges, bottom row with Save icon (left) + Availability pill (right).
// =============================================================================
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../router/uellow_router.dart';
import '../theme/uellow_theme.dart';

class ProductCard extends StatelessWidget {
  const ProductCard({
    super.key,
    required this.product,
    this.showStockLabel = true,
    this.inFlashSale = false,
    this.onTap,
  });

  final UellowProductCard product;
  final bool showStockLabel;
  final bool inFlashSale;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final lang = UellowApi.instance.lang;
    final hasDiscount = product.comparePrice != null &&
        product.comparePrice!.amount > product.price.amount;
    final discountPct = product.discountPct;
    final saveAmount = hasDiscount
        ? product.comparePrice!.amount - product.price.amount : 0.0;

    return GestureDetector(
      onTap: onTap ?? () => UellowRouter.goProduct(context, product.id),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: UellowRadius.all_lg,
          border: Border.all(color: UellowColors.border),
          boxShadow: const [
            BoxShadow(color: Color(0x0D000000), blurRadius: 4, offset: Offset(0, 1)),
          ],
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _Image(product: product, hasDiscount: hasDiscount, discountPct: discountPct),
            if (inFlashSale) const _FlashBanner(),
            Padding(
              padding: const EdgeInsets.all(10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Name (2 lines, ellipsis)
                  Text(
                    product.name.current(lang),
                    maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 12.5, height: 1.35, color: UellowColors.ink,
                    ),
                  ),
                  const SizedBox(height: 6),
                  // Price + discount pill
                  Row(
                    children: [
                      Text(
                        '${product.price.amount.toStringAsFixed(3)} ',
                        style: const TextStyle(
                          fontSize: 17, fontWeight: FontWeight.w900,
                          color: UellowColors.darkBrown, letterSpacing: -0.3,
                        ),
                      ),
                      Text(
                        product.price.symbol,
                        style: const TextStyle(
                          fontSize: 11, fontWeight: FontWeight.w700,
                          color: UellowColors.muted,
                        ),
                      ),
                      const Spacer(),
                      if (discountPct > 0) _DiscountPill(pct: discountPct),
                    ],
                  ),
                  // Was-price (strikethrough)
                  if (hasDiscount) Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      '${product.comparePrice!.amount.toStringAsFixed(3)} ${product.comparePrice!.symbol}',
                      style: const TextStyle(
                        fontSize: 11.5, color: UellowColors.muted,
                        decoration: TextDecoration.lineThrough,
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  _RatingRow(rating: product.rating),
                  const SizedBox(height: 4),
                  // Bottom row: Save icon (left) | Availability pill (right)
                  Container(
                    margin: const EdgeInsets.only(top: 6),
                    padding: const EdgeInsets.only(top: 6),
                    decoration: const BoxDecoration(
                      border: Border(top: BorderSide(
                        color: UellowColors.border, style: BorderStyle.solid, width: 1,
                      )),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        if (hasDiscount)
                          _SaveIcon(amount: saveAmount, currency: product.price.symbol)
                        else
                          const Text('Available now',
                              style: TextStyle(fontSize: 10, color: UellowColors.muted)),
                        if (showStockLabel) _AvailPill(product: product),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Image with badges + bottom-right actions ─────────────────────

class _Image extends StatelessWidget {
  const _Image({required this.product, required this.hasDiscount, required this.discountPct});
  final UellowProductCard product;
  final bool hasDiscount;
  final int discountPct;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1,
      child: Stack(
        fit: StackFit.expand,
        children: [
          ColoredBox(
            color: const Color(0xFFFAFAFA),
            child: CachedNetworkImage(
              imageUrl: product.image,
              fit: BoxFit.cover,
              placeholder: (_, __) => const ColoredBox(color: UellowColors.border),
              errorWidget: (_, __, ___) => const ColoredBox(color: UellowColors.border),
            ),
          ),
          // Discount badge top-left
          if (discountPct > 0) Positioned(
            top: 8, left: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: UellowColors.danger,
                borderRadius: BorderRadius.circular(6),
                boxShadow: [BoxShadow(
                  color: UellowColors.danger.withOpacity(.5),
                  blurRadius: 8, offset: const Offset(0, 3),
                )],
              ),
              child: Text(
                '-$discountPct%',
                style: const TextStyle(
                  color: Colors.white, fontSize: 10,
                  fontWeight: FontWeight.w800, letterSpacing: 0.3,
                ),
              ),
            ),
          ),
          // Bottom-right action buttons
          Positioned(
            bottom: 8, right: 8,
            child: Row(
              children: [
                _ImgAction(icon: Icons.favorite_border, onTap: () {}),
                const SizedBox(width: 6),
                _ImgAction(icon: Icons.ios_share, onTap: () {}),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ImgAction extends StatelessWidget {
  const _ImgAction({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 30, height: 30,
        decoration: const BoxDecoration(
          color: Color(0xF2FFFFFF),
          shape: BoxShape.circle,
          boxShadow: [BoxShadow(color: Color(0x1F000000),
              blurRadius: 6, offset: Offset(0, 2))],
        ),
        child: Icon(icon, size: 14, color: UellowColors.muted),
      ),
    );
  }
}

class _FlashBanner extends StatelessWidget {
  const _FlashBanner();
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: const BoxDecoration(gradient: UellowColors.heroFlash),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.bolt, size: 12, color: Colors.white),
              SizedBox(width: 3),
              Text('FLASH',
                  style: TextStyle(color: Colors.white, fontSize: 10,
                      fontWeight: FontWeight.w900, letterSpacing: 0.3)),
            ],
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(.3),
              borderRadius: BorderRadius.circular(4),
            ),
            child: const Text('02:14:37',
                style: TextStyle(color: Colors.white, fontSize: 10,
                    fontFamily: 'monospace', letterSpacing: 0.5)),
          ),
        ],
      ),
    );
  }
}

class _DiscountPill extends StatelessWidget {
  const _DiscountPill({required this.pct});
  final int pct;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: UellowColors.dangerBg,
        borderRadius: BorderRadius.circular(5),
      ),
      child: Text(
        '-$pct%',
        style: const TextStyle(
          color: UellowColors.dangerDk, fontSize: 10,
          fontWeight: FontWeight.w900, letterSpacing: 0.3,
        ),
      ),
    );
  }
}

class _RatingRow extends StatelessWidget {
  const _RatingRow({required this.rating});
  final UellowRating rating;
  @override
  Widget build(BuildContext context) {
    if (rating.count == 0) return const SizedBox.shrink();
    return Row(
      children: [
        const Icon(Icons.star, size: 12, color: UellowColors.yellow),
        const SizedBox(width: 2),
        Text(rating.avg.toStringAsFixed(1),
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                color: UellowColors.darkBrown)),
        const SizedBox(width: 3),
        Text('(${rating.count})',
            style: const TextStyle(fontSize: 10.5, color: UellowColors.muted)),
      ],
    );
  }
}

class _SaveIcon extends StatelessWidget {
  const _SaveIcon({required this.amount, required this.currency});
  final double amount;
  final String currency;
  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.local_offer_outlined, size: 11, color: UellowColors.success),
        const SizedBox(width: 3),
        Text(
          amount.toStringAsFixed(3),
          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900,
              color: UellowColors.successDk),
        ),
        const SizedBox(width: 2),
        Text(currency,
            style: const TextStyle(fontSize: 10, color: UellowColors.successDk)),
      ],
    );
  }
}

class _AvailPill extends StatelessWidget {
  const _AvailPill({required this.product});
  final UellowProductCard product;
  @override
  Widget build(BuildContext context) {
    final qty = product.qtyAvailable;
    Color bg, fg; String text;
    if (qty != null && qty <= 0) {
      bg = UellowColors.dangerBg; fg = UellowColors.dangerDk; text = 'OUT';
    } else if (qty != null && qty <= 5) {
      bg = UellowColors.warnBg; fg = UellowColors.warn; text = 'Only $qty';
    } else {
      bg = UellowColors.successBg; fg = UellowColors.successDk; text = 'Available';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(4)),
      child: Text(text,
          style: TextStyle(color: fg, fontSize: 9.5,
              fontWeight: FontWeight.w900, letterSpacing: 0.5)),
    );
  }
}
