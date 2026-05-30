// =============================================================================
// Uellow Mobile API Client — v2
// =============================================================================
//
// One file, one client, one error path. Replaces the legacy WooCommerce-style
// `base_woo_api.dart` and the dozen `*_api.dart` files in `lib/services/`.
//
// Usage:
//   final api = UellowApi.instance;
//   final user = await api.auth.login('email@x.com', 'pw');
//   final products = await api.products.list(page: 1, perPage: 20);
//   final cart = await api.cart.add(productId: 1786, qty: 1);
//
// Auth:
//   Token is issued by `/auth/login` and stored in flutter_secure_storage.
//   Every subsequent request adds `Authorization: Bearer <token>` automatically.
//   Logout clears it. 401 responses also clear it (kicks user to login).
//
// Errors:
//   Every method throws `UellowApiException` on failure. The exception has
//   `.code` (machine-friendly: AUTH_REQUIRED / NOT_FOUND / VALIDATION / ...)
//   and `.message` (already localized by the server for the active lang).
//
// Bilingual text:
//   Fields like product names come back as `{en: ..., ar: ...}`. Use the
//   helper `.localized(context)` extension on the typed models — never hardcode
//   one language.
// =============================================================================

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'uellow_endpoints.dart';
import 'uellow_models.dart';
import 'uellow_token_store.dart';

/// Base URL of the Odoo instance hosting the v2 API. Switch with
/// `--dart-define=UELLOW_API_BASE=https://staging.uellow.com` for staging.
const String kUellowApiBase = String.fromEnvironment(
  'UELLOW_API_BASE',
  defaultValue: 'https://www.uellow.com',
);

/// Default request timeout. Network-level only; the server has its own.
const Duration kDefaultTimeout = Duration(seconds: 25);

// =============================================================================
// Exceptions
// =============================================================================

class UellowApiException implements Exception {
  final String code;
  final String message;
  final int statusCode;
  final Map<String, dynamic>? raw;

  const UellowApiException({
    required this.code,
    required this.message,
    required this.statusCode,
    this.raw,
  });

  bool get isAuthError =>
      code == 'AUTH_REQUIRED' || statusCode == 401;
  bool get isNotFound => code == 'NOT_FOUND' || statusCode == 404;
  bool get isNetwork => code == 'NETWORK_ERROR';
  bool get isServer => statusCode >= 500;

  @override
  String toString() => 'UellowApiException($code, $statusCode): $message';
}

// =============================================================================
// Core client
// =============================================================================

class UellowApi {
  UellowApi._({
    required this.baseUrl,
    required this.tokenStore,
    required http.Client httpClient,
  }) : _http = httpClient {
    auth          = _AuthApi(this);
    profile       = _ProfileApi(this);
    home          = _HomeApi(this);
    products      = _ProductsApi(this);
    categories    = _CategoriesApi(this);
    cart          = _CartApi(this);
    orders        = _OrdersApi(this);
    addresses     = _AddressesApi(this);
    wishlist      = _WishlistApi(this);
    search        = _SearchApi(this);
    reviews       = _ReviewsApi(this);
    loyalty       = _LoyaltyApi(this);
    wallet        = _WalletApi(this);
    notifications = _NotificationsApi(this);
    beena         = _BeenaApi(this);
    settings      = _SettingsApi(this);
  }

  /// Singleton. Initialize once at app start via [UellowApi.init].
  static late UellowApi instance;

  /// Initialize the singleton. Call this in `main()` before any usage.
  /// The default constructor uses the real HTTP client and the secure
  /// token storage — only override for tests.
  static Future<UellowApi> init({
    String? baseUrl,
    UellowTokenStore? tokenStore,
    http.Client? httpClient,
  }) async {
    final store = tokenStore ?? await UellowTokenStore.create();
    instance = UellowApi._(
      baseUrl: (baseUrl ?? kUellowApiBase).replaceAll(RegExp(r'/$'), ''),
      tokenStore: store,
      httpClient: httpClient ?? http.Client(),
    );
    return instance;
  }

