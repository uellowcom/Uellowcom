// =============================================================================
// TryOnScreen — virtual try-on AI preview + color swap + photo upload +
// Smart Fit measurements + recommended size.
// =============================================================================
import 'package:flutter/material.dart';

import '../theme/uellow_theme.dart';

class TryOnScreen extends StatefulWidget {
  const TryOnScreen({super.key, this.productId});
  final int? productId;
  @override
  State<TryOnScreen> createState() => _TryOnScreenState();
}

class _TryOnScreenState extends State<TryOnScreen> {
  int _color = 0;
  final _heightCtrl = TextEditingController(text: '175');
  final _weightCtrl = TextEditingController(text: '72');
  final _chestCtrl = TextEditingController(text: '98');
  final _waistCtrl = TextEditingController(text: '82');

  static const _colors = [
    Color(0xFF412402), Color(0xFFFF4D4D), Color(0xFFF5C320),
    Color(0xFF3B82F6), Colors.white,
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: UellowColors.bg,
      body: ListView(padding: EdgeInsets.zero, children: [
        _Header(),
        _CanvasCard(color: _colors[_color], colorIdx: _color,
            onColor: (i) => setState(() => _color = i)),
        const _UploadCard(),
        _SmartFitCard(
          heightCtrl: _heightCtrl, weightCtrl: _weightCtrl,
          chestCtrl: _chestCtrl, waistCtrl: _waistCtrl,
        ),
        const SizedBox(height: 30),
      ]),
    );
  }
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 18, 16),
      decoration: const BoxDecoration(gradient: UellowColors.heroWallet),
      child: SafeArea(bottom: false, child: Row(children: [
        IconButton(
          onPressed: () => Navigator.maybePop(context),
          icon: const Icon(Icons.arrow_back, color: UellowColors.yellowLight),
          padding: EdgeInsets.zero, constraints: const BoxConstraints(),
        ),
        const SizedBox(width: 8),
        const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('✨ Virtual Try-On', style: TextStyle(
              color: UellowColors.yellowLight, fontSize: 18, fontWeight: FontWeight.w800)),
          Text('See how it looks on you — powered by AI',
              style: TextStyle(color: Color(0xB3FFD340), fontSize: 12)),
        ])),
      ])),
    );
  }
}

