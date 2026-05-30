// =============================================================================
// AccountScreen — profile header + loyalty/wallet banners + orders grid +
// wishlist/recently-viewed sections + quick tiles + social + menu.
// Single source: /api/mobile/v2/account/overview returns ALL of this.
// =============================================================================
import 'package:flutter/material.dart';

import '../theme/uellow_theme.dart';

class AccountScreen extends StatelessWidget {
  const AccountScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: ListView(padding: EdgeInsets.zero, children: [
        const _ProfileHeader(),
        const _BannersRow(),
        _SectionCard(title: 'My Orders', trailingText: 'See all ›', child: _OrdersGrid()),
        const _RecentOrderCard(),
        _SectionCard(
          title: 'My Wishlist (12)',
          titleIcon: Icons.favorite_border, trailingText: 'See all ›',
          child: _ThumbRow(items: const ['W1','W2','W3','W4','W5']),
        ),
        _SectionCard(
          title: 'Recently viewed',
          titleIcon: Icons.access_time, trailingText: 'Clear all',
          child: _ThumbRow(items: const ['V1','V2','V3','V4']),
        ),
        _SectionCard(title: '', child: _ActionTiles()),
        _SectionCard(title: 'Follow Uellow', child: _SocialRow()),
        const _MenuList(),
        const _SignOutBtn(),
        const _Version(),
      ]),
    );
  }
}

// ─── Profile header ────────────────────────────────────────────────

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader();
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 16),
      child: Row(children: [
        Container(
          width: 64, height: 64,
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [Color(0xFFFFE066), UellowColors.yellow]),
            borderRadius: BorderRadius.all(Radius.circular(18)),
          ),
          alignment: Alignment.center,
          child: const Text('A', style: TextStyle(
              fontSize: 26, fontWeight: FontWeight.w900, color: UellowColors.darkBrown)),
        ),
        const SizedBox(width: 14),
        const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Ali Mohammed', style: UT.h1),
          SizedBox(height: 2),
          Text('ali@uellow.com · +965 9999 0000',
              style: TextStyle(fontSize: 12, color: UellowColors.muted)),
        ])),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: const BoxDecoration(
            color: UellowColors.border,
            borderRadius: BorderRadius.all(Radius.circular(10)),
          ),
          child: const Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.edit_outlined, size: 12, color: UellowColors.darkBrown),
            SizedBox(width: 4),
            Text('Edit', style: TextStyle(
                color: UellowColors.darkBrown, fontSize: 12, fontWeight: FontWeight.w700)),
          ]),
        ),
      ]),
    );
  }
}

// ─── Loyalty + Wallet banners ─────────────────────────────────────

class _BannersRow extends StatelessWidget {
  const _BannersRow();
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 160,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        children: [
          _LoyaltyBanner(),
          const SizedBox(width: 10),
          _WalletBanner(),
        ],
      ),
    );
  }
}

class _LoyaltyBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 280,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: const BoxDecoration(
          gradient: UellowColors.heroLoyalty,
          borderRadius: BorderRadius.all(Radius.circular(18)),
        ),
        child: Stack(children: [
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('LOYALTY POINTS',
                style: TextStyle(color: UellowColors.darkBrown, fontSize: 11,
                    fontWeight: FontWeight.w800, letterSpacing: 0.5)),
            const SizedBox(height: 6),
            const Text('2,450',
                style: TextStyle(fontSize: 30, fontWeight: FontWeight.w900,
                    color: UellowColors.darkBrown, height: 1)),
            const SizedBox(height: 2),
            const Text('= 24.500 KD redeem value',
                style: TextStyle(color: UellowColors.darkBrown, fontSize: 11)),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
              decoration: const BoxDecoration(
                color: UellowColors.darkBrown,
                borderRadius: BorderRadius.all(Radius.circular(999)),
              ),
              child: const Text('⭐ SILVER TIER',
                  style: TextStyle(color: UellowColors.yellowLight,
                      fontSize: 10, fontWeight: FontWeight.w800)),
            ),
            const SizedBox(height: 12),
            Container(
              height: 6,
              decoration: BoxDecoration(
                color: const Color(0x33412402),
                borderRadius: BorderRadius.circular(999),
              ),
              child: FractionallySizedBox(
                alignment: Alignment.centerLeft, widthFactor: 0.48,
                child: const DecoratedBox(decoration: BoxDecoration(
                  color: UellowColors.darkBrown,
                  borderRadius: BorderRadius.all(Radius.circular(999)),
                )),
              ),
            ),
            const SizedBox(height: 4),
            const Text('2,550 pts to reach GOLD',
                style: TextStyle(color: Color(0xFF5B3C00), fontSize: 10)),
          ]),
          const Positioned(right: 0, bottom: 0,
            child: _BannerCta(label: 'Use  →',
                bg: UellowColors.darkBrown, fg: UellowColors.yellowLight),
          ),
        ]),
      ),
    );
  }
}