  final String baseUrl;
  final UellowTokenStore tokenStore;
  final http.Client _http;

  /// Active language, two letters ('ar' or 'en'). The host app sets this
  /// based on `Localizations.localeOf(context)` — pass it via [setLang].
  String _lang = 'en';
  void setLang(String code) {
    _lang = code.toLowerCase().startsWith('ar') ? 'ar' : 'en';
  }
  String get lang => _lang;

  /// App version + platform, sent on every request so the server can decide
  /// version gates / log analytics. Set once at startup.
  String _appVersion = '1.0.0';
  String _platform = 'android';
  void setAppMeta({required String appVersion, required String platform}) {
    _appVersion = appVersion;
    _platform = platform;
  }

  // ─── Resource APIs ───────────────────────────────────────────────────
  late final _AuthApi auth;
  late final _ProfileApi profile;
  late final _HomeApi home;
  late final _ProductsApi products;
  late final _CategoriesApi categories;
  late final _CartApi cart;
  late final _OrdersApi orders;
  late final _AddressesApi addresses;
  late final _WishlistApi wishlist;
  late final _SearchApi search;
  late final _ReviewsApi reviews;
  late final _LoyaltyApi loyalty;
  late final _WalletApi wallet;
  late final _NotificationsApi notifications;
  late final _BeenaApi beena;
  late final _SettingsApi settings;

  // ─── Auth listener (lets ui react to 401 / logout) ───────────────────

  final _authChangedController = StreamController<UellowUser?>.broadcast();
  Stream<UellowUser?> get onAuthChanged => _authChangedController.stream;
  void _emitAuth(UellowUser? user) => _authChangedController.add(user);

  // ─── Low-level request ───────────────────────────────────────────────

  Future<Map<String, dynamic>> _request(
    String method,
    String path, {
    Map<String, dynamic>? query,
    Object? body,
    bool requireAuth = false,
    Duration timeout = kDefaultTimeout,
  }) async {
    final url = Uri.parse('$baseUrl$path').replace(
      queryParameters: {
        ...?query?.map((k, v) => MapEntry(k, '$v')),
      },
    );

    final headers = <String, String>{
      'Content-Type': 'application/json; charset=utf-8',
      'Accept': 'application/json',
      'X-Lang': _lang,
      'X-App-Version': _appVersion,
      'X-Platform': _platform,
    };
    final token = await tokenStore.readToken();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    } else if (requireAuth) {
      throw const UellowApiException(
        code: 'AUTH_REQUIRED',
        message: 'You must be logged in.',
        statusCode: 401,
      );
    }
    final cartToken = await tokenStore.readCartToken();
    if (cartToken != null && cartToken.isNotEmpty) {
      headers['X-Cart-Token'] = cartToken;
    }

    http.Response resp;
    try {
      switch (method) {
        case 'GET':
          resp = await _http.get(url, headers: headers).timeout(timeout);
          break;
        case 'POST':
          resp = await _http
              .post(url,
                  headers: headers,
                  body: body == null ? null : jsonEncode(body))
              .timeout(timeout);
          break;
        case 'PUT':
          resp = await _http
              .put(url,
                  headers: headers,
                  body: body == null ? null : jsonEncode(body))
              .timeout(timeout);
          break;
        case 'DELETE':
          resp = await _http.delete(url, headers: headers).timeout(timeout);
          break;
        default:
          throw UellowApiException(
              code: 'BAD_METHOD',
              message: 'Unsupported HTTP method $method',
              statusCode: 0);
      }
    } on SocketException catch (e) {
      throw UellowApiException(
        code: 'NETWORK_ERROR',
        message: 'No internet connection: ${e.message}',
        statusCode: 0,
      );
    } on TimeoutException {
      throw const UellowApiException(
        code: 'TIMEOUT',
        message: 'Request timed out',
        statusCode: 0,
      );
    } on HttpException catch (e) {
      throw UellowApiException(
        code: 'NETWORK_ERROR',
        message: e.message,
        statusCode: 0,
      );
    }