class _CanvasCard extends StatelessWidget {
  const _CanvasCard({required this.color, required this.colorIdx, required this.onColor});
  final Color color;
  final int colorIdx;
  final ValueChanged<int> onColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(16)),
        boxShadow: [BoxShadow(color: Color(0x0F000000), blurRadius: 14, offset: Offset(0, 4))],
      ),
      child: Column(children: [
        Container(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: UellowColors.border)),
          ),
          child: Row(children: const [
            Expanded(child: Text('Preview', style: UT.h3)),
            Text('Generated in 4.2s', style: TextStyle(fontSize: 11, color: UellowColors.text)),
          ]),
        ),
        // AI generated preview (placeholder striped background)
        AspectRatio(
          aspectRatio: 3/4,
          child: Stack(children: [
            DecoratedBox(decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: const Alignment(-1, -1), end: const Alignment(1, 1),
                colors: List.generate(8, (i) => i.isEven ? UellowColors.yellowSoft : UellowColors.warnBg),
                stops: List.generate(8, (i) => i / 7),
                tileMode: TileMode.repeated,
              ),
            )),
            Center(child: Text(
              '✨', style: TextStyle(fontSize: 60, color: Colors.black.withOpacity(.6)),
            )),
            // Wearing-color hint chip (top-right)
            Positioned(top: 14, right: 14, child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(.95),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Container(width: 14, height: 14,
                    decoration: BoxDecoration(color: color, shape: BoxShape.circle,
                        border: Border.all(color: UellowColors.border))),
                const SizedBox(width: 6),
                const Text('Color', style: TextStyle(
                    fontSize: 11, fontWeight: FontWeight.w700, color: UellowColors.darkBrown)),
              ]),
            )),
            // AI badge
            Positioned(top: 14, left: 14, child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [UellowColors.yellowLight, UellowColors.yellow]),
                borderRadius: BorderRadius.all(Radius.circular(999)),
              ),
              child: const Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.star, size: 12, color: UellowColors.darkBrown),
                SizedBox(width: 4),
                Text('AI Generated', style: TextStyle(
                    color: UellowColors.darkBrown, fontWeight: FontWeight.w800, fontSize: 11)),
              ]),
            )),
          ]),
        ),
        // Color swatches
        Container(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          decoration: const BoxDecoration(
            border: Border(top: BorderSide(color: UellowColors.border)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Try different colors', style: TextStyle(
                fontSize: 12, color: UellowColors.text, fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            Row(children: [
              for (var i = 0; i < _colors.length; i++) Padding(
                padding: const EdgeInsets.only(right: 8),
                child: GestureDetector(
                  onTap: () => onColor(i),
                  child: Container(
                    width: 36, height: 36,
                    padding: const EdgeInsets.all(2),
                    decoration: BoxDecoration(
                      border: Border.all(
                        color: colorIdx == i ? UellowColors.yellow : Colors.transparent, width: 2,
                      ),
                      shape: BoxShape.circle,
                    ),
                    child: Container(
                      decoration: BoxDecoration(
                        color: _colors[i], shape: BoxShape.circle,
                        border: Border.all(color: UellowColors.border),
                      ),
                    ),
                  ),
                ),
              ),
            ]),
          ]),
        ),
        // Actions row
        Container(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
          decoration: const BoxDecoration(
            border: Border(top: BorderSide(color: UellowColors.border)),
          ),
          child: Row(children: [
            Expanded(child: _btn(Icons.share_outlined, 'Share', primary: false)),
            const SizedBox(width: 8),
            Expanded(child: _btn(Icons.person_outline, 'Ask reviewer', primary: false)),
            const SizedBox(width: 8),
            Expanded(child: _btn(Icons.shopping_cart_outlined, 'Add', primary: true)),
          ]),
        ),
      ]),
    );
  }

  Widget _btn(IconData icon, String label, {bool primary = false}) {
    return ElevatedButton(
      onPressed: () {},
      style: ElevatedButton.styleFrom(
        backgroundColor: primary ? UellowColors.yellowLight : UellowColors.border,
        foregroundColor: UellowColors.darkBrown, elevation: 0,
        padding: const EdgeInsets.symmetric(vertical: 10),
        shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(10))),
      ),
      child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        Icon(icon, size: 14),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
      ]),
    );
  }

  static const _colors = _TryOnScreenState._colors;
}

class _UploadCard extends StatelessWidget {
  const _UploadCard();
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
      padding: const EdgeInsets.fromLTRB(14, 20, 14, 20),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: UellowColors.warnBg, style: BorderStyle.solid, width: 2),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(children: [
        Container(
          width: 56, height: 56,
          decoration: const BoxDecoration(
            color: UellowColors.yellowSoft,
            borderRadius: BorderRadius.all(Radius.circular(18)),
          ),
          child: const Icon(Icons.camera_alt_outlined, size: 26, color: UellowColors.warn),
        ),
        const SizedBox(height: 10),
        const Text('Want to try with your photo?', style: UT.h3),
        const SizedBox(height: 4),
        const Text('Upload a clear front-facing photo for a personalised preview',
            textAlign: TextAlign.center, style: UT.small),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(child: ElevatedButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.camera_alt_outlined, size: 14),
            label: const Text('Camera'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 11),
              shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.all(Radius.circular(10))),
            ),
          )),
          const SizedBox(width: 8),
          Expanded(child: ElevatedButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.grid_view, size: 14),
            label: const Text('Gallery'),
            style: ElevatedButton.styleFrom(
              backgroundColor: UellowColors.border,
              foregroundColor: UellowColors.darkBrown,
              padding: const EdgeInsets.symmetric(vertical: 11),
              shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.all(Radius.circular(10))),
            ),
          )),
        ]),
      ]),
    );
  }
}

