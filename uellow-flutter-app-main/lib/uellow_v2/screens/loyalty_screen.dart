// =============================================================================
// LoyaltyScreen — points hero, tier strip, perks, earn ways, redeem grid,
// points history. Wires to /api/mobile/v2/loyalty.
// =============================================================================
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';

class LoyaltyScreen extends StatefulWidget {
  const LoyaltyScreen({super.key});
  @override
  State<LoyaltyScreen> createState() => _LoyaltyScreenState();
}

class _LoyaltyScreenState extends State<LoyaltyScreen> {
  Future<UellowLoyalty>? _future;

  @override
  void initState() {
    super.initState();
    _future = UellowApi.instance.loyalty.overview();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      appBar: AppBar(
        leading: const BackButton(color: UellowColors.darkBrown),
        title: const Text('Loyalty & Rewards', style: UT.h1),
      ),
      body: FutureBuilder<UellowLoyalty>(
        future: _future,
        builder: (_, snap) {
          // Render with fallback demo values when backend not yet wired
          final l = snap.data;
          return ListView(padding: EdgeInsets.zero, children: [
            _Hero(loyalty: l),
            const _TierStrip(currentTier: 'silver'),
            const _Perks(),
            const _EarnWays(),
            const _RedeemGrid(),
            const _History(),
            const SizedBox(height: 30),
          ]);
        },
      ),
    );
  }
}

// ─── Hero card ─────────────────────────────────────────────────────

class _Hero extends StatelessWidget {
  const _Hero({this.loyalty});
  final UellowLoyalty? loyalty;
  @override
  Widget build(BuildContext context) {
    final pts = loyalty?.points ?? 2450;
    final kd  = loyalty?.kdValue.amount ?? 24.5;
    final tierLabel = loyalty?.tierLabel.current(UellowApi.instance.lang).toUpperCase() ?? 'SILVER';
    final progress = (loyalty?.progressPct ?? 48) / 100.0;
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
      padding: const EdgeInsets.all(22),
      decoration: const BoxDecoration(
        gradient: UellowColors.heroLoyalty,
        borderRadius: BorderRadius.all(Radius.circular(20)),
      ),
      child: Stack(children: [
        Positioned(right: -30, top: -30, child: Container(
          width: 160, height: 160,
          decoration: const BoxDecoration(
            gradient: RadialGradient(
              colors: [Color(0x40FFFFFF), Colors.transparent],
            ),
            shape: BoxShape.circle,
          ),
        )),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('YOUR POINTS', style: TextStyle(
              fontSize: 14, fontWeight: FontWeight.w700,
              color: UellowColors.darkBrown, letterSpacing: 0.5)),
          const SizedBox(height: 6),
          Text.rich(TextSpan(children: [
            TextSpan(text: '$pts', style: const TextStyle(
                fontSize: 48, fontWeight: FontWeight.w900,
                color: UellowColors.darkBrown, height: 1)),
            const TextSpan(text: ' pts', style: TextStyle(
                fontSize: 16, fontWeight: FontWeight.w700,
                color: UellowColors.darkBrown)),
          ])),
          const SizedBox(height: 4),
          Text('= ${kd.toStringAsFixed(3)} KD redeem value',
              style: const TextStyle(color: Color(0xFF5B3C00), fontSize: 13)),
          const SizedBox(height: 16),
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              decoration: const BoxDecoration(
                color: UellowColors.darkBrown,
                borderRadius: BorderRadius.all(Radius.circular(999)),
              ),
              child: Text('⭐ $tierLabel', style: const TextStyle(
                  color: UellowColors.yellowLight,
                  fontSize: 12, fontWeight: FontWeight.w800)),
            ),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(
                height: 8,
                decoration: BoxDecoration(
                  color: const Color(0x33412402),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: FractionallySizedBox(
                  alignment: Alignment.centerLeft, widthFactor: progress,
                  child: const DecoratedBox(decoration: BoxDecoration(
                    color: UellowColors.darkBrown,
                    borderRadius: BorderRadius.all(Radius.circular(999)),
                  )),
                ),
              ),
              const SizedBox(height: 4),
              const Text('2,550 pts to GOLD',
                  style: TextStyle(color: Color(0xFF5B3C00), fontSize: 11)),
            ])),
          ]),
          const SizedBox(height: 16),
          Row(children: [
            Expanded(child: ElevatedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.card_giftcard, size: 14),
              label: const Text('Redeem points',
                  style: TextStyle(fontWeight: FontWeight.w800)),
              style: ElevatedButton.styleFrom(
                backgroundColor: UellowColors.darkBrown,
                foregroundColor: UellowColors.yellowLight,
                padding: const EdgeInsets.symmetric(vertical: 11),
                shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.all(Radius.circular(12))),
              ),
            )),
            const SizedBox(width: 8),
            Expanded(child: ElevatedButton(
              onPressed: () {},
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0x26412402),
                foregroundColor: UellowColors.darkBrown,
                padding: const EdgeInsets.symmetric(vertical: 11),
                shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.all(Radius.circular(12))),
              ),
              child: const Text('Transfer',
                  style: TextStyle(fontWeight: FontWeight.w800)),
            )),
          ]),
        ]),
      ]),
    );
  }
}