    if (kDebugMode) {
      debugPrint('UellowApi $method ${url.path} → ${resp.statusCode}');
    }

    Map<String, dynamic> json;
    try {
      json = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    } catch (_) {
      throw UellowApiException(
        code: 'BAD_RESPONSE',
        message: 'Server returned non-JSON (status ${resp.statusCode})',
        statusCode: resp.statusCode,
      );
    }

    // Unified envelope: {success, data, meta, error, code}
    if (json['success'] == true) {
      return json;
    }
    final code = (json['code'] as String?) ?? 'UNKNOWN';
    final msg  = (json['error'] as String?) ?? 'Unknown error';

    // 401 → invalidate stored token + emit auth-changed
    if (resp.statusCode == 401 || code == 'AUTH_REQUIRED') {
      await tokenStore.clearToken();
      _emitAuth(null);
    }
    throw UellowApiException(
      code: code,
      message: msg,
      statusCode: resp.statusCode,
      raw: json,
    );
  }

  // Convenience shortcuts
  Future<Map<String, dynamic>> _get(String path,
          {Map<String, dynamic>? query, bool auth = false}) =>
      _request('GET', path, query: query, requireAuth: auth);
  Future<Map<String, dynamic>> _post(String path,
          {Object? body, bool auth = false}) =>
      _request('POST', path, body: body, requireAuth: auth);

  void dispose() {
    _http.close();
    _authChangedController.close();
  }
}

// =============================================================================
// Resource APIs — thin wrappers around _request that produce typed models
// =============================================================================

class _AuthApi {
  _AuthApi(this._c);
  final UellowApi _c;

  Future<UellowAuthResult> login(String email, String password,
      {String? deviceId, String? deviceName, String? pushToken, String? appVersion}) async {
    final res = await _c._post(EP.authLogin, body: {
      'email': email,
      'password': password,
      if (deviceId   != null) 'device_id': deviceId,
      if (deviceName != null) 'device_name': deviceName,
      if (pushToken  != null) 'push_token': pushToken,
      if (appVersion != null) 'app_version': appVersion,
    });
    return _saveAuth(res);
  }

  Future<UellowAuthResult> register({
    required String name,
    required String email,
    required String password,
    String? phone,
    String? deviceId,
    String? pushToken,
  }) async {
    final res = await _c._post(EP.authRegister, body: {
      'name': name, 'email': email, 'password': password,
      if (phone     != null) 'phone': phone,
      if (deviceId  != null) 'device_id': deviceId,
      if (pushToken != null) 'push_token': pushToken,
    });
    return _saveAuth(res);
  }

  Future<UellowAuthResult> verifyOtp({
    required String phone,
    required String firebaseUid,
    String? name,
    String? deviceId,
    String? pushToken,
  }) async {
    final res = await _c._post(EP.authOtpVerify, body: {
      'phone': phone, 'firebase_uid': firebaseUid,
      if (name      != null) 'name': name,
      if (deviceId  != null) 'device_id': deviceId,
      if (pushToken != null) 'push_token': pushToken,
    });
    return _saveAuth(res);
  }

  Future<UellowAuthResult> google({
    required String email, required String providerUserId, String? name,
  }) =>
      _social('/api/mobile/v2/auth/social/google', email, providerUserId, name);
  Future<UellowAuthResult> apple({
    required String email, required String providerUserId, String? name,
  }) =>
      _social('/api/mobile/v2/auth/social/apple', email, providerUserId, name);
  Future<UellowAuthResult> facebook({
    required String email, required String providerUserId, String? name,
  }) =>
      _social('/api/mobile/v2/auth/social/facebook', email, providerUserId, name);

  Future<UellowAuthResult> _social(
      String path, String email, String providerUid, String? name) async {
    final res = await _c._post(path, body: {
      'email': email,
      'provider_user_id': providerUid,
      if (name != null) 'name': name,
    });
    return _saveAuth(res);
  }

