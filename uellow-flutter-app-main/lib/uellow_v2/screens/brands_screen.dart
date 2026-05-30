// =============================================================================
// BrandsScreen — A-Z scroll bar + featured carousel + brands grid.
// Wires to /api/mobile/v2/vendors.
// =============================================================================
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../theme/uellow_theme.dart';

class BrandsScreen extends StatefulWidget {
  const BrandsScreen({super.key});
  @override
  State<BrandsScreen> createState() => _BrandsScreenState();
}

class _BrandsScreenState extends State<BrandsScreen> {
  String _letter = 'A';
  // Demo brand list grouped by letter
  static const _demo = <String, List<(String, Color)>>{
    'A': [('Anker', Color(0xFFFF4D4D)), ('Apple', Colors.black), ('Acer', Color(0xFF10B981))],
    'B': [('Bestrio', Color(0xFF412402)), ('Borofone', Color(0xFF06B6D4)), ('Bose', Color(0xFF000000))],
    'H': [('Huawei', Color(0xFF10B981)), ('Hago', Color(0xFFF59E0B))],
    'S': [('Samsung', Color(0xFF3B82F6)), ('Sumo', Color(0xFFF5C320)), ('Sayona', Color(0xFFEC4899)), ('Sing-e', Color(0xFF84CC16))],
    'V': [('Vidvie', Color(0xFF8B5CF6))],
    'X': [('Xiaomi', Color(0xFFFF9500))],
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      appBar: AppBar(
        leading: const BackButton(color: UellowColors.darkBrown),
        title: const Text('All Brands', style: UT.h1),
      ),
      body: Stack(children: [
        ListView(padding: EdgeInsets.zero, children: [
          _searchBar(),
          _featured(),
          for (final letter in _demo.keys) ...[
            _groupHeader(letter),
            _brandGrid(_demo[letter]!),
          ],
          const SizedBox(height: 30),
        ]),
        _AlphabetBar(active: _letter, onTap: (l) => setState(() => _letter = l)),
      ]),
    );
  }

  Widget _searchBar() {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
      child: Container(
        height: 40, padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: const BoxDecoration(
          color: UellowColors.border,
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
        child: Row(children: const [
          Icon(Icons.search, size: 18, color: UellowColors.muted),
          SizedBox(width: 10),
          Text('Search brand or vendor…',
              style: TextStyle(fontSize: 13, color: UellowColors.muted)),
        ]),
      ),
    );
  }

  Widget _featured() {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Padding(
          padding: EdgeInsets.only(bottom: 12),
          child: Text('⭐ Featured brands this week', style: UT.h3),
        ),
        SizedBox(height: 130, child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: 3,
          separatorBuilder: (_, __) => const SizedBox(width: 10),
          itemBuilder: (_, i) {
            final cards = [
              (LinearGradient(colors: [UellowColors.darkBrown, const Color(0xFF7A4A08)]),
                  'A', 'Anker Official', 'UP TO 35% OFF', UellowColors.yellowLight),
              (const LinearGradient(colors: [UellowColors.danger, Color(0xFFC81212)]),
                  'H', 'Huawei Store', 'NEW LAUNCH', Colors.white),
              (const LinearGradient(colors: [Color(0xFF3B82F6), Color(0xFF1E40AF)]),
                  'S', 'Samsung', 'EXCLUSIVE', Colors.white),
            ];
            final c = cards[i];
            return SizedBox(width: 140, child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: c.$1, borderRadius: BorderRadius.circular(14),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  width: 44, height: 44,
                  decoration: BoxDecoration(
                    color: c.$5,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  alignment: Alignment.center,
                  child: Text(c.$2, style: TextStyle(
                      color: c.$5 == UellowColors.yellowLight
                          ? UellowColors.darkBrown : c.$1.colors.first,
                      fontWeight: FontWeight.w900, fontSize: 20)),
                ),
                const SizedBox(height: 10),
                Text(c.$3, style: TextStyle(
                    color: c.$5, fontSize: 14, fontWeight: FontWeight.w800)),
                const SizedBox(height: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                    color: c.$5, borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(c.$4, style: TextStyle(
                      color: c.$5 == UellowColors.yellowLight
                          ? UellowColors.darkBrown : c.$1.colors.first,
                      fontSize: 10, fontWeight: FontWeight.w800)),
                ),
              ]),
            ));
          },
        )),
      ]),
    );
  }

  Widget _groupHeader(String letter) {
    return Container(
      color: Colors.white,
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
      child: Text(letter, style: const TextStyle(
          fontSize: 16, fontWeight: FontWeight.w900, color: UellowColors.darkBrown)),
    );
  }

  Widget _brandGrid(List<(String, Color)> brands) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
      child: GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 4, crossAxisSpacing: 8, mainAxisSpacing: 8, childAspectRatio: 0.92,
        ),
        itemCount: brands.length,
        itemBuilder: (_, i) {
          final (name, color) = brands[i];
          return Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: UellowColors.yellowFaint,
              border: Border.all(color: UellowColors.border),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Container(
                width: 44, height: 44,
                decoration: BoxDecoration(
                  color: color, borderRadius: BorderRadius.circular(12),
                ),
                alignment: Alignment.center,
                child: Text(name[0], style: const TextStyle(
                    color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
              ),
              const SizedBox(height: 6),
              Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700,
                      color: UellowColors.ink)),
              const SizedBox(height: 1),
              const Text('★ 4.6', style: TextStyle(fontSize: 9.5, color: UellowColors.muted)),
            ]),
          );
        },
      ),
    );
  }
}

class _AlphabetBar extends StatelessWidget {
  const _AlphabetBar({required this.active, required this.onTap});
  final String active;
  final ValueChanged<String> onTap;
  static const _letters = ['#','A','B','C','D','E','F','G','H','I','J','K','L',
      'M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z'];
  @override
  Widget build(BuildContext context) {
    return Positioned(right: 4, top: 80, bottom: 80, child: Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        for (final l in _letters) GestureDetector(
          onTap: () => onTap(l),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
            child: Text(l, style: TextStyle(
              fontSize: 10, fontWeight: FontWeight.w700,
              color: l == active ? UellowColors.danger : UellowColors.muted,
            )),
          ),
        ),
      ]),
    ));
  }
}
