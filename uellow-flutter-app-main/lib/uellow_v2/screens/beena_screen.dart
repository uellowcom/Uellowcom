// =============================================================================
// BeenaScreen — AI chat with product suggestions, voice/visual entry,
// typing indicator, quick-action chips. Wires to /api/mobile/v2/beena/chat.
// =============================================================================
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../theme/uellow_theme.dart';

class BeenaScreen extends StatefulWidget {
  const BeenaScreen({super.key});
  @override
  State<BeenaScreen> createState() => _BeenaScreenState();
}

class _BeenaScreenState extends State<BeenaScreen> {
  final _ctrl = TextEditingController();
  final _scroll = ScrollController();
  bool _typing = false;
  final _msgs = <_Msg>[
    _Msg(isUser: false, text: "Hi Ali! 👋 I'm Beena. I can find products, track orders, redeem points, or just chat. What's up?"),
    _Msg(isUser: true, text: 'عندي مناسبة عيد ميلاد، اقترح علي ساعة ذكية مناسبة كهدية لشاب'),
    _Msg(isUser: false, text: 'اختيار رائع 🎂 إليك أفضل ٣ ساعات ذكية:', suggestions: const [
      ('W1', 'HainoTeko Pro Watch', '14.900 KD'),
      ('W2', 'Huawei GT4 Pro', '65.000 KD'),
      ('W3', 'Apple Watch SE', '95.500 KD'),
    ]),
  ];

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _msgs.add(_Msg(isUser: true, text: text));
      _ctrl.clear();
      _typing = true;
    });
    _scrollToEnd();
    try {
      final res = await UellowApi.instance.beena.chat(message: text);
      final reply = res['reply'] ?? res['text'] ?? 'Got it!';
      if (!mounted) return;
      setState(() {
        _msgs.add(_Msg(isUser: false, text: '$reply'));
        _typing = false;
      });
    } on UellowApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _msgs.add(_Msg(isUser: false, text: 'Sorry, I had trouble: ${e.message}'));
        _typing = false;
      });
    }
    _scrollToEnd();
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      body: SafeArea(child: Column(children: [
        _Header(),
        const _ChipsBar(),
        Expanded(child: ListView.builder(
          controller: _scroll,
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
          itemCount: _msgs.length + (_typing ? 1 : 0),
          itemBuilder: (_, i) {
            if (_typing && i == _msgs.length) return const _TypingBubble();
            return _MsgBubble(msg: _msgs[i]);
          },
        )),
        _InputBar(ctrl: _ctrl, onSend: _send),
      ])),
    );
  }
}

class _Msg {
  _Msg({required this.isUser, required this.text, this.suggestions});
  final bool isUser;
  final String text;
  final List<(String, String, String)>? suggestions;
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 18, 16),
      decoration: const BoxDecoration(gradient: UellowColors.heroWallet),
      child: Row(children: [
        IconButton(
          onPressed: () => Navigator.maybePop(context),
          icon: const Icon(Icons.arrow_back, color: UellowColors.yellowLight),
          padding: EdgeInsets.zero, constraints: const BoxConstraints(),
        ),
        const SizedBox(width: 8),
        Container(
          width: 48, height: 48,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              center: Alignment(-0.4, -0.5),
              colors: [Color(0xFFFFE45E), UellowColors.yellow, Color(0xFFC99000)],
            ),
            boxShadow: [BoxShadow(color: Color(0x80F5C320), blurRadius: 12, offset: Offset(0, 4))],
          ),
          alignment: Alignment.center,
          child: const Text('✨', style: TextStyle(fontSize: 22)),
        ),
        const SizedBox(width: 12),
        const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Beena AI', style: TextStyle(
              color: UellowColors.yellowLight, fontSize: 17, fontWeight: FontWeight.w800)),
          Text('🟢 online · powered by Uellow',
              style: TextStyle(color: Color(0x99FFD340), fontSize: 12)),
        ])),
      ]),
    );
  }
}

class _ChipsBar extends StatelessWidget {
  const _ChipsBar();
  static const _chips = ['📸 Visual search','📦 Track my order','🎁 Use my points',
      '💬 Ask a question','🎂 Gift ideas'];
  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: UellowColors.border)),
      ),
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: SizedBox(height: 32, child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        itemCount: _chips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 6),
        itemBuilder: (_, i) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            color: UellowColors.yellowSoft,
            border: Border.all(color: UellowColors.warnBg),
            borderRadius: BorderRadius.circular(999),
          ),
          alignment: Alignment.center,
          child: Text(_chips[i], style: const TextStyle(
              color: UellowColors.darkBrown, fontSize: 12, fontWeight: FontWeight.w600)),
        ),
      )),
    );
  }
}