  Future<bool> forgotPassword(String email) async {
    final res = await _c._post(EP.authForgot, body: {'email': email});
    return res['data']?['sent'] == true;
  }

  Future<void> logout() async {
    try {
      await _c._post(EP.authLogout, auth: true);
    } catch (_) {
      // Even if the server call fails, clear local state.
    }
    await _c.tokenStore.clearToken();
    _c._emitAuth(null);
  }

  Future<UellowUser> me() async {
    final res = await _c._get(EP.authMe, auth: true);
    return UellowUser.fromJson(res['data']['user'] as Map<String, dynamic>);
  }

  Future<UellowAuthResult> _saveAuth(Map<String, dynamic> res) async {
    final data = res['data'] as Map<String, dynamic>;
    final token = data['token'] as String;
    final user = UellowUser.fromJson(data['user'] as Map<String, dynamic>);
    await _c.tokenStore.writeToken(token);
    _c._emitAuth(user);
    return UellowAuthResult(token: token, user: user);
  }
}

class _ProfileApi {
  _ProfileApi(this._c);
  final UellowApi _c;

  Future<UellowUser> update({
    String? name, String? phone, String? email, String? lang,
  }) async {
    final res = await _c._post(EP.profileUpdate, auth: true, body: {
      if (name  != null) 'name': name,
      if (phone != null) 'phone': phone,
      if (email != null) 'email': email,
      if (lang  != null) 'lang': lang,
    });
    return UellowUser.fromJson(res['data']['user'] as Map<String, dynamic>);
  }

  Future<bool> changePassword({
    required String oldPassword, required String newPassword,
  }) async {
    final res = await _c._post(EP.profileChangePassword, auth: true, body: {
      'old_password': oldPassword,
      'new_password': newPassword,
    });
    return res['data']?['changed'] == true;
  }

  Future<void> deleteAccount() async {
    await _c._post(EP.profileDelete, auth: true);
    await _c.tokenStore.clearToken();
    _c._emitAuth(null);
  }
}

class _HomeApi {
  _HomeApi(this._c);
  final UellowApi _c;

  Future<UellowHome> get() async {
    final res = await _c._get(EP.home);
    return UellowHome.fromJson(res['data'] as Map<String, dynamic>);
  }
}

class _ProductsApi {
  _ProductsApi(this._c);
  final UellowApi _c;

  Future<UellowPage<UellowProductCard>> list({
    int page = 1, int perPage = 20,
    int? categoryId, String? search, String sort = 'newest',
    int? brandId, int? tagId, double? minPrice, double? maxPrice,
    bool? onSale,
  }) async {
    final res = await _c._get(EP.products, query: {
      'page': page, 'per_page': perPage, 'sort': sort,
      if (categoryId != null) 'category_id': categoryId,
      if (search     != null) 'search': search,
      if (brandId    != null) 'brand_id': brandId,
      if (tagId      != null) 'tag_id': tagId,
      if (minPrice   != null) 'min_price': minPrice,
      if (maxPrice   != null) 'max_price': maxPrice,
      if (onSale == true) 'on_sale': '1',
    });
    return UellowPage.fromJson(
      res,
      (item) => UellowProductCard.fromJson(item),
    );
  }

  Future<UellowProductFull> detail(int productId) async {
    final res = await _c._get('${EP.products}/$productId');
    return UellowProductFull.fromJson(
        res['data']['product'] as Map<String, dynamic>);
  }

  Future<List<UellowProductVariant>> variants(int productId) async {
    final res = await _c._get('${EP.products}/$productId/variants');
    final list = res['data']['variants'] as List;
    return list.map((e) => UellowProductVariant.fromJson(e)).toList();
  }

  Future<UellowReviewsResult> reviews(int productId,
      {int page = 1, int perPage = 20}) async {
    final res = await _c._get('${EP.products}/$productId/reviews',
        query: {'page': page, 'per_page': perPage});
    return UellowReviewsResult.fromJson(res);
  }

  Future<List<UellowProductCard>> related(int productId) async {
    final res = await _c._get('${EP.products}/$productId/related');
    return (res['data'] as List)
        .map((e) => UellowProductCard.fromJson(e))
        .toList();
  }

