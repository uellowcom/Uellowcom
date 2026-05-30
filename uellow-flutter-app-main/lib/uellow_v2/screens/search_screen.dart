// =============================================================================
// SearchScreen — typing autocomplete + recent + trending + browse cats.
// Live suggestions via /api/mobile/v2/search.
// =============================================================================
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});
  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _ctrl = TextEditingController();
  final _focus = FocusNode();
  Future<UellowSearchResult>? _results;
  final _recent = ['apple watch','huawei buds','samsung tv 55','عطر زمزم','red dress'];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _focus.requestFocus());
    _ctrl.addListener(_onChanged);
  }

  void _onChanged() {
    final q = _ctrl.text.trim();
    if (q.length >= 2) {
      setState(() => _results = UellowApi.instance.search.search(q, perPage: 6));
    } else {
      setState(() => _results = null);
    }
  }

  @override
  void dispose() { _ctrl.dispose(); _focus.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      body: SafeArea(
        child: Column(children: [
          _topBar(),
          Expanded(child: _ctrl.text.length >= 2 ? _liveResults() : _idleState()),
        ]),
      ),
    );
  }

  Widget _topBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 10, 10, 10),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      child: Row(children: [
        IconButton(
          onPressed: () => Navigator.maybePop(context),
          icon: const Icon(Icons.arrow_back, color: UellowColors.darkBrown),
          style: IconButton.styleFrom(
            backgroundColor: UellowColors.border,
            shape: const RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(10))),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(child: TextField(
          controller: _ctrl, focusNode: _focus, autofocus: true,
          decoration: InputDecoration(
            hintText: 'ابحث عن منتج، ماركة، أو ﺗﺎﺟﺮ…',
            prefixIcon: const Icon(Icons.search, size: 18, color: UellowColors.muted),
            suffixIcon: Row(mainAxisSize: MainAxisSize.min, children: [
              IconButton(icon: const Icon(Icons.qr_code_scanner_outlined, size: 18, color: UellowColors.muted), onPressed: () {}),
              IconButton(icon: const Icon(Icons.camera_alt_outlined, size: 18, color: UellowColors.muted), onPressed: () {}),
            ]),
            contentPadding: EdgeInsets.zero,
          ),
        )),
        const SizedBox(width: 4),
        TextButton(
          onPressed: () => Navigator.maybePop(context),
          child: const Text('Cancel', style: TextStyle(
              color: UellowColors.darkBrown, fontWeight: FontWeight.w700, fontSize: 13)),
        ),
      ]),
    );
  }

  // ─── Idle state (recent + trending + browse) ────────────────

  Widget _idleState() {
    return ListView(children: [
      _section(title: 'RECENT SEARCHES', trailing: 'Clear all',
        child: Wrap(spacing: 6, runSpacing: 6, children: _recent.map((q) => Container(
          padding: const EdgeInsets.fromLTRB(12, 7, 10, 7),
          decoration: const BoxDecoration(
            color: UellowColors.border,
            borderRadius: BorderRadius.all(Radius.circular(999)),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Text(q, style: const TextStyle(fontSize: 12.5, color: UellowColors.text)),
            const SizedBox(width: 6),
            const Icon(Icons.close, size: 14, color: UellowColors.danger),
          ]),
        )).toList()),
      ),
      _section(title: 'TRENDING TODAY  🔥', child: GridView.builder(
        shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2, crossAxisSpacing: 10, mainAxisSpacing: 10, childAspectRatio: 4.5,
        ),
        itemCount: 6,
        itemBuilder: (_, i) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: UellowColors.yellowFaint,
            border: Border.all(color: UellowColors.warnBg),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(children: [
            Container(
              width: 22, height: 22, alignment: Alignment.center,
              decoration: BoxDecoration(
                color: i < 2 ? UellowColors.danger : UellowColors.yellowLight,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text('${i+1}', style: TextStyle(
                color: i < 2 ? Colors.white : UellowColors.darkBrown,
                fontWeight: FontWeight.w900, fontSize: 11,
              )),
            ),
            const SizedBox(width: 10),
            Text(_trends[i], style: const TextStyle(
                fontSize: 12.5, fontWeight: FontWeight.w700, color: UellowColors.darkBrown)),
          ]),
        ),
      )),
      _section(title: 'BROWSE CATEGORIES', child: SizedBox(
        height: 100,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: _qcats.length,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (_, i) => Container(
            width: 80, padding: const EdgeInsets.symmetric(vertical: 14),
            decoration: const BoxDecoration(
              color: UellowColors.yellowSoft,
              borderRadius: BorderRadius.all(Radius.circular(12)),
            ),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Text(_qcats[i].$1, style: const TextStyle(fontSize: 24)),
              const SizedBox(height: 4),
              Text(_qcats[i].$2, style: const TextStyle(
                  fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.darkBrown)),
            ]),
          ),
        ),
      )),
    ]);
  }

  Widget _section({required String title, String? trailing, required Widget child}) {
    return Container(
      color: Colors.white,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(title, style: const TextStyle(
              fontSize: 11, fontWeight: FontWeight.w800,
              color: UellowColors.muted, letterSpacing: 0.5))),
          if (trailing != null) Text(trailing, style: const TextStyle(
              fontSize: 12, color: UellowColors.text, fontWeight: FontWeight.w700)),
        ]),
        const SizedBox(height: 10),
        child,
      ]),
    );
  }

  static const _trends = [
    'Smart watches','iPhone 17 cases','Air fryer','Perfumes',
    'Kids tablets','Gaming chair',
  ];
  static const _qcats = [
    ('📱','Phones'), ('👗','Fashion'), ('💄','Beauty'),
    ('🏠','Home'), ('⌚','Watches'), ('🎮','Gaming'),
  ];

  // ─── Live results state (typing ≥ 2 chars) ─────────────────

  Widget _liveResults() {
    return FutureBuilder<UellowSearchResult>(
      future: _results,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snap.hasError) {
          return Center(child: Text(snap.error.toString(), style: UT.body));
        }
        final r = snap.data!;
        final lang = UellowApi.instance.lang;
        return ListView(children: [
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
            child: const Text('SUGGESTED RESULTS',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                    color: UellowColors.muted, letterSpacing: 0.5)),
          ),
          Container(
            color: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(children: r.products.take(6).map((p) => Container(
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: UellowColors.border)),
              ),
              child: Row(children: [
                ClipRRect(borderRadius: BorderRadius.circular(8),
                  child: CachedNetworkImage(imageUrl: p.image,
                      width: 50, height: 50, fit: BoxFit.cover),
                ),
                const SizedBox(width: 10),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(p.name.current(lang), maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12.5, color: UellowColors.ink)),
                  const SizedBox(height: 2),
                  Row(children: [
                    Text(p.price.format(), style: const TextStyle(
                        fontWeight: FontWeight.w800, color: UellowColors.darkBrown,
                        fontSize: 12)),
                    const Text(' · ', style: TextStyle(color: UellowColors.muted)),
                    const Text('⭐ 4.7', style: TextStyle(fontSize: 11, color: UellowColors.muted)),
                  ]),
                ])),
              ]),
            )).toList()),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: ElevatedButton(
              onPressed: () {},
              child: Text('See all results for "${_ctrl.text.trim()}"  →'),
            ),
          ),
        ]);
      },
    );
  }
}
