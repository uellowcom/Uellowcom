// =============================================================================
// SplashScreen — first screen on app launch.
//
// Flow:
//   1. Call /app/geo to detect country from IP + see if user already
//      picked one (server tells us via mobile.session).
//   2. If auto-detected and user hasn't manually overridden, navigate to
//      Home directly with the detected country/website pre-applied.
//   3. Otherwise show the picker dropdown (matching the mockup) and let
//      them choose. Their pick goes to /app/set-country and persists.
//
// UX: matches the mockup splash exactly — Uellow logo top, country
// dropdown, language tabs, "Detected" hint, Continue CTA bottom.
// =============================================================================
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../api/uellow_api.dart';
import '../../api/uellow_endpoints.dart';
import '../router/uellow_router.dart';
import '../theme/uellow_theme.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  bool _loading = true;
  Map<String, dynamic>? _detected;
  List<Map<String, dynamic>> _countries = [];
  Map<String, dynamic>? _picked;
  String _lang = 'ar';

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    try {
      // Two parallel calls: geo + the full country list for the picker
      final results = await Future.wait([
        _request('GET', EP.appGeo()),
        _request('GET', EP.appCountriesList()),
      ]);
      final geo = results[0]['data'] as Map<String, dynamic>;
      final list = (results[1]['data'] as List).cast<Map<String, dynamic>>();
      _detected = geo;
      _countries = list;
      _picked = geo['recommended'] as Map<String, dynamic>?;
      // Pre-select language from picked country's default or phone locale
      final fromCountry = (_picked?['default_language'] as String?)?.toLowerCase();
      _lang = (fromCountry?.startsWith('ar') ?? true) ? 'ar' : 'en';
    } catch (_) {
      // network down or backend not reachable; still let user pick manually
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Minimal direct GET — splash runs before tokens exist, so we keep
  /// it standalone instead of going through the typed client.
  Future<Map<String, dynamic>> _request(String method, String path) async {
    final uri = Uri.parse('${UellowApi.instance.baseUrl}$path');
    final resp = await http.get(uri, headers: {
      'Accept': 'application/json',
      'X-Lang': UellowApi.instance.lang,
    });
    final body = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    if (body['success'] != true) throw Exception(body['error'] ?? 'request failed');
    return body;
  }

  Future<void> _persistAndGoHome() async {
    final code = _picked?['country']?['code'] as String?;
    if (code != null) {
      // Tell the server the user picked this country
      try {
        final uri = Uri.parse(
            '${UellowApi.instance.baseUrl}${EP.appSetCountry()}');
        await http.post(uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'country': code, 'lang': _lang}));
      } catch (_) {/* non-blocking */}
    }
    UellowApi.instance.setLang(_lang == 'ar' ? 'ar_001' : 'en_US');
    if (!mounted) return;
    Navigator.of(context).pushReplacementNamed(Routes.home);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft, end: Alignment.bottomRight,
            colors: [Color(0xFFFFD340), UellowColors.yellow, Color(0xFFC99000)],
          ),
        ),
        child: SafeArea(
          child: _loading
              ? const Center(child: CircularProgressIndicator(color: UellowColors.darkBrown))
              : _buildContent(),
        ),
      ),
    );
  }

  Widget _buildContent() {
    return Stack(
      children: [
        SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 20),
              _logo(),
              const SizedBox(height: 18),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 8),
                child: Column(
                  children: [
                    Text('Your trusted marketplace in the Middle East.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 14, color: Color(0xFF5B3C00))),
                    SizedBox(height: 2),
                    Text("Choose where you're shopping from.",
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 14, color: UellowColors.darkBrown,
                            fontWeight: FontWeight.w800)),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              _pickerCard(),
              if (_detected != null) ...[
                const SizedBox(height: 14),
                _detectedHint(),
              ],
            ],
          ),
        ),
        Positioned(
          left: 24, right: 24, bottom: 30,
          child: ElevatedButton(
            onPressed: _persistAndGoHome,
            style: ElevatedButton.styleFrom(
              backgroundColor: UellowColors.darkBrown,
              foregroundColor: UellowColors.yellowLight,
              padding: const EdgeInsets.symmetric(vertical: 16),
              elevation: 14,
              shadowColor: const Color(0x80412402),
              shape: const RoundedRectangleBorder(
                borderRadius: BorderRadius.all(Radius.circular(16))),
            ),
            child: const Text('Continue  →',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
          ),
        ),
      ],
    );
  }

  Widget _logo() {
    return Center(
      child: Container(
        padding: const EdgeInsets.fromLTRB(18, 10, 22, 10),
        decoration: const BoxDecoration(
          color: UellowColors.darkBrown,
          borderRadius: BorderRadius.all(Radius.circular(16)),
          boxShadow: [BoxShadow(color: Color(0x66412402),
              blurRadius: 30, offset: Offset(0, 14))],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 38, height: 38,
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft, end: Alignment.bottomRight,
                  colors: [Color(0xFFFFE066), UellowColors.yellow],
                ),
                borderRadius: BorderRadius.all(Radius.circular(12)),
              ),
              child: const Center(
                child: Text('U', style: TextStyle(color: UellowColors.darkBrown,
                    fontWeight: FontWeight.w900, fontSize: 22)),
              ),
            ),
            const SizedBox(width: 12),
            const Text('Uellow',
                style: TextStyle(color: UellowColors.yellowLight,
                    fontWeight: FontWeight.w900, fontSize: 24, letterSpacing: -0.5)),
          ],
        ),
      ),
    );
  }

  Widget _pickerCard() {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: const BorderRadius.all(Radius.circular(20)),
        boxShadow: [BoxShadow(color: const Color(0x40412402),
            blurRadius: 40, offset: const Offset(0, 16))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(14, 12, 14, 6),
            child: Text('COUNTRY',
                style: TextStyle(fontSize: 11, color: UellowColors.muted,
                    fontWeight: FontWeight.w800, letterSpacing: 0.8)),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
            child: _countryDropdown(),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(14, 6, 14, 6),
            child: Text('LANGUAGE',
                style: TextStyle(fontSize: 11, color: UellowColors.muted,
                    fontWeight: FontWeight.w800, letterSpacing: 0.8)),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
            child: _langTabs(),
          ),
        ],
      ),
    );
  }

  Widget _countryDropdown() {
    final country = _picked?['country'] as Map<String, dynamic>?;
    final flag = country?['flag'] as String? ?? '🌐';
    final name = country?['name']?['en'] as String? ?? 'Kuwait';
    final cur  = (_picked?['currency'] as String?) ?? 'KWD';
    return InkWell(
      onTap: _showCountrySheet,
      borderRadius: const BorderRadius.all(Radius.circular(12)),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: UellowColors.yellowFaint,
          border: Border.all(color: UellowColors.border, width: 1.5),
          borderRadius: const BorderRadius.all(Radius.circular(12)),
        ),
        child: Row(
          children: [
            Text(flag, style: const TextStyle(fontSize: 22)),
            const SizedBox(width: 12),
            Expanded(
              child: Row(
                children: [
                  Text(name,
                      style: const TextStyle(color: UellowColors.darkBrown,
                          fontWeight: FontWeight.w800, fontSize: 15)),
                  const SizedBox(width: 6),
                  Text('· $cur',
                      style: const TextStyle(color: UellowColors.muted,
                          fontWeight: FontWeight.w500, fontSize: 12)),
                ],
              ),
            ),
            const Icon(Icons.keyboard_arrow_down, color: UellowColors.muted),
          ],
        ),
      ),
    );
  }

  void _showCountrySheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        constraints: const BoxConstraints(maxHeight: 480),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Container(
                width: 36, height: 4,
                decoration: BoxDecoration(color: UellowColors.border,
                    borderRadius: BorderRadius.circular(2)),
              ),
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 8, 20, 12),
              child: Align(alignment: Alignment.centerLeft,
                  child: Text('Select your country',
                      style: TextStyle(color: UellowColors.darkBrown,
                          fontWeight: FontWeight.w800, fontSize: 16))),
            ),
            Flexible(
              child: ListView.separated(
                shrinkWrap: true,
                itemCount: _countries.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, i) {
                  final c = _countries[i];
                  final cn = c['country'] as Map<String, dynamic>?;
                  final flag = cn?['flag'] as String? ?? '🌐';
                  final name = cn?['name']?['en'] as String? ?? '—';
                  final cur = c['currency'] as String? ?? '';
                  return ListTile(
                    leading: Text(flag, style: const TextStyle(fontSize: 22)),
                    title: Text(name,
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text(cn?['name']?['ar'] as String? ?? '',
                        style: const TextStyle(fontSize: 11)),
                    trailing: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                      decoration: const BoxDecoration(
                        color: UellowColors.yellow,
                        borderRadius: BorderRadius.all(Radius.circular(999)),
                      ),
                      child: Text(cur,
                          style: const TextStyle(color: UellowColors.darkBrown,
                              fontWeight: FontWeight.w800, fontSize: 11)),
                    ),
                    onTap: () { setState(() => _picked = c); Navigator.pop(context); },
                  );
                },
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _langTabs() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: UellowColors.yellowFaint,
        border: Border.all(color: UellowColors.border, width: 1.5),
        borderRadius: const BorderRadius.all(Radius.circular(12)),
      ),
      child: Row(
        children: [
          Expanded(child: _langBtn('العربية', 'ar')),
          const SizedBox(width: 6),
          Expanded(child: _langBtn('English', 'en')),
        ],
      ),
    );
  }

  Widget _langBtn(String label, String code) {
    final on = _lang == code;
    return GestureDetector(
      onTap: () => setState(() => _lang = code),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: on ? UellowColors.darkBrown : Colors.transparent,
          borderRadius: const BorderRadius.all(Radius.circular(8)),
        ),
        alignment: Alignment.center,
        child: Text(label,
            style: TextStyle(
              color: on ? UellowColors.yellowLight : UellowColors.text,
              fontWeight: FontWeight.w800, fontSize: 14,
            )),
      ),
    );
  }

  Widget _detectedHint() {
    final country = _detected?['recommended']?['country'] as Map<String, dynamic>?;
    final domain  = _detected?['recommended']?['website']?['domain'] as String? ?? 'The App';
    final name    = country?['name']?['en'] as String? ?? 'your region';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(.7),
        border: Border.all(color: const Color(0x4DF5C320)),
        borderRadius: const BorderRadius.all(Radius.circular(14)),
      ),
      child: Row(
        children: [
          const Text('📍', style: TextStyle(fontSize: 18)),
          const SizedBox(width: 10),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: const TextStyle(fontSize: 12, color: UellowColors.darkBrown),
                children: [
                  const TextSpan(text: 'Detected: '),
                  TextSpan(text: name,
                      style: const TextStyle(fontWeight: FontWeight.w800)),
                  const TextSpan(text: ' · Connecting to '),
                  TextSpan(text: domain,
                      style: const TextStyle(fontWeight: FontWeight.w800)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