class _SmartFitCard extends StatelessWidget {
  const _SmartFitCard({
    required this.heightCtrl, required this.weightCtrl,
    required this.chestCtrl, required this.waistCtrl,
  });
  final TextEditingController heightCtrl, weightCtrl, chestCtrl, waistCtrl;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(14)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: const [
          Icon(Icons.straighten, size: 16, color: UellowColors.darkBrown),
          SizedBox(width: 6),
          Text('Smart Fit', style: UT.h3),
        ]),
        const SizedBox(height: 4),
        const Text("Enter a few measurements and we'll recommend your exact size — no more guessing.",
            style: UT.body),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: _field('Height', 'cm', heightCtrl)),
          const SizedBox(width: 8),
          Expanded(child: _field('Weight', 'kg', weightCtrl)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _field('Chest', 'cm', chestCtrl)),
          const SizedBox(width: 8),
          Expanded(child: _field('Waist', 'cm', waistCtrl)),
        ]),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [UellowColors.yellowLight, UellowColors.yellow]),
            borderRadius: BorderRadius.all(Radius.circular(12)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: const [
              Icon(Icons.check_circle, size: 14, color: UellowColors.darkBrown),
              SizedBox(width: 6),
              Text('Recommended size', style: TextStyle(
                  fontWeight: FontWeight.w800, fontSize: 13, color: UellowColors.darkBrown)),
            ]),
            const SizedBox(height: 6),
            const Text('M', style: TextStyle(
                fontSize: 36, fontWeight: FontWeight.w900, color: UellowColors.darkBrown, height: 1)),
            const SizedBox(height: 4),
            const Text('94% match · True to size · No stretch',
                style: TextStyle(fontSize: 11.5, color: Color(0xCC412402))),
            const SizedBox(height: 8),
            Wrap(spacing: 6, children: const [
              _Alt(label: 'L (relaxed fit)'),
              _Alt(label: 'S (tight fit)'),
            ]),
          ]),
        ),
        const SizedBox(height: 12),
        SizedBox(width: double.infinity, child: ElevatedButton(
          onPressed: () {},
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: const RoundedRectangleBorder(
                borderRadius: BorderRadius.all(Radius.circular(12))),
          ),
          child: const Text('Add size M to cart',
              style: TextStyle(fontWeight: FontWeight.w800)),
        )),
      ]),
    );
  }

  Widget _field(String label, String unit, TextEditingController c) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(label.toUpperCase(), style: const TextStyle(
          fontSize: 11, color: UellowColors.muted,
          fontWeight: FontWeight.w800, letterSpacing: 0.4)),
      const SizedBox(height: 4),
      Row(children: [
        Expanded(child: TextField(
          controller: c,
          keyboardType: TextInputType.number,
          style: const TextStyle(fontWeight: FontWeight.w700, color: UellowColors.darkBrown),
          decoration: InputDecoration(
            fillColor: UellowColors.yellowFaint, filled: true,
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: UellowColors.border, width: 1.5)),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: UellowColors.border, width: 1.5)),
          ),
        )),
        const SizedBox(width: 4),
        Container(
          width: 44, height: 42, alignment: Alignment.center,
          decoration: const BoxDecoration(
            color: UellowColors.border,
            borderRadius: BorderRadius.all(Radius.circular(10)),
          ),
          child: Text(unit, style: const TextStyle(
              fontWeight: FontWeight.w800, color: UellowColors.darkBrown, fontSize: 11)),
        ),
      ]),
    ]);
  }
}

class _Alt extends StatelessWidget {
  const _Alt({required this.label});
  final String label;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0x26412402),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(label, style: const TextStyle(
          fontSize: 11, color: UellowColors.darkBrown, fontWeight: FontWeight.w700)),
    );
  }
}
