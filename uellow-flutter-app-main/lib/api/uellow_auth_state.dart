// =============================================================================
// AuthState — ChangeNotifier wrapping the v2 client's auth lifecycle.
// =============================================================================
//
// Drop into MultiProvider; everything in the app subscribes via Provider.of /
// Consumer / context.watch. UI re-renders automatically on:
//   • login / register / social / OTP   → notifyListeners with new user
//   • logout                            → notifyListeners(null)
//   • 401 from any endpoint             → token cleared, notifyListeners(null)
//   • app start (token-already-saved)   → silent refresh via /auth/me
//
// Typical wiring:
//
//   MultiProvider(
//     providers: [
//       ChangeNotifierProvider(create: (_) => AuthState()..bootstrap()),
//       // ...
//     ],
//     child: MyApp(),
//   )
//
//   final auth = context.watch<AuthState>();
//   if (!auth.isLoggedIn) return const LoginPage();
//   return Text('Hello ${auth.user!.name}');
// =============================================================================

import 'dart:async';

import 'package:flutter/foundation.dart';

import 'uellow_api.dart';
import 'uellow_models.dart';

class AuthState extends ChangeNotifier {
  AuthState() {
    _sub = UellowApi.instance.onAuthChanged.listen(_handleAuthEvent);
  }

  UellowUser? _user;
  bool _bootstrapping = false;
  bool _busy = false;
  String? _lastError;
  late final StreamSubscription<UellowUser?> _sub;

  /// Currently authenticated user (or null for guest).
  UellowUser? get user => _user;
  bool get isLoggedIn => _user != null;
  /// True while [bootstrap] is verifying a stored token at app start.
  bool get isBootstrapping => _bootstrapping;
  /// True during any login/register/logout/refresh call.
  bool get isBusy => _busy;
  /// Last error message (cleared on next successful call). UI shows it.
  String? get lastError => _lastError;

  // ─── Bootstrap (call once after app start) ────────────────────────

  /// Verify any stored token. If valid, populate [user]; if expired,
  /// the v2 client clears it transparently and we stay in guest state.
  /// Idempotent — safe to call multiple times.
  Future<void> bootstrap() async {
    if (_user != null || _bootstrapping) return;
    final token = await UellowApi.instance.tokenStore.readToken();
    if (token == null || token.isEmpty) return;
    _bootstrapping = true;
    notifyListeners();
    try {
      _user = await UellowApi.instance.auth.me();
    } on UellowApiException catch (_) {
      // Token expired or invalid — already cleared by the client.
      _user = null;
    } finally {
      _bootstrapping = false;
      notifyListeners();
    }
  }

  // ─── Actions ──────────────────────────────────────────────────────

  Future<bool> login(String email, String password,
      {String? deviceId, String? deviceName, String? pushToken}) async {
    return _run(() async {
      final res = await UellowApi.instance.auth.login(
        email, password,
        deviceId: deviceId, deviceName: deviceName, pushToken: pushToken,
      );
      _user = res.user;
    });
  }

  Future<bool> register({
    required String name, required String email, required String password,
    String? phone, String? deviceId, String? pushToken,
  }) {
    return _run(() async {
      final res = await UellowApi.instance.auth.register(
        name: name, email: email, password: password,
        phone: phone, deviceId: deviceId, pushToken: pushToken,
      );
      _user = res.user;
    });
  }

  Future<bool> loginGoogle({
    required String email, required String providerUserId, String? name,
  }) =>
      _run(() async {
        final res = await UellowApi.instance.auth
            .google(email: email, providerUserId: providerUserId, name: name);
        _user = res.user;
      });

  Future<bool> loginApple({
    required String email, required String providerUserId, String? name,
  }) =>
      _run(() async {
        final res = await UellowApi.instance.auth
            .apple(email: email, providerUserId: providerUserId, name: name);
        _user = res.user;
      });

  Future<bool> loginFacebook({
    required String email, required String providerUserId, String? name,
  }) =>
      _run(() async {
        final res = await UellowApi.instance.auth
            .facebook(email: email, providerUserId: providerUserId, name: name);
        _user = res.user;
      });

  Future<bool> verifyOtp({
    required String phone, required String firebaseUid,
    String? name, String? deviceId, String? pushToken,
  }) =>
      _run(() async {
        final res = await UellowApi.instance.auth.verifyOtp(
          phone: phone, firebaseUid: firebaseUid,
          name: name, deviceId: deviceId, pushToken: pushToken,
        );
        _user = res.user;
      });

  Future<bool> forgotPassword(String email) =>
      _run(() async => UellowApi.instance.auth.forgotPassword(email));

  Future<void> logout() async {
    _busy = true;
    notifyListeners();
    try {
      await UellowApi.instance.auth.logout();
    } catch (_) {
      // ignore — local state is what matters
    }
    _user = null;
    _busy = false;
    notifyListeners();
  }

  Future<bool> updateProfile({
    String? name, String? phone, String? email, String? lang,
  }) =>
      _run(() async {
        _user = await UellowApi.instance.profile.update(
          name: name, phone: phone, email: email, lang: lang,
        );
      });

  Future<bool> changePassword({
    required String oldPassword, required String newPassword,
  }) =>
      _run(() async => UellowApi.instance.profile.changePassword(
            oldPassword: oldPassword, newPassword: newPassword,
          ));

  Future<bool> refresh() => _run(() async {
        _user = await UellowApi.instance.auth.me();
      });

  // ─── Internals ────────────────────────────────────────────────────

  Future<bool> _run(Future<dynamic> Function() body) async {
    _busy = true;
    _lastError = null;
    notifyListeners();
    try {
      await body();
      _busy = false;
      notifyListeners();
      return true;
    } on UellowApiException catch (e) {
      _lastError = e.message;
      _busy = false;
      notifyListeners();
      return false;
    } catch (e) {
      _lastError = e.toString();
      _busy = false;
      notifyListeners();
      return false;
    }
  }

  void _handleAuthEvent(UellowUser? user) {
    // The v2 client emits null on logout / 401. Mirror into local state.
    if (user == null) {
      if (_user != null) {
        _user = null;
        notifyListeners();
      }
    } else if (_user?.id != user.id) {
      _user = user;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _sub.cancel();
    super.dispose();
  }
}