  Future<List<UellowProductCard>> topSelling() async {
    final res = await _c._get(EP.productsTopSelling);
    return (res['data'] as List)
        .map((e) => UellowProductCard.fromJson(e))
        .toList();
  }

  Future<List<UellowProductCard>> recommended() async {
    final res = await _c._get(EP.productsRecommended);
    return (res['data'] as List)
        .map((e) => UellowProductCard.fromJson(e))
        .toList();
  }

  Future<List<UellowProductCard>> recentlyViewed() async {
    final res = await _c._get(EP.productsRecentlyViewed);
    return (res['data'] as List)
        .map((e) => UellowProductCard.fromJson(e))
        .toList();
  }

  Future<List<UellowProductCard>> bySection(int sectionId) async {
    final res = await _c._get('${EP.products}/section/$sectionId');
    return (res['data'] as List)
        .map((e) => UellowProductCard.fromJson(e))
        .toList();
  }
}

class _CategoriesApi {
  _CategoriesApi(this._c);
  final UellowApi _c;

  Future<List<UellowCategory>> list({int? parentId, bool withChildren = false}) async {
    final res = await _c._get(EP.categories, query: {
      if (parentId != null) 'parent_id': parentId,
      'with_children': withChildren ? 'true' : 'false',
    });
    return (res['data'] as List)
        .map((e) => UellowCategory.fromJson(e))
        .toList();
  }

  Future<List<UellowCategory>> tree() async {
    final res = await _c._get(EP.categoriesTree);
    return (res['data'] as List)
        .map((e) => UellowCategory.fromJson(e))
        .toList();
  }

  Future<UellowCategory> detail(int id) async {
    final res = await _c._get('${EP.categories}/$id');
    return UellowCategory.fromJson(
        res['data']['category'] as Map<String, dynamic>);
  }
}

class _CartApi {
  _CartApi(this._c);
  final UellowApi _c;

  Future<UellowCart> get() async {
    final res = await _c._get(EP.cart);
    return _save(UellowCart.fromJson(res['data']['cart']));
  }

  Future<UellowCart> add({required int productId, int qty = 1}) async {
    final res = await _c._post(EP.cartAdd,
        body: {'product_id': productId, 'qty': qty});
    return _save(UellowCart.fromJson(res['data']['cart']));
  }

  Future<UellowCart> update({required int lineId, required int qty}) async {
    final res = await _c._post(EP.cartUpdate,
        body: {'line_id': lineId, 'qty': qty});
    return _save(UellowCart.fromJson(res['data']['cart']));
  }

  Future<UellowCart> remove(int lineId) async {
    final res = await _c._post(EP.cartRemove, body: {'line_id': lineId});
    return _save(UellowCart.fromJson(res['data']['cart']));
  }

  Future<UellowCart> clear() async {
    final res = await _c._post(EP.cartClear);
    return _save(UellowCart.fromJson(res['data']['cart']));
  }

  Future<UellowCart> applyCoupon(String code) async {
    final res = await _c._post(EP.cartApplyCoupon, body: {'code': code});
    return _save(UellowCart.fromJson(res['data']['cart']));
  }

  Future<UellowCart> removeCoupon() async {
    final res = await _c._post(EP.cartRemoveCoupon);
    return _save(UellowCart.fromJson(res['data']['cart']));
  }

  Future<UellowCart> _save(UellowCart cart) async {
    if (cart.cartToken.isNotEmpty) {
      await _c.tokenStore.writeCartToken(cart.cartToken);
    }
    return cart;
  }
}

class _OrdersApi {
  _OrdersApi(this._c);
  final UellowApi _c;

  Future<UellowPage<UellowOrderSummary>> list({int page = 1, int perPage = 20}) async {
    final res = await _c._get(EP.orders, query: {
      'page': page, 'per_page': perPage,
    }, auth: true);
    return UellowPage.fromJson(
        res, (e) => UellowOrderSummary.fromJson(e));
  }

