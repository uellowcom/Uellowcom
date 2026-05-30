// =============================================================================
// WalletScreen — balance hero, quick top-up pills, stats, transactions.
// Wires to /api/mobile/v2/wallet/balance + /transactions.
// =============================================================================
import 'package:flutter/material.dart';

import '../theme/uellow_theme.dart';

class WalletScreen extends StatelessWidget {
  const WalletScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      appBar: AppBar(
        leading: const BackButton(color: UellowColors.darkBrown),
        title: const Text('My Wallet', style: UT.h1),
      ),
      body: ListView(padding: EdgeInsets.zero, children: const [
        _Hero(),
        _StatsRow(),
        _QuickTopup(),
        _Transactions(),
        SizedBox(height: 30),
      ]),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero();
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 22),
      decoration: const BoxDecoration(
        gradient: UellowColors.heroWallet,
        borderRadius: BorderRadius.all(Radius.circular(20)),
        boxShadow: [BoxShadow(color: Color(0x80412402),
            blurRadius: 30, offset: Offset(0, 14))],
      ),
      child: Stack(children: [
        Positioned(right: -40, bottom: -40, child: Container(
          width: 180, height: 180,
          decoration: const BoxDecoration(
            gradient: RadialGradient(colors: [Color(0x1FFFD340), Colors.transparent]),
            shape: BoxShape.circle,
          ),
        )),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('AVAILABLE BALANCE', style: TextStyle(
              fontSize: 12, fontWeight: FontWeight.w700,
              color: UellowColors.yellowLight, letterSpacing: 0.8)),
          const SizedBox(height: 6),
          Text.rich(TextSpan(children: const [
            TextSpan(text: '12.750', style: TextStyle(
                fontSize: 44, fontWeight: FontWeight.w900,
                color: UellowColors.yellowLight, height: 1)),
            TextSpan(text: ' KD', style: TextStyle(
                fontSize: 18, fontWeight: FontWeight.w700,
                color: UellowColors.yellowLight)),
          ])),
          const SizedBox(height: 4),
          const Text('Last top-up 3 days ago via KNET',
              style: TextStyle(color: UellowColors.yellowLight, fontSize: 12)),
          const SizedBox(height: 18),
          Row(children: [
            Expanded(child: _action(
                icon: Icons.add_circle_outline, label: 'Top up', primary: true)),
            const SizedBox(width: 8),
            Expanded(child: _action(icon: Icons.swap_horiz, label: 'Send')),
            const SizedBox(width: 8),
            Expanded(child: _action(icon: Icons.history, label: 'History')),
          ]),
        ]),
      ]),
    );
  }

  Widget _action({required IconData icon, required String label, bool primary = false}) {
    final bg = primary ? UellowColors.yellowLight : const Color(0x2EFFD340);
    final fg = primary ? UellowColors.darkBrown : UellowColors.yellowLight;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12)),
      child: Column(children: [
        Icon(icon, size: 16, color: fg),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(
            color: fg, fontWeight: FontWeight.w800, fontSize: 11.5)),
      ]),
    );
  }
}

class _StatsRow extends StatelessWidget {
  const _StatsRow();
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      child: Row(children: [
        Expanded(child: _stat('THIS MONTH SPENT', '−45.300', '+15% vs last', false)),
        const SizedBox(width: 8),
        Expanded(child: _stat('EARNED CASHBACK', '+2.150', '+8 transactions', true)),
      ]),
    );
  }
  Widget _stat(String lbl, String val, String delta, bool up) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(12)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.center, children: [
        Text(lbl, style: const TextStyle(
            fontSize: 10, color: UellowColors.muted, fontWeight: FontWeight.w700,
            letterSpacing: 0.4)),
        const SizedBox(height: 4),
        Text(val, style: const TextStyle(
            fontSize: 18, fontWeight: FontWeight.w900, color: UellowColors.darkBrown)),
        Text(delta, style: TextStyle(
            fontSize: 10, fontWeight: FontWeight.w700,
            color: up ? UellowColors.successDk : UellowColors.dangerDk)),
      ]),
    );
  }
}