class _MsgBubble extends StatelessWidget {
  const _MsgBubble({required this.msg});
  final _Msg msg;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisAlignment: msg.isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          if (!msg.isUser) _avatar(),
          if (!msg.isUser) const SizedBox(width: 10),
          ConstrainedBox(
            constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
            child: Column(
              crossAxisAlignment: msg.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: msg.isUser ? UellowColors.darkBrown : Colors.white,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(16),
                      topRight: const Radius.circular(16),
                      bottomLeft: msg.isUser ? const Radius.circular(16) : const Radius.circular(6),
                      bottomRight: msg.isUser ? const Radius.circular(6) : const Radius.circular(16),
                    ),
                    boxShadow: msg.isUser ? null
                        : [const BoxShadow(color: Color(0x0D000000), blurRadius: 4)],
                  ),
                  child: Text(msg.text, style: TextStyle(
                    color: msg.isUser ? UellowColors.yellowLight : UellowColors.ink,
                    fontSize: 13.5, height: 1.5,
                  )),
                ),
                if (msg.suggestions != null) _suggestions(msg.suggestions!),
              ],
            ),
          ),
          if (msg.isUser) const SizedBox(width: 10),
          if (msg.isUser) _userAvatar(),
        ],
      ),
    );
  }

  Widget _avatar() => Container(
    width: 28, height: 28,
    decoration: const BoxDecoration(
        color: UellowColors.yellowLight, shape: BoxShape.circle),
    alignment: Alignment.center,
    child: const Text('B', style: TextStyle(
        color: UellowColors.darkBrown, fontWeight: FontWeight.w800, fontSize: 12)),
  );

  Widget _userAvatar() => Container(
    width: 28, height: 28,
    decoration: const BoxDecoration(
        color: UellowColors.darkBrown, shape: BoxShape.circle),
    alignment: Alignment.center,
    child: const Text('A', style: TextStyle(
        color: UellowColors.yellowLight, fontWeight: FontWeight.w800, fontSize: 12)),
  );

  Widget _suggestions(List<(String, String, String)> items) {
    final colors = [UellowColors.yellow, UellowColors.darkBrown, const Color(0xFFFFE066)];
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: SizedBox(height: 160, child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final it = items[i];
          return SizedBox(width: 130, child: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: UellowColors.border),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(
                width: double.infinity, height: 70,
                decoration: BoxDecoration(
                  color: colors[i % colors.length],
                  borderRadius: BorderRadius.circular(6),
                ),
                alignment: Alignment.center,
                child: Text(it.$1, style: const TextStyle(
                    color: Colors.white, fontWeight: FontWeight.w900)),
              ),
              const SizedBox(height: 4),
              Text(it.$2, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11, color: UellowColors.ink)),
              const SizedBox(height: 2),
              Text(it.$3, style: const TextStyle(
                  fontWeight: FontWeight.w800, fontSize: 12, color: UellowColors.darkBrown)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(vertical: 4),
                decoration: const BoxDecoration(
                  color: UellowColors.yellowLight,
                  borderRadius: BorderRadius.all(Radius.circular(6)),
                ),
                alignment: Alignment.center,
                child: const Text('View', style: TextStyle(
                    color: UellowColors.darkBrown, fontSize: 10, fontWeight: FontWeight.w800)),
              ),
            ]),
          ));
        },
      )),
    );
  }
}

class _TypingBubble extends StatefulWidget {
  const _TypingBubble();
  @override
  State<_TypingBubble> createState() => _TypingBubbleState();
}

class _TypingBubbleState extends State<_TypingBubble> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 900))
      ..repeat();
  }
  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return Padding(padding: const EdgeInsets.only(bottom: 12), child: Row(children: [
      Container(
        width: 28, height: 28,
        decoration: const BoxDecoration(color: UellowColors.yellowLight, shape: BoxShape.circle),
        alignment: Alignment.center,
        child: const Text('B', style: TextStyle(
            color: UellowColors.darkBrown, fontWeight: FontWeight.w800, fontSize: 12)),
      ),
      const SizedBox(width: 10),
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(16), topRight: Radius.circular(16),
            bottomLeft: Radius.circular(6), bottomRight: Radius.circular(16),
          ),
          boxShadow: [BoxShadow(color: Color(0x0D000000), blurRadius: 4)],
        ),
        child: AnimatedBuilder(
          animation: _ctrl,
          builder: (_, __) => Row(mainAxisSize: MainAxisSize.min, children: List.generate(3, (i) {
            final t = (_ctrl.value + i * 0.2) % 1;
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 1.5),
              child: Container(
                width: 6, height: 6,
                decoration: BoxDecoration(
                  color: Color.lerp(const Color(0xFFCCCCCC), UellowColors.muted, t)!,
                  shape: BoxShape.circle,
                ),
              ),
            );
          })),
        ),
      ),
    ]));
  }
}

class _InputBar extends StatelessWidget {
  const _InputBar({required this.ctrl, required this.onSend});
  final TextEditingController ctrl;
  final VoidCallback onSend;
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: UellowColors.border)),
      ),
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
      child: SafeArea(top: false, child: Row(children: [
        _iconBtn(Icons.camera_alt_outlined, () {}),
        const SizedBox(width: 6),
        _iconBtn(Icons.mic_none_outlined, () {}),
        const SizedBox(width: 6),
        Expanded(child: TextField(
          controller: ctrl,
          textInputAction: TextInputAction.send,
          onSubmitted: (_) => onSend(),
          decoration: const InputDecoration(
            hintText: 'اكتب رسالتك…',
            contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 11),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.all(Radius.circular(18)),
              borderSide: BorderSide.none),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.all(Radius.circular(18)),
              borderSide: BorderSide.none),
            fillColor: UellowColors.border, filled: true,
          ),
        )),
        const SizedBox(width: 6),
        _iconBtn(Icons.send, onSend, primary: true),
      ])),
    );
  }
  Widget _iconBtn(IconData icon, VoidCallback onTap, {bool primary = false}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 42, height: 42,
        decoration: BoxDecoration(
          color: primary ? UellowColors.yellowLight : UellowColors.border,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, size: 18,
            color: primary ? UellowColors.darkBrown : UellowColors.text),
      ),
    );
  }
}