  Future<UellowOrderDetail> detail(int id) async {
    final res = await _c._get('${EP.orders}/$id', auth: true);
    return UellowOrderDetail.fromJson(
        res['data']['order'] as Map<String, dynamic>);
  }

  Future<List<UellowShippingMethod>> shippingMethods() async {
    final res = await _c._get(EP.shippingMethods);
    return (res['data'] as List)
        .map((e) => UellowShippingMethod.fromJson(e))
        .toList();
  }

  Future<List<UellowPaymentMethod>> paymentMethods() async {
    final res = await _c._get(EP.paymentMethods);
    return (res['data'] as List)
        .map((e) => UellowPaymentMethod.fromJson(e))
        .toList();
  }

  Future<UellowCheckoutSummary> checkoutSummary() async {
    final res = await _c._get(EP.checkoutSummary, auth: true);
    return UellowCheckoutSummary.fromJson(res['data'] as Map<String, dynamic>);
  }

  Future<UellowCheckoutConfirm> checkoutConfirm({
    int? deliveryAddressId,
    int? invoiceAddressId,
    int? carrierId,
    String? paymentMethod,
  }) async {
    final res = await _c._post(EP.checkoutConfirm, auth: true, body: {
      if (deliveryAddressId != null) 'delivery_address_id': deliveryAddressId,
      if (invoiceAddressId  != null) 'invoice_address_id': invoiceAddressId,
      if (carrierId         != null) 'carrier_id': carrierId,
      if (paymentMethod     != null) 'payment_method': paymentMethod,
    });
    return UellowCheckoutConfirm.fromJson(res['data'] as Map<String, dynamic>);
  }
}

class _AddressesApi {
  _AddressesApi(this._c);
  final UellowApi _c;

  Future<List<UellowAddress>> list() async {
    final res = await _c._get(EP.addresses, auth: true);
    return (res['data'] as List)
        .map((e) => UellowAddress.fromJson(e))
        .toList();
  }

  Future<UellowAddress> create(Map<String, dynamic> data) async {
    final res = await _c._post(EP.addressesCreate, auth: true, body: data);
    return UellowAddress.fromJson(
        res['data']['address'] as Map<String, dynamic>);
  }

  Future<UellowAddress> update(int id, Map<String, dynamic> data) async {
    final res = await _c._post('${EP.addresses}/$id/update', auth: true, body: data);
    return UellowAddress.fromJson(
        res['data']['address'] as Map<String, dynamic>);
  }

  Future<bool> delete(int id) async {
    final res = await _c._post('${EP.addresses}/$id/delete', auth: true);
    return res['data']?['deleted'] == true;
  }
}

class _WishlistApi {
  _WishlistApi(this._c);
  final UellowApi _c;

  Future<List<UellowProductCard>> list() async {
    final res = await _c._get(EP.wishlist, auth: true);
    return (res['data'] as List)
        .map((e) => UellowProductCard.fromJson(e))
        .toList();
  }

  Future<bool> add(int productId) async {
    final res = await _c._post(EP.wishlistAdd, auth: true,
        body: {'product_id': productId});
    return res['data']?['added'] == true;
  }

  Future<bool> remove(int productId) async {
    final res = await _c._post(EP.wishlistRemove, auth: true,
        body: {'product_id': productId});
    return res['data']?['removed'] == true;
  }
}

class _SearchApi {
  _SearchApi(this._c);
  final UellowApi _c;

  Future<UellowSearchResult> search(String query,
      {int page = 1, int perPage = 20}) async {
    final res = await _c._get(EP.search, query: {
      'q': query, 'page': page, 'per_page': perPage,
    });
    return UellowSearchResult.fromJson(res);
  }

  Future<List<UellowPopularQuery>> popular() async {
    final res = await _c._get(EP.searchPopular);
    return (res['data'] as List)
        .map((e) => UellowPopularQuery.fromJson(e))
        .toList();
  }
}

class _ReviewsApi {
  _ReviewsApi(this._c);
  final UellowApi _c;

