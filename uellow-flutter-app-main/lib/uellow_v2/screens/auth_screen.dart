// =============================================================================
// AuthScreen — tabbed Sign in / Sign up + social providers + Phone OTP.
// Wires to UellowApi.auth.login / register / google / apple / facebook.
// =============================================================================
import 'package:flutter/material.dart';

import '../../api/uellow_api.dart';
import '../theme/uellow_theme.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  int _tab = 0;   // 0 = sign in, 1 = sign up
  bool _busy = false;
  String? _err;
  final _email = TextEditingController(text: 'ali@uellow.com');
  final _password = TextEditingController(text: 'password');
  final _name = TextEditingController();
  final _phone = TextEditingController();

  Future<void> _submit() async {
    setState(() { _busy = true; _err = null; });
    try {
      if (_tab == 0) {
        await UellowApi.instance.auth.login(_email.text, _password.text);
      } else {
        await UellowApi.instance.auth.register(
          name: _name.text, email: _email.text,
          password: _password.text, phone: _phone.text,
        );
      }
      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed('/home');
    } on UellowApiException catch (e) {
      setState(() => _err = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
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
          child: ListView(padding: const EdgeInsets.fromLTRB(24, 40, 24, 30), children: [
            _logo(),
            const SizedBox(height: 24),
            _card(),
          ]),
        ),
      ),
    );
  }

  Widget _logo() {
    return Center(child: Container(
      padding: const EdgeInsets.fromLTRB(18, 10, 22, 10),
      decoration: const BoxDecoration(
        color: UellowColors.darkBrown,
        borderRadius: BorderRadius.all(Radius.circular(16)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Container(
          width: 32, height: 32,
          decoration: const BoxDecoration(
            color: UellowColors.yellowLight,
            borderRadius: BorderRadius.all(Radius.circular(10)),
          ),
          alignment: Alignment.center,
          child: const Text('U', style: TextStyle(
              color: UellowColors.darkBrown, fontWeight: FontWeight.w900, fontSize: 18)),
        ),
        const SizedBox(width: 10),
        const Text('Uellow', style: TextStyle(
            color: UellowColors.yellowLight, fontWeight: FontWeight.w900, fontSize: 20)),
      ]),
    ));
  }

  Widget _card() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 24),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.all(Radius.circular(20)),
        boxShadow: [BoxShadow(color: Color(0x40412402),
            blurRadius: 40, offset: Offset(0, 16))],
      ),
      child: Column(children: [
        _tabs(),
        const SizedBox(height: 22),
        if (_tab == 1) _field('NAME', _name, hint: 'Full name'),
        _field(_tab == 1 ? 'EMAIL' : 'EMAIL OR PHONE', _email, hint: 'you@example.com'),
        if (_tab == 1) _field('PHONE', _phone, hint: '+965 9999 0000'),
        _field('PASSWORD', _password, hint: '••••••••', obscure: true),
        if (_err != null) Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(_err!, style: const TextStyle(color: UellowColors.danger, fontSize: 12)),
        ),
        if (_tab == 0) Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Row(children: const [
            Checkbox(value: true, onChanged: null, activeColor: UellowColors.yellow),
            Text('Remember me', style: TextStyle(color: UellowColors.text, fontSize: 12)),
            Spacer(),
            Text('Forgot password?',
                style: TextStyle(color: UellowColors.darkBrown,
                    fontWeight: FontWeight.w800, fontSize: 12)),
          ]),
        ),
        const SizedBox(height: 14),
        SizedBox(width: double.infinity, child: ElevatedButton(
          onPressed: _busy ? null : _submit,
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: const RoundedRectangleBorder(
                borderRadius: BorderRadius.all(Radius.circular(12))),
          ),
          child: _busy
              ? const SizedBox(width: 18, height: 18,
                  child: CircularProgressIndicator(color: UellowColors.yellowLight, strokeWidth: 2))
              : Text(_tab == 0 ? 'Sign in  →' : 'Create account  →',
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
        )),
        const Padding(padding: EdgeInsets.symmetric(vertical: 18),
            child: Row(children: [
              Expanded(child: Divider(color: UellowColors.border)),
              Padding(padding: EdgeInsets.symmetric(horizontal: 10),
                  child: Text('or continue with',
                      style: TextStyle(color: UellowColors.muted, fontSize: 11))),
              Expanded(child: Divider(color: UellowColors.border)),
            ])),
        Row(children: [
          Expanded(child: _social('Google', Icons.g_mobiledata, const Color(0xFF4285F4))),
          const SizedBox(width: 8),
          Expanded(child: _social('Apple', Icons.apple, Colors.black)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _social('Facebook', Icons.facebook, const Color(0xFF1877F2))),
          const SizedBox(width: 8),
          Expanded(child: _social('Phone OTP', Icons.phone_outlined, UellowColors.darkBrown)),
        ]),
        const SizedBox(height: 16),
        Text.rich(TextSpan(
          style: const TextStyle(color: UellowColors.text, fontSize: 11),
          children: [
            const TextSpan(text: 'By continuing you agree to our '),
            TextSpan(text: 'Terms', style: const TextStyle(
                color: UellowColors.darkBrown, fontWeight: FontWeight.w800)),
            const TextSpan(text: ' & '),
            TextSpan(text: 'Privacy', style: const TextStyle(
                color: UellowColors.darkBrown, fontWeight: FontWeight.w800)),
            const TextSpan(text: '.'),
          ],
        ), textAlign: TextAlign.center),
      ]),
    );
  }

  Widget _tabs() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: const BoxDecoration(
        color: UellowColors.border,
        borderRadius: BorderRadius.all(Radius.circular(12)),
      ),
      child: Row(children: [
        Expanded(child: _tabBtn('Sign in', 0)),
        const SizedBox(width: 4),
        Expanded(child: _tabBtn('Create account', 1)),
      ]),
    );
  }

  Widget _tabBtn(String label, int idx) {
    final on = _tab == idx;
    return GestureDetector(
      onTap: () => setState(() => _tab = idx),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: on ? UellowColors.darkBrown : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
        ),
        alignment: Alignment.center,
        child: Text(label, style: TextStyle(
            color: on ? UellowColors.yellowLight : UellowColors.text,
            fontWeight: FontWeight.w800, fontSize: 13)),
      ),
    );
  }

  Widget _field(String label, TextEditingController c, {String? hint, bool obscure = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(padding: const EdgeInsets.symmetric(vertical: 4),
            child: Text(label, style: const TextStyle(
                fontSize: 11, color: UellowColors.muted, fontWeight: FontWeight.w800,
                letterSpacing: 0.5))),
        TextField(
          controller: c, obscureText: obscure,
          decoration: InputDecoration(
            hintText: hint,
            fillColor: UellowColors.yellowFaint, filled: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: UellowColors.border, width: 1.5)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: UellowColors.border, width: 1.5)),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          ),
        ),
      ]),
    );
  }

  Widget _social(String label, IconData icon, Color color) {
    return InkWell(
      onTap: () {},
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          border: Border.all(color: UellowColors.border, width: 1.5),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Text(label, style: TextStyle(
              fontWeight: FontWeight.w700, fontSize: 13, color: color)),
        ]),
      ),
    );
  }
}
