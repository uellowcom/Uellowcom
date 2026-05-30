# Uellow API v2 — Flutter Integration Guide

A drop-in replacement for the legacy `base_woo_api.dart` + scattered
`*_api.dart` files in `lib/services/`. One client, one error path,
typed models, bilingual text built-in.

## Files in this package

```
lib/api/
├── uellow_api.dart           ← the client (singleton + per-resource APIs)
├── uellow_endpoints.dart     ← endpoint path constants
├── uellow_models.dart        ← typed response models
├── uellow_token_store.dart   ← secure bearer + cart token storage
└── INTEGRATION.md            ← this file
```

## Quick start (3 steps)

### 1. Initialize in `main.dart`

```dart
import 'package:nyoba/api/uellow_api.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await UellowApi.init();                        // ← here
  UellowApi.instance.setAppMeta(
    appVersion: '4.1.11',
    platform: Platform.isIOS ? 'ios' : 'android',
  );
  runApp(const MyApp());
}
```

### 2. Set the language whenever locale changes

```dart
UellowApi.instance.setLang(Localizations.localeOf(context).languageCode);
```

### 3. Use it from anywhere

```dart
final api = UellowApi.instance;

// Home screen — one call returns everything
final home = await api.home.get();
for (final s in home.sliders) {
  final title = s.title.current(api.lang);
  final imgUrl = s.imageUrl;
}

// Products list with pagination
final page = await api.products.list(page: 1, perPage: 20, sort: 'newest');
for (final p in page.items) {
  print(p.name.current(api.lang));
  print(p.price.format());
}

// Add to cart (works for guests AND auth — cart token auto-managed)
final cart = await api.cart.add(productId: 1786, qty: 2);

// Login
try {
  final res = await api.auth.login('user@x.com', 'password');
  print('Welcome ${res.user.name}');
} on UellowApiException catch (e) {
  if (e.code == 'INVALID_CREDENTIALS') showSnackBar('Wrong credentials');
}
```

## Migration from legacy services

| Old call                                              | New call                                      |
|-------------------------------------------------------|-----------------------------------------------|
| `LoginApi().login(email, password)`                   | `api.auth.login(email, password)`             |
| `RegisterApi().register(...)`                         | `api.auth.register(...)`                      |
| `ProductApi().getProducts(...)`                       | `api.products.list(...)`                      |
| `ProductApi().getProduct(id)`                         | `api.products.detail(id)`                     |
| `CategoriesApi().getCategories()`                     | `api.categories.tree()`                       |
| `HomeApi().getHomeData()`                             | `api.home.get()`                              |
| `OrderApi().listOrders()`                             | `api.orders.list()`                           |
| `OrderApi().placeOrder(...)`                          | `api.orders.checkoutConfirm(...)`             |
| `WishlistApi().listWishlist()`                        | `api.wishlist.list()`                         |
| `WalletApi().getBalance()`                            | `api.wallet.balance()`                        |
| `CouponApi().applyCoupon(code)`                       | `api.cart.applyCoupon(code)`                  |
| `ReviewApi().postReview(...)`                         | `api.reviews.create(...)`                     |
| `UserApi().getUser()`                                 | `api.auth.me()`                               |
| `UserApi().updateUser(...)`                           | `api.profile.update(...)`                     |
| `NotificationApi().getNotifications()`                | `api.notifications.list()`                    |

### What changes in the call sites

**Before:**
```dart
var response = await newUrl.newCustomBaseAPI.postAsync('place-order', data, isCustom: true);
if (response['status_code'] == 200) {
  var orderId = response['data']['order_id'];
} else {
  print(response['message']);
}
```

**After:**
```dart
try {
  final result = await api.orders.checkoutConfirm(
    deliveryAddressId: 42, carrierId: 1, paymentMethod: 'cod',
  );
  print('Order #${result.orderName}');
  if (result.paymentRequired) {
    openWebView(result.paymentUrl!);
  }
} on UellowApiException catch (e) {
  showError(e.message);                                // already localized
}
```

## Provider integration

Wrap the singleton in a ChangeNotifier when you want the UI to react
to auth changes:

```dart
class AuthState extends ChangeNotifier {
  AuthState() {
    UellowApi.instance.onAuthChanged.listen((user) {
      _user = user;
      notifyListeners();
    });
    _bootstrap();
  }
  UellowUser? _user;
  UellowUser? get user => _user;
  bool get isLoggedIn => _user != null;

  Future<void> _bootstrap() async {
    final token = await UellowApi.instance.tokenStore.readToken();
    if (token != null && token.isNotEmpty) {
      try {
        _user = await UellowApi.instance.auth.me();
        notifyListeners();
      } catch (_) {/* token expired — already cleared */}
    }
  }

  Future<void> login(String email, String password) async {
    final res = await UellowApi.instance.auth.login(email, password);
    _user = res.user;
    notifyListeners();
  }

  Future<void> logout() async {
    await UellowApi.instance.auth.logout();
    // onAuthChanged stream fires → notifyListeners called
  }
}

// In main.dart:
//   ChangeNotifierProvider(create: (_) => AuthState(), child: MyApp())
```

## Cart token (guest flow)

The client transparently handles guest carts. On first add-to-cart,
the server issues `cart_token` which the client stores. Subsequent
requests send `X-Cart-Token: <value>` automatically. When the user
logs in, the server merges the guest cart into the partner's cart.

No code needed in the app — just call `api.cart.add()`.

## Bilingual text

Every translatable field uses `UellowText`:

```dart
Text(product.name.current(api.lang))      // picks 'ar' or 'en'
Text(product.name.en)                      // English explicitly
Text(product.name.ar)                      // Arabic explicitly
```

## Error handling

Every method throws `UellowApiException` on failure. Code is machine-friendly:

```dart
try {
  await api.cart.add(productId: 1, qty: 5);
} on UellowApiException catch (e) {
  if (e.code == 'AUTH_REQUIRED') Navigator.pushNamed(context, '/login');
  else if (e.isNetwork) showSnackBar('Check your internet');
  else showSnackBar(e.message);
}
```

## Switching servers

For staging/local, run with:

```
flutter run --dart-define=UELLOW_API_BASE=https://staging.uellow.com
flutter run --dart-define=UELLOW_API_BASE=http://192.168.1.10:8069
```

The default is `https://www.uellow.com`.

## Push notifications

After receiving the FCM token in Flutter:

```dart
await api.notifications.registerDevice(
  deviceId:  await DeviceInfoPlus.androidId,
  pushToken: await FirebaseMessaging.instance.getToken(),
  platform:  'android',
  deviceName: await DeviceInfoPlus.model,
  osVersion:  Platform.operatingSystemVersion,
  appVersion: '4.1.11',
);
```

Works for guests too — the token is attached to the device session.
At login, the server can match the device's existing FCM token to
the user automatically.

## Files you can delete after migration

Once all call sites are switched over:

```
lib/services/base_woo_api.dart
lib/services/banner_api.dart
lib/services/blog_api.dart
lib/services/categories_api.dart
lib/services/coupon_api.dart
lib/services/flash_sale_api.dart
lib/services/general_settings_api.dart
lib/services/home_api.dart
lib/services/login_api.dart
lib/services/notification_api.dart
lib/services/notify_api.dart
lib/services/order_api.dart
lib/services/product_api.dart
lib/services/register_api.dart
lib/services/review_api.dart
lib/services/service.dart
lib/services/user_api.dart
lib/services/wallet_api.dart
lib/services/wishlist_api.dart
lib/constant/constants.dart        ← contains hardcoded WC consumer secrets
lib/constant/global_url.dart       ← WC-style endpoint constants
```

**Keep**: `lib/services/session.dart` if it holds non-API session state
(theme, locale, etc.).

## Testing

```dart
import 'package:test/test.dart';
import 'package:nyoba/api/uellow_api.dart';
import 'package:nyoba/api/uellow_token_store.dart';
import 'package:http/testing.dart';

void main() {
  test('login stores token', () async {
    final mock = MockClient((req) async => http.Response('''
      {"success":true,"data":{"token":"abc","user":{"id":1,"name":"Ali",
       "email":"a@x.com","phone":"","avatar":"","is_company":false,
       "lang":"en_US","wallet_balance":0,"loyalty_points":0,
       "addresses_count":0}}}
    ''', 200, headers: {'content-type': 'application/json'}));
    await UellowApi.init(httpClient: mock);
    final res = await UellowApi.instance.auth.login('a@x.com', 'x');
    expect(res.token, 'abc');
    expect(await UellowApi.instance.tokenStore.readToken(), 'abc');
  });
}
```
