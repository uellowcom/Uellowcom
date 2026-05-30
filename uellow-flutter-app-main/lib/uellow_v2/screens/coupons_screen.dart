// =============================================================================
// CouponsScreen — perforated coupons with tabs (Available/Used/Expired).
// =============================================================================
import 'package:flutter/material.dart';

import '../theme/uellow_theme.dart';

class CouponsScreen extends StatefulWidget {
  const CouponsScreen({super.key});
  @override
  State<CouponsScreen> createState() => _CouponsScreenState();
}

class _CouponsScreenState extends State<CouponsScreen> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      appBar: AppBar(
        leading: const BackButton(color: UellowColors.darkBrown),
        title: const Text('My Coupons', style: UT.h1),
      ),
      body: Column(children: [
        Container(
          color: Colors.white,
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: UellowColors.border)),
          ),
          child: Row(children: [
            _tabBtn('Available (5)', 0),
            _tabBtn('Used (12)', 1),
            _tabBtn('Expired (3)', 2),
          ]),
        ),
        Expanded(child: ListView(padding: const EdgeInsets.all(12), children: const [
          _Coupon(
            leftBg: _CouponBg.gold, amount: '15%', amountSub: 'OFF',
            name: '15% off any order',
            min: 'Min spend KD 20 · Max discount KD 5',
            code: 'SAVE15', expiry: '⏰ Expires in 2 days', expiryColor: UellowColors.danger,
          ),
          _Coupon(
            leftBg: _CouponBg.brown, amount: '5 KD', amountSub: 'OFF',
            name: '5 KD off new arrivals',
            min: 'Valid on selected categories',
            code: 'NEW5', expiry: '⏰ Expires Aug 15', expiryColor: UellowColors.warn,
          ),
          _Coupon(
            leftBg: _CouponBg.red, amount: '⚡', amountSub: 'FREE',
            name: 'Free same-day delivery',
            min: 'Order before 2 PM · Kuwait only',
            code: 'SAMEDAY', expiry: '⏰ Expires May 31', expiryColor: UellowColors.warn,
          ),
          _Coupon(
            leftBg: _CouponBg.gold, amount: '10%', amountSub: 'OFF',
            name: 'Loyalty member exclusive',
            min: 'Silver tier and above',
            code: 'LOYAL10', expiry: 'No expiration', expiryColor: UellowColors.muted,
          ),
          _Coupon(
            leftBg: _CouponBg.brown, amount: '2 KD', amountSub: 'CASHBACK',
            name: '2 KD cashback on KNET',
            min: 'Pay with KNET · Min 10 KD',
            code: 'KNET2', expiry: '⏰ 7 days left', expiryColor: UellowColors.warn,
          ),
        ])),
      ]),
    );
  }

  Widget _tabBtn(String label, int idx) {
    final on = _tab == idx;
    return Expanded(child: GestureDetector(
      onTap: () => setState(() => _tab = idx),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(
            color: on ? UellowColors.yellow : Colors.transparent, width: 2,
          )),
        ),
        alignment: Alignment.center,
        child: Text(label, style: TextStyle(
          color: on ? UellowColors.darkBrown : UellowColors.muted,
          fontSize: 13, fontWeight: FontWeight.w700,
        )),
      ),
    ));
  }
}

enum _CouponBg { gold, brown, red }

class _Coupon extends StatelessWidget {
  const _Coupon({
    required this.leftBg, required this.amount, required this.amountSub,
    required this.name, required this.min, required this.code,
    required this.expiry, required this.expiryColor,
  });
  final _CouponBg leftBg;
  final String amount, amountSub, name, min, code, expiry;
  final Color expiryColor;

  Gradient _gradient() {
    switch (leftBg) {
      case _CouponBg.gold:
        return const LinearGradient(
          begin: Alignment.topLeft, end: Alignment.bottomRight,
          colors: [UellowColors.yellowLight, Color(0xFFF5A800)]);
      case _CouponBg.brown:
        return const LinearGradient(
          begin: Alignment.topLeft, end: Alignment.bottomRight,
          colors: [UellowColors.darkBrown, UellowColors.darkSoft]);
      case _CouponBg.red:
        return const LinearGradient(
          begin: Alignment.topLeft, end: Alignment.bottomRight,
          colors: [UellowColors.danger, Color(0xFFC81212)]);
    }
  }

  Color _amtColor() {
    return leftBg == _CouponBg.gold ? UellowColors.darkBrown
        : (leftBg == _CouponBg.brown ? UellowColors.yellowLight : Colors.white);
  }

  @override
  Widget build(BuildContext context) {
    final amtCol = _amtColor();
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
        boxShadow: [BoxShadow(color: Color(0x0D000000), blurRadius: 4, offset: Offset(0, 1))],
      ),
      child: Stack(children: [
        Row(children: [
          // Left tear-off
          Container(
            width: 90, padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              gradient: _gradient(),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(14), bottomLeft: Radius.circular(14)),
            ),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Text(amount, style: TextStyle(
                  fontSize: 24, fontWeight: FontWeight.w900, color: amtCol, height: 1)),
              const SizedBox(height: 2),
              Text(amountSub, style: TextStyle(
                  fontSize: 10, fontWeight: FontWeight.w700, color: amtCol.withOpacity(.85))),
            ]),
          ),
          // Right body
          Expanded(child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 80, 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center, children: [
              Text(name, style: const TextStyle(
                  fontWeight: FontWeight.w800, fontSize: 13, color: UellowColors.ink)),
              const SizedBox(height: 2),
              Text(min, style: UT.small),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: const BoxDecoration(
                  color: UellowColors.border,
                  borderRadius: BorderRadius.all(Radius.circular(6)),
                ),
                child: Text(code, style: const TextStyle(
                    fontFamily: 'monospace', fontWeight: FontWeight.w800,
                    fontSize: 11, color: UellowColors.darkBrown, letterSpacing: 1)),
              ),
              const SizedBox(height: 4),
              Text(expiry, style: TextStyle(
                  color: expiryColor, fontSize: 10.5, fontWeight: FontWeight.w700)),
            ]),
          )),
        ]),
        // Perforated holes (left + right)
        _hole(left: true), _hole(left: false),
        // CTA button bottom-right
        Positioned(right: 12, bottom: 12, child: GestureDetector(
          onTap: () {},
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
            decoration: const BoxDecoration(
              color: UellowColors.darkBrown,
              borderRadius: BorderRadius.all(Radius.circular(8)),
            ),
            child: const Text('Use', style: TextStyle(
                color: UellowColors.yellowLight,
                fontSize: 11, fontWeight: FontWeight.w800)),
          ),
        )),
      ]),
    );
  }

  Widget _hole({required bool left}) {
    return Positioned(
      top: 0, bottom: 0,
      left: left ? 83 : null, right: left ? null : 0,
      child: Center(child: Container(
        width: 14, height: 14, transform: Matrix4.translationValues(left ? -7 : 7, 0, 0),
        decoration: const BoxDecoration(
            color: UellowColors.bg, shape: BoxShape.circle),
      )),
    );
  }
}