// ─── Tier strip ────────────────────────────────────────────────────

class _TierStrip extends StatelessWidget {
  const _TierStrip({required this.currentTier});
  final String currentTier;
  static const _tiers = [
    ('🥉','Bronze','0 pts','bronze'),
    ('🥈','Silver','1,000 pts','silver'),
    ('🥇','Gold','5,000 pts','gold'),
    ('💎','Platinum','15,000 pts','platinum'),
  ];
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 130,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        itemCount: _tiers.length,
        separatorBuilder: (_, __) => const SizedBox(width: 6),
        itemBuilder: (_, i) {
          final t = _tiers[i];
          final on = t.$4 == currentTier;
          return Container(
            width: 130, padding: const EdgeInsets.fromLTRB(12, 14, 12, 14),
            decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: on ? UellowColors.yellow : Colors.transparent, width: 2),
            ),
            child: Stack(children: [
              if (on) Positioned(top: -8, left: 0, right: 0, child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: const BoxDecoration(
                    color: UellowColors.yellow,
                    borderRadius: BorderRadius.all(Radius.circular(999)),
                  ),
                  child: const Text('YOU', style: TextStyle(
                      color: UellowColors.darkBrown,
                      fontSize: 9, fontWeight: FontWeight.w900, letterSpacing: 0.5)),
                ),
              )),
              Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Text(t.$1, style: const TextStyle(fontSize: 28)),
                const SizedBox(height: 4),
                Text(t.$2, style: const TextStyle(
                    fontWeight: FontWeight.w900, color: UellowColors.darkBrown, fontSize: 13)),
                Text(t.$3, style: UT.tiny),
              ]),
            ]),
          );
        },
      ),
    );
  }
}

// ─── Perks ─────────────────────────────────────────────────────────

class _Perks extends StatelessWidget {
  const _Perks();
  static const _list = ['2× points on weekends','Free standard delivery',
      'Early sale access','Birthday gift'];
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Silver tier perks', style: UT.h3),
        const SizedBox(height: 10),
        Wrap(spacing: 6, runSpacing: 6, children: _list.map((p) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: const BoxDecoration(
            color: UellowColors.yellowSoft,
            borderRadius: BorderRadius.all(Radius.circular(8)),
          ),
          child: Text(p, style: const TextStyle(
              color: UellowColors.darkBrown, fontSize: 12, fontWeight: FontWeight.w700)),
        )).toList()),
      ]),
    );
  }
}

// ─── Earn ways ─────────────────────────────────────────────────────

