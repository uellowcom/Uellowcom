// =============================================================================
// NotificationsScreen — tabbed inbox (All / Orders / Promos / Beena / System)
// grouped by day. Wires to /api/mobile/v2/notifications.
// =============================================================================
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../theme/uellow_theme.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});
  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  int _tab = 0;
  late Future<List<dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = UellowApi.instance.notifications.list();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: Column(children: [
        _Header(),
        _Tabs(active: _tab, onChange: (i) => setState(() => _tab = i)),
        Expanded(child: ListView(children: [
          _DayLabel(label: 'TODAY'),
          _Notif(
            iconBg: UellowColors.yellowSoft, iconFg: UellowColors.warn,
            icon: Icons.local_shipping_outlined,
            title: 'Out for delivery', unread: true,
            body: 'Your order #S00532 is on its way · arrives 3-5 PM',
            time: '5 minutes ago',
          ),
          _Notif(
            iconBg: UellowColors.dangerBg, iconFg: UellowColors.dangerDk,
            icon: Icons.local_offer_outlined,
            title: 'Flash sale: up to 70% off', unread: true,
            body: 'Limited time deals on smart watches · ends tonight',
            time: '1 hour ago',
          ),
          _Notif(
            iconBg: UellowColors.darkBrown, iconFg: UellowColors.yellowLight,
            icon: Icons.chat_bubble_outline,
            title: 'Beena suggested products for you', unread: true,
            body: 'Based on your search "smart watch", here are 5 picks just for you',
            time: '3 hours ago',
          ),
          _DayLabel(label: 'YESTERDAY'),
          _Notif(
            iconBg: UellowColors.yellowSoft, iconFg: UellowColors.warn,
            icon: Icons.check_circle_outline,
            title: 'Order packed',
            body: 'Your order #S00532 has been packed and is ready to ship',
            time: 'Yesterday at 2:14 PM',
          ),
          _Notif(
            iconBg: UellowColors.successBg, iconFg: UellowColors.successDk,
            icon: Icons.star_outline,
            title: 'You earned 150 loyalty points',
            body: 'Thanks for your purchase · 150 pts added to your account',
            time: 'Yesterday at 11:30 AM',
          ),
          _Notif(
            iconBg: UellowColors.dangerBg, iconFg: UellowColors.dangerDk,
            icon: Icons.card_giftcard,
            title: '⬇ Price drop on your wishlist',
            body: '"HainoTeko Watch" dropped from 12.000 → 8.500 KD (-29%)',
            time: 'Yesterday at 9:12 AM',
          ),
          _DayLabel(label: 'EARLIER'),
          _Notif(
            iconBg: UellowColors.successBg, iconFg: UellowColors.successDk,
            icon: Icons.shield_outlined,
            title: 'New login from iPhone 16 Pro',
            body: "If this wasn't you, secure your account immediately",
            time: '3 days ago',
          ),
          _Notif(
            iconBg: UellowColors.darkBrown, iconFg: UellowColors.yellowLight,
            icon: Icons.auto_awesome,
            title: 'Try Beena\'s new visual search',
            body: 'Take a photo of any product and let Beena find it for you',
            time: '5 days ago',
          ),
          const SizedBox(height: 30),
        ])),
      ]),
    );
  }
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
      child: Row(children: [
        IconButton(onPressed: () => Navigator.maybePop(context),
            icon: const Icon(Icons.arrow_back, color: UellowColors.darkBrown),
            padding: EdgeInsets.zero, constraints: const BoxConstraints()),
        const SizedBox(width: 6),
        const Expanded(child: Text('Notifications', style: UT.h1)),
        const Text('Mark all read', style: TextStyle(
            color: UellowColors.text, fontWeight: FontWeight.w700, fontSize: 12)),
      ]),
    );
  }
}

class _Tabs extends StatelessWidget {
  const _Tabs({required this.active, required this.onChange});
  final int active;
  final ValueChanged<int> onChange;
  static const _tabs = [
    ('All', 12), ('Orders', 3), ('Promos', 5),
    ('Beena AI', 2), ('System', 0),
  ];
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      child: SizedBox(height: 30, child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _tabs.length,
        separatorBuilder: (_, __) => const SizedBox(width: 4),
        itemBuilder: (_, i) {
          final t = _tabs[i];
          final on = i == active;
          return GestureDetector(
            onTap: () => onChange(i),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: on ? UellowColors.darkBrown : UellowColors.border,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(t.$1, style: TextStyle(
                  color: on ? UellowColors.yellowLight : UellowColors.text,
                  fontSize: 11.5, fontWeight: FontWeight.w700)),
                if (t.$2 > 0) ...[
                  const SizedBox(width: 5),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                    decoration: BoxDecoration(
                      color: on ? UellowColors.yellowLight : UellowColors.danger,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text('${t.$2}', style: TextStyle(
                      color: on ? UellowColors.darkBrown : Colors.white,
                      fontSize: 9.5, fontWeight: FontWeight.w900)),
                  ),
                ],
              ]),
            ),
          );
        },
      )),
    );
  }
}

class _DayLabel extends StatelessWidget {
  const _DayLabel({required this.label});
  final String label;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 6),
      child: Text(label, style: const TextStyle(
          fontSize: 11, color: UellowColors.muted,
          fontWeight: FontWeight.w700, letterSpacing: 0.5)),
    );
  }
}

class _Notif extends StatelessWidget {
  const _Notif({
    required this.iconBg, required this.iconFg, required this.icon,
    required this.title, required this.body, required this.time, this.unread = false,
  });
  final Color iconBg, iconFg;
  final IconData icon;
  final String title, body, time;
  final bool unread;
  @override
  Widget build(BuildContext context) {
    return Container(
      color: unread ? UellowColors.yellowFaint : Colors.white,
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: UellowColors.bg)),
      ),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          width: 38, height: 38,
          decoration: BoxDecoration(color: iconBg, borderRadius: BorderRadius.circular(12)),
          child: Icon(icon, size: 20, color: iconFg),
        ),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(title, style: const TextStyle(
                fontWeight: FontWeight.w800, fontSize: 13, color: UellowColors.ink))),
            if (unread) Container(
              width: 7, height: 7,
              decoration: const BoxDecoration(
                  color: UellowColors.danger, shape: BoxShape.circle),
            ),
          ]),
          const SizedBox(height: 3),
          Text(body, style: const TextStyle(
              fontSize: 12.5, color: UellowColors.text, height: 1.4)),
          const SizedBox(height: 2),
          Text(time, style: UT.small),
        ])),
      ]),
    );
  }
}