class _QuickTopup extends StatelessWidget {
  const _QuickTopup();
  static const _amounts = [5, 10, 25, 50];
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(14),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Quick top-up', style: UT.h3),
        const SizedBox(height: 10),
        Row(children: [
          for (var i = 0; i < _amounts.length; i++) ...[
            Expanded(child: _pill(_amounts[i], popular: i == 2)),
            if (i < _amounts.length - 1) const SizedBox(width: 6),
          ],
        ]),
      ]),
    );
  }
  Widget _pill(int amt, {bool popular = false}) {
    return Stack(clipBehavior: Clip.none, children: [
      Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: popular ? UellowColors.yellowSoft : UellowColors.yellowFaint,
          border: Border.all(
              color: popular ? UellowColors.yellow : UellowColors.border, width: 1.5),
          borderRadius: BorderRadius.circular(10),
        ),
        alignment: Alignment.center,
        child: Text('$amt KD', style: const TextStyle(
            color: UellowColors.darkBrown, fontWeight: FontWeight.w800, fontSize: 13)),
      ),
      if (popular) Positioned(top: -8, left: 0, right: 0, child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
          decoration: const BoxDecoration(
            color: UellowColors.yellow,
            borderRadius: BorderRadius.all(Radius.circular(999)),
          ),
          child: const Text('POPULAR', style: TextStyle(
              color: UellowColors.darkBrown, fontSize: 8, fontWeight: FontWeight.w800)),
        ),
      )),
    ]);
  }
}

class _Transactions extends StatelessWidget {
  const _Transactions();
  static const _txs = [
    (in_: false, title: 'Order #S00532', meta: 'Today · 11:24 AM', amt: '−5.500', status: 'Completed'),
    (in_: true,  title: 'Top-up via KNET', meta: '3 days ago · ****1234', amt: '+25.000', status: 'Completed'),
    (in_: true,  title: 'Cashback — order #S00498', meta: '5 days ago', amt: '+0.250', status: 'Completed'),
    (in_: false, title: 'Order #S00498', meta: 'May 25 · 4:32 PM', amt: '−8.900', status: 'Completed'),
    (in_: true,  title: 'Refund — order #S00489', meta: 'May 20', amt: '+12.500', status: 'Pending'),
  ];
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      padding: const EdgeInsets.all(14),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: const [
          Expanded(child: Text('Recent transactions', style: UT.h3)),
          Text('Filter ▾', style: TextStyle(fontSize: 11, color: UellowColors.text)),
        ]),
        const SizedBox(height: 6),
        for (final tx in _txs) Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: UellowColors.bg)),
          ),
          child: Row(children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: tx.in_ ? UellowColors.successBg : UellowColors.dangerBg,
                borderRadius: BorderRadius.circular(10),
              ),
              alignment: Alignment.center,
              child: Text(tx.in_ ? '+' : '−', style: TextStyle(
                color: tx.in_ ? UellowColors.successDk : UellowColors.dangerDk,
                fontWeight: FontWeight.w900, fontSize: 18,
              )),
            ),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tx.title, style: const TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w700, color: UellowColors.ink)),
              Text(tx.meta, style: UT.small),
              Container(
                margin: const EdgeInsets.only(top: 3),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                decoration: BoxDecoration(
                  color: tx.status == 'Completed'
                      ? UellowColors.successBg : UellowColors.yellowSoft,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(tx.status, style: TextStyle(
                  color: tx.status == 'Completed' ? UellowColors.successDk : UellowColors.warn,
                  fontSize: 9.5, fontWeight: FontWeight.w700)),
              ),
            ])),
            Text(tx.amt, style: TextStyle(
                color: tx.in_ ? UellowColors.successDk : UellowColors.dangerDk,
                fontWeight: FontWeight.w900, fontSize: 14)),
          ]),
        ),
      ]),
    );
  }
}