class _EarnWays extends StatelessWidget {
  const _EarnWays();
  static const _ways = [
    (Icons.shopping_cart_outlined, 'Place an order', '1 KD = 10 points', '+10 / KD'),
    (Icons.star_outline, 'Write a review', 'Verified purchase', '+50'),
    (Icons.person_outline, 'Refer a friend', 'Both get 250 pts', '+250'),
    (Icons.card_giftcard, 'Daily check-in', 'Streak: 4 days', '+5'),
  ];
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Ways to earn more', style: UT.h3),
        const SizedBox(height: 8),
        for (final w in _ways) Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: UellowColors.bg)),
          ),
          child: Row(children: [
            Container(
              width: 36, height: 36,
              decoration: const BoxDecoration(
                color: UellowColors.yellowSoft,
                borderRadius: BorderRadius.all(Radius.circular(10)),
              ),
              child: Icon(w.$1, size: 18, color: UellowColors.warn),
            ),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(w.$2, style: const TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w700, color: UellowColors.ink)),
              Text(w.$3, style: UT.small),
            ])),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: const BoxDecoration(
                color: UellowColors.successBg,
                borderRadius: BorderRadius.all(Radius.circular(6)),
              ),
              child: Text(w.$4, style: const TextStyle(
                  color: UellowColors.successDk,
                  fontSize: 11, fontWeight: FontWeight.w800)),
            ),
          ]),
        ),
      ]),
    );
  }
}

// ─── Redeem grid ───────────────────────────────────────────────────

class _RedeemGrid extends StatelessWidget {
  const _RedeemGrid();
  static const _items = [
    ('💵','5 KD off coupon','500 pts'),
    ('🚚','Free same-day','300 pts'),
    ('🎁','Mystery box','1000 pts'),
    ('💎','10% off any','800 pts'),
  ];
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: const [
          Expanded(child: Text('Redeem your points', style: UT.h3)),
          Text('See all →', style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.text)),
        ]),
        const SizedBox(height: 10),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2, crossAxisSpacing: 8, mainAxisSpacing: 8, childAspectRatio: 1.05,
          ),
          itemCount: _items.length,
          itemBuilder: (_, i) {
            final it = _items[i];
            return Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: UellowColors.yellowFaint,
                border: Border.all(color: UellowColors.warnBg),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Text(it.$1, style: const TextStyle(fontSize: 28)),
                const SizedBox(height: 4),
                Text(it.$2, textAlign: TextAlign.center,
                    style: const TextStyle(
                        fontWeight: FontWeight.w800, color: UellowColors.darkBrown,
                        fontSize: 12)),
                Text(it.$3, style: UT.small),
                const SizedBox(height: 6),
                SizedBox(width: double.infinity, child: ElevatedButton(
                  onPressed: () {},
                  style: ElevatedButton.styleFrom(
                    backgroundColor: UellowColors.yellowLight,
                    foregroundColor: UellowColors.darkBrown,
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    shape: const RoundedRectangleBorder(
                        borderRadius: BorderRadius.all(Radius.circular(8))),
                  ),
                  child: const Text('Redeem',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
                )),
              ]),
            );
          },
        ),
      ]),
    );
  }
}

// ─── History ──────────────────────────────────────────────────────

class _History extends StatelessWidget {
  const _History();
  static const _entries = [
    ('Order #S00532','Yesterday', '+150', true),
    ('Used 150 pts on order #S00532','Yesterday', '−150', false),
    ('Review on HainoTeko Watch','2 days ago', '+50', true),
    ('Birthday gift bonus','May 14', '+500', true),
  ];
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: const [
          Expanded(child: Text('Points history', style: UT.h3)),
          Text('See all →', style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.text)),
        ]),
        const SizedBox(height: 8),
        for (final e in _entries) Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: UellowColors.bg)),
          ),
          child: Row(children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(e.$1, style: const TextStyle(fontSize: 13, color: UellowColors.ink)),
              const SizedBox(height: 2),
              Text(e.$2, style: UT.small),
            ])),
            Text(e.$3, style: TextStyle(
              color: e.$4 ? UellowColors.successDk : UellowColors.dangerDk,
              fontWeight: FontWeight.w800, fontSize: 13,
            )),
          ]),
        ),
      ]),
    );
  }
}
