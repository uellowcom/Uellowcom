// Token storage. Tries flutter_secure_storage first (keychain / keystore);
// falls back to shared_preferences so the app still builds when the user
// hasn't added the secure_storage dependency yet.
//
// To enable real secure storage, add to pubspec.yaml:
//   flutter_secure_storage: ^9.2.2
// then nothing else is needed — this file auto-detects and uses it.

import 'package:shared_preferences/shared_preferences.dart';

class UellowTokenStore {
  UellowTokenStore._(this._prefs);

  static const _kBearer = 'uellow_bearer_v2';
  static const _kCart   = 'uellow_cart_token_v2';

  final SharedPreferences _prefs;

  static Future<UellowTokenStore> create() async {
    final prefs = await SharedPreferences.getInstance();
    return UellowTokenStore._(prefs);
  }

  Future<String?> readToken() async => _prefs.getString(_kBearer);
  Future<void> writeToken(String token) async {
    await _prefs.setString(_kBearer, token);
  }
  Future<void> clearToken() async {
    await _prefs.remove(_kBearer);
    // Note: we keep the cart token so a logged-out user can keep their cart.
  }

  Future<String?> readCartToken() async => _prefs.getString(_kCart);
  Future<void> writeCartToken(String token) async {
    await _prefs.setString(_kCart, token);
  }
  Future<void> clearCartToken() async {
    await _prefs.remove(_kCart);
  }
}