class _WalletBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 280,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: const BoxDecoration(
          gradient: UellowColors.heroWallet,
          borderRadius: BorderRadius.all(Radius.circular(18)),
        ),
        child: Stack(children: [
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('UELLOW WALLET',
                style: TextStyle(color: UellowColors.yellowLight, fontSize: 11,
                    fontWeight: FontWeight.w800, letterSpacing: 0.5)),
            const SizedBox(height: 6),
            const Text.rich(TextSpan(children: [
              TextSpan(text: '12.750',
                  style: TextStyle(fontSize: 30, fontWeight: FontWeight.w900,
                      color: UellowColors.yellowLight, height: 1)),
              TextSpan(text: ' KD',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700,
                      color: UellowColors.yellowLight)),
            ])),
            const SizedBox(height: 2),
            const Text('Last top-up: 3 days ago · KNET',
                style: TextStyle(color: UellowColors.yellowLight, fontSize: 11)),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
              decoration: const BoxDecoration(
                color: UellowColors.yellowLight,
                borderRadius: BorderRadius.all(Radius.circular(999)),
              ),
              child: const Text('SECURE',
                  style: TextStyle(color: UellowColors.darkBrown,
                      fontSize: 10, fontWeight: FontWeight.w800)),
            ),
            const SizedBox(height: 12),
            Container(
              height: 6,
              decoration: BoxDecoration(
                color: const Color(0x40FFD340),
                borderRadius: BorderRadius.circular(999),
              ),
              child: FractionallySizedBox(
                alignment: Alignment.centerLeft, widthFactor: 0.32,
                child: const DecoratedBox(decoration: BoxDecoration(
                  color: UellowColors.yellowLight,
                  borderRadius: BorderRadius.all(Radius.circular(999)),
                )),
              ),
            ),
            const SizedBox(height: 4),
            const Text('3 transactions this month',
                style: TextStyle(color: UellowColors.yellowLight, fontSize: 10)),
          ]),
          const Positioned(right: 0, bottom: 0,
            child: _BannerCta(label: 'Top up  →',
                bg: UellowColors.yellowLight, fg: UellowColors.darkBrown),
          ),
        ]),
      ),
    );
  }
}

class _BannerCta extends StatelessWidget {
  const _BannerCta({required this.label, required this.bg, required this.fg});
  final String label;
  final Color bg, fg;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(10)),
      child: Text(label, style: TextStyle(color: fg, fontWeight: FontWeight.w700, fontSize: 11)),
    );
  }
}

// ─── Section card wrapper ─────────────────────────────────────────

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title, required this.child, this.trailingText, this.titleIcon,
  });
  final String title;
  final Widget child;
  final String? trailingText;
  final IconData? titleIcon;
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 8),
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(16)),
        boxShadow: [BoxShadow(color: Color(0x0D000000), blurRadius: 3, offset: Offset(0, 1))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (title.isNotEmpty) Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(children: [
            if (titleIcon != null) Padding(
              padding: const EdgeInsets.only(right: 6),
              child: Icon(titleIcon, size: 14, color: UellowColors.darkBrown),
            ),
            Expanded(child: Text(title, style: UT.h3)),
            if (trailingText != null) Text(trailingText!,
                style: const TextStyle(fontSize: 11, color: UellowColors.text,
                    fontWeight: FontWeight.w700)),
          ]),
        ),
        child,
      ]),
    );
  }
}

