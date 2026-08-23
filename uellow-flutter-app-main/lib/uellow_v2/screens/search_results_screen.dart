// =============================================================================
// SearchResultsScreen — full, paginated search results.
// Fixes "search shows only a few results": the suggestions dropdown shows 6,
// this screen loads the COMPLETE result set (/api/mobile/v2/products?search=)
// with infinite scroll, so e.g. searching "NEO" shows every matching product.
// =============================================================================
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../../api/uellow_models.dart';
import '../theme/uellow_theme.dart';
import '../widgets/product_card.dart';

class SearchResultsScreen extends StatefulWidget {
  final String query;
  const SearchResultsScreen({super.key, required this.query});
  @override
  State<SearchResultsScreen> createState() => _SearchResultsScreenState();
}

class _SearchResultsScreenState extends State<SearchResultsScreen> {
  final _scroll = ScrollController();
  final List<UellowProductCard> _items = [];
  int _page = 1;
  bool _loading = false;
  bool _hasNext = true;
  int _total = 0;

  @override
  void initState() {
    super.initState();
    _load();
    _scroll.addListener(() {
      if (_scroll.position.pixels >= _scroll.position.maxScrollExtent - 320 &&
          !_loading &&
          _hasNext) {
        _load();
      }
    });
  }

  Future<void> _load() async {
    if (_loading || !_hasNext) return;
    setState(() => _loading = true);
    try {
      final res = await UellowApi.instance.products.list(
          search: widget.query, page: _page, perPage: 20, sort: 'newest');
      if (!mounted) return;
      setState(() {
        _items.addAll(res.items);
        _total = res.total;
        _hasNext = res.hasNext;
        _page += 1;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _hasNext = false);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      appBar: AppBar(
        backgroundColor: Colors.white,
        foregroundColor: UellowColors.ink,
        elevation: 0.5,
        title: Text('“${widget.query}”',
            style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: UellowColors.ink)),
      ),
      body: (_items.isEmpty && _loading)
          ? const Center(
              child: CircularProgressIndicator(color: UellowColors.darkBrown))
          : (_items.isEmpty)
              ? _empty()
              : Column(children: [
                  Container(
                    width: double.infinity,
                    color: Colors.white,
                    padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
                    child: Text('$_total ${_total == 1 ? "result" : "results"}',
                        style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w700,
                            color: UellowColors.muted)),
                  ),
                  Expanded(
                    child: GridView.builder(
                      controller: _scroll,
                      padding: const EdgeInsets.all(12),
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        crossAxisSpacing: 10,
                        mainAxisSpacing: 10,
                        childAspectRatio: 0.6,
                      ),
                      itemCount: _items.length + (_hasNext ? 2 : 0),
                      itemBuilder: (_, i) {
                        if (i >= _items.length) {
                          return const Center(
                            child: Padding(
                              padding: EdgeInsets.all(14),
                              child: CircularProgressIndicator(
                                  color: UellowColors.darkBrown),
                            ),
                          );
                        }
                        return ProductCard(product: _items[i]);
                      },
                    ),
                  ),
                ]),
    );
  }

  Widget _empty() => ListView(children: [
        const SizedBox(height: 100),
        const Center(
            child:
                Icon(Icons.search_off, size: 80, color: UellowColors.muted)),
        const SizedBox(height: 18),
        Center(child: Text('No results for “${widget.query}”', style: UT.h2)),
      ]);
}