  Future<Map<String, dynamic>> create({
    required int productId, required double rating,
    String? title, String? body,
  }) async {
    final res = await _c._post(EP.reviewsCreate, auth: true, body: {
      'product_id': productId, 'rating': rating,
      if (title != null) 'title': title,
      if (body  != null) 'body': body,
    });
    return res['data'] as Map<String, dynamic>;
  }

  Future<List<UellowMyReview>> mine() async {
    final res = await _c._get(EP.reviewsMine, auth: true);
    return (res['data'] as List)
        .map((e) => UellowMyReview.fromJson(e))
        .toList();
  }
}

class _LoyaltyApi {
  _LoyaltyApi(this._c);
  final UellowApi _c;

  Future<UellowLoyalty> overview() async {
    final res = await _c._get(EP.loyalty, auth: true);
    return UellowLoyalty.fromJson(res['data'] as Map<String, dynamic>);
  }
}

class _WalletApi {
  _WalletApi(this._c);
  final UellowApi _c;

  Future<UellowMoney> balance() async {
    final res = await _c._get(EP.walletBalance, auth: true);
    return UellowMoney.fromJson(res['data']['balance'] as Map<String, dynamic>);
  }

  Future<List<UellowWalletTx>> transactions() async {
    final res = await _c._get(EP.walletTransactions, auth: true);
    return (res['data'] as List)
        .map((e) => UellowWalletTx.fromJson(e))
        .toList();
  }
}

class _NotificationsApi {
  _NotificationsApi(this._c);
  final UellowApi _c;

  Future<List<UellowNotification>> list() async {
    final res = await _c._get(EP.notifications, auth: true);
    return (res['data'] as List)
        .map((e) => UellowNotification.fromJson(e))
        .toList();
  }

  Future<bool> markRead(int id) async {
    final res = await _c._post('${EP.notifications}/$id/read', auth: true);
    return res['data']?['read'] == true;
  }

  Future<void> registerDevice({
    required String deviceId,
    required String pushToken,
    String? platform, String? deviceName, String? osVersion, String? appVersion,
  }) async {
    await _c._post(EP.notificationsRegister, body: {
      'device_id': deviceId,
      'push_token': pushToken,
      if (platform    != null) 'platform': platform,
      if (deviceName  != null) 'device_name': deviceName,
      if (osVersion   != null) 'os_version': osVersion,
      if (appVersion  != null) 'app_version': appVersion,
    });
  }
}

class _BeenaApi {
  _BeenaApi(this._c);
  final UellowApi _c;

  Future<Map<String, dynamic>> config() async {
    final res = await _c._get(EP.beenaConfig);
    return res['data'] as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> chat({
    required String message, List<Map<String, dynamic>>? history,
    int? productId,
  }) async {
    final res = await _c._post(EP.beenaChat, body: {
      'message': message,
      if (history   != null) 'history': history,
      if (productId != null) 'product_id': productId,
    });
    return res['data'] as Map<String, dynamic>;
  }
}

class _SettingsApi {
  _SettingsApi(this._c);
  final UellowApi _c;

  Future<UellowAppSettings> get() async {
    final res = await _c._get(EP.appSettings, query: {'platform': _c._platform});
    return UellowAppSettings.fromJson(res['data'] as Map<String, dynamic>);
  }

  Future<List<UellowCountry>> countries() async {
    final res = await _c._get(EP.appCountries);
    return (res['data'] as List)
        .map((e) => UellowCountry.fromJson(e))
        .toList();
  }

  Future<List<UellowState>> states(int countryId) async {
    final res = await _c._get(EP.appStates, query: {'country_id': countryId});
    return (res['data'] as List)
        .map((e) => UellowState.fromJson(e))
        .toList();
  }

  Future<UellowVersionCheck> versionCheck(String version) async {
    final res = await _c._get(EP.appVersionCheck,
        query: {'version': version, 'platform': _c._platform});
    return UellowVersionCheck.fromJson(res['data'] as Map<String, dynamic>);
  }
}