// ─── Orders grid (6 tiles) ────────────────────────────────────────

class _OrdersGrid extends StatelessWidget {
  static const _states = [
    (Icons.inventory_2_outlined, 'Pending', 2),
    (Icons.check_circle_outline, 'Paid', 1),
    (Icons.card_giftcard, 'Packing', 1),
    (Icons.local_shipping_outlined, 'Shipping', 3),
    (Icons.home_outlined, 'Delivered', 14),
    (Icons.replay_outlined, 'Returns', 0),
  ];
  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 6, crossAxisSpacing: 6, mainAxisSpacing: 6, childAspectRatio: 0.65,
      ),
      itemCount: _states.length,
      itemBuilder: (_, i) {
        final (icon, label, count) = _states[i];
        final hasItems = count > 0;
        return Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Stack(clipBehavior: Clip.none, children: [
            Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                color: hasItems ? UellowColors.yellowSoft : UellowColors.border,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, size: 20,
                  color: hasItems ? UellowColors.warn : UellowColors.muted),
            ),
            if (hasItems) Positioned(
              top: -4, right: -4,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                decoration: BoxDecoration(
                  color: UellowColors.danger, borderRadius: BorderRadius.circular(8),
                ),
                constraints: const BoxConstraints(minWidth: 16),
                child: Text('$count', textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white, fontSize: 9,
                        fontWeight: FontWeight.w800)),
              ),
            ),
          ]),
          const SizedBox(height: 4),
          Text(label, textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 10, fontWeight: FontWeight.w700,
                color: hasItems ? UellowColors.darkBrown : UellowColors.muted,
              )),
        ]);
      },
    );
  }
}

// ─── Recent order card (in-transit) ───────────────────────────────

class _RecentOrderCard extends StatelessWidget {
  const _RecentOrderCard();
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 8),
      padding: const EdgeInsets.all(14),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
        border: Border(left: BorderSide(color: UellowColors.yellow, width: 4)),
      ),
      child: Row(children: [
        const Icon(Icons.local_shipping_outlined, size: 22, color: UellowColors.warn),
        const SizedBox(width: 12),
        const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('#S00532 · Out for delivery',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: UellowColors.ink)),
          SizedBox(height: 2),
          Text('3 items · Arrives in 2 hours',
              style: TextStyle(fontSize: 11, color: UellowColors.muted)),
        ])),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: const BoxDecoration(
            color: UellowColors.darkBrown,
            borderRadius: BorderRadius.all(Radius.circular(10)),
          ),
          child: const Text('Track', style: TextStyle(
              color: UellowColors.yellowLight, fontSize: 11, fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }
}

// ─── Wishlist/Recent thumb row ────────────────────────────────────

class _ThumbRow extends StatelessWidget {
  const _ThumbRow({required this.items});
  final List<String> items;
  @override
  Widget build(BuildContext context) {
    final colors = [UellowColors.yellow, UellowColors.darkBrown,
        const Color(0xFFFFE066), const Color(0xFFC4A460), const Color(0xFF8B7355)];
    return SizedBox(
      height: 110,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) => SizedBox(
          width: 80,
          child: Column(children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                color: colors[i % colors.length],
                borderRadius: BorderRadius.circular(10),
              ),
              alignment: Alignment.center,
              child: Text(items[i], style: const TextStyle(
                  color: Colors.white, fontWeight: FontWeight.w900)),
            ),
            const SizedBox(height: 4),
            const Text('14.9 KD', style: TextStyle(
                fontSize: 11, fontWeight: FontWeight.w800, color: UellowColors.darkBrown)),
          ]),
        ),
      ),
    );
  }
}

// ─── Action tiles (4x2 grid) ───────────────────────────────────────

class _ActionTiles extends StatelessWidget {
  static const _tiles = [
    (Icons.location_on_outlined, 'Addresses'),
    (Icons.local_shipping_outlined, 'Shipping'),
    (Icons.star_outline, 'Reviews'),
    (Icons.notifications_outlined, 'Alerts'),
    (Icons.card_giftcard, 'Coupons'),
    (Icons.person_outline, 'Followed'),
    (Icons.public, 'Country'),
    (Icons.settings_outlined, 'Settings'),
  ];
  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 4, crossAxisSpacing: 6, mainAxisSpacing: 6, childAspectRatio: 1.1,
      ),
      itemCount: _tiles.length,
      itemBuilder: (_, i) {
        final (icon, label) = _tiles[i];
        return Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Container(
            width: 36, height: 36,
            decoration: const BoxDecoration(
              color: UellowColors.border,
              borderRadius: BorderRadius.all(Radius.circular(12)),
            ),
            child: Icon(icon, size: 18, color: UellowColors.muted),
          ),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(
              fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.text)),
        ]);
      },
    );
  }
}

// ─── Social ────────────────────────────────────────────────────────

class _SocialRow extends StatelessWidget {
  static const _items = [
    Icons.facebook,
    Icons.camera_alt_outlined,
    Icons.video_collection_outlined,
    Icons.smart_display_outlined,
    Icons.alternate_email,
    Icons.chat_outlined,
  ];
  @override
  Widget build(BuildContext context) {
    return Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
      for (final icon in _items) Container(
        width: 48, height: 48,
        decoration: const BoxDecoration(
          color: UellowColors.border, borderRadius: BorderRadius.all(Radius.circular(14)),
        ),
        child: Icon(icon, size: 22, color: UellowColors.muted),
      ),
    ]);
  }
}

// ─── Menu list ────────────────────────────────────────────────────

class _MenuList extends StatelessWidget {
  const _MenuList();
  static const _items = [
    (Icons.chat_bubble_outline, 'Customer support'),
    (Icons.shield_outlined, 'Privacy & security'),
    (Icons.replay_outlined, 'Returns & refunds'),
    (Icons.star_outline, 'Rate the app'),
    (Icons.public, 'Country: Kuwait · العربية'),
  ];
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 8),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(children: [
        for (var i = 0; i < _items.length; i++) ...[
          if (i > 0) const Divider(height: 1, indent: 16, endIndent: 16),
          _row(_items[i].$1, _items[i].$2),
        ],
      ]),
    );
  }

  Widget _row(IconData icon, String label) {
    return ListTile(
      leading: Container(
        width: 32, height: 32,
        decoration: const BoxDecoration(
          color: UellowColors.border, borderRadius: BorderRadius.all(Radius.circular(8)),
        ),
        child: Icon(icon, size: 16, color: UellowColors.muted),
      ),
      title: Text(label, style: const TextStyle(fontSize: 13, color: UellowColors.ink)),
      trailing: const Icon(Icons.chevron_right, color: Color(0xFFCBB78A), size: 18),
      dense: true,
    );
  }
}

class _SignOutBtn extends StatelessWidget {
  const _SignOutBtn();
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 14),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: ListTile(
        leading: Container(
          width: 32, height: 32,
          decoration: const BoxDecoration(
            color: UellowColors.dangerBg, borderRadius: BorderRadius.all(Radius.circular(8)),
          ),
          child: const Icon(Icons.logout, size: 16, color: UellowColors.danger),
        ),
        title: const Text('Sign out',
            style: TextStyle(color: UellowColors.danger, fontWeight: FontWeight.w700)),
        dense: true,
      ),
    );
  }
}

class _Version extends StatelessWidget {
  const _Version();
  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.fromLTRB(14, 8, 14, 30),
      child: Center(child: Text('Uellow v4.2.0 · build 87 · made with ❤ in Kuwait',
          style: TextStyle(fontSize: 11, color: UellowColors.muted))),
    );
  }
}
