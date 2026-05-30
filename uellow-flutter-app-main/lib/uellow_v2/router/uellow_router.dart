// =============================================================================
// Centralized routing for all v2 screens. Plain Navigator + named routes —
// no GoRouter dep needed. Push by name or factory: UellowRouter.go(...).
// =============================================================================
import 'package:flutter/material.dart';

import '../screens/splash_screen.dart';
import '../screens/home_screen.dart';
import '../screens/product_screen.dart';
import '../screens/cart_screen.dart';
import '../screens/checkout_screen.dart';
import '../screens/account_screen.dart';
import '../screens/category_screen.dart';
import '../screens/search_screen.dart';
import '../screens/auth_screen.dart';
import '../screens/order_screen.dart';
import '../screens/wishlist_screen.dart';
import '../screens/notifications_screen.dart';
import '../screens/loyalty_screen.dart';
import '../screens/wallet_screen.dart';
import '../screens/coupons_screen.dart';
import '../screens/brands_screen.dart';
import '../screens/vendor_screen.dart';
import '../screens/flash_screen.dart';
import '../screens/tryon_screen.dart';
import '../screens/beena_screen.dart';

class Routes {
  Routes._();
  static const splash        = '/';
  static const auth          = '/auth';
  static const home          = '/home';
  static const search        = '/search';
  static const category      = '/category';
  static const brands        = '/brands';
  static const flash         = '/flash';
  static const product       = '/product';        // arg: productId (int)
  static const vendor        = '/vendor';         // arg: vendorId (int)
  static const tryOn         = '/tryon';          // arg: productId
  static const cart          = '/cart';
  static const checkout      = '/checkout';
  static const order         = '/order';          // arg: orderId
  static const account       = '/account';
  static const loyalty       = '/loyalty';
  static const wallet        = '/wallet';
  static const coupons       = '/coupons';
  static const wishlist      = '/wishlist';
  static const notifications = '/notifications';
  static const beena         = '/beena';
}

class UellowRouter {
  UellowRouter._();

  /// Routes registered for named navigation. Concrete pages that need
  /// arguments use [generate] below.
  static Map<String, WidgetBuilder> routes = {
    Routes.splash:        (ctx) => const SplashScreen(),
    Routes.auth:          (ctx) => const AuthScreen(),
    Routes.home:          (ctx) => const HomeScreen(),
    Routes.cart:          (ctx) => const CartScreen(),
    Routes.checkout:      (ctx) => const CheckoutScreen(),
    Routes.account:       (ctx) => const AccountScreen(),
    Routes.category:      (ctx) => const CategoryScreen(),
    Routes.search:        (ctx) => const SearchScreen(),
    Routes.wishlist:      (ctx) => const WishlistScreen(),
    Routes.notifications: (ctx) => const NotificationsScreen(),
    Routes.loyalty:       (ctx) => const LoyaltyScreen(),
    Routes.wallet:        (ctx) => const WalletScreen(),
    Routes.coupons:       (ctx) => const CouponsScreen(),
    Routes.brands:        (ctx) => const BrandsScreen(),
    Routes.flash:         (ctx) => const FlashScreen(),
    Routes.beena:         (ctx) => const BeenaScreen(),
  };

  /// Handles dynamic routes that take arguments (e.g. /product with id).
  static Route<dynamic>? generate(RouteSettings settings) {
    switch (settings.name) {
      case Routes.product:
        final id = (settings.arguments as Map?)?['id'] as int? ?? 0;
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => ProductScreen(productId: id),
        );
      case Routes.order:
        final id = (settings.arguments as Map?)?['id'] as int? ?? 0;
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => OrderScreen(orderId: id),
        );
      case Routes.vendor:
        final id = (settings.arguments as Map?)?['id'] as int? ?? 0;
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => VendorScreen(vendorId: id),
        );
      case Routes.tryOn:
        final id = (settings.arguments as Map?)?['id'] as int?;
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => TryOnScreen(productId: id),
        );
    }
    return null;
  }

  static void goVendor(BuildContext context, int vendorId) =>
      Navigator.of(context).pushNamed(Routes.vendor, arguments: {'id': vendorId});

  static void goTryOn(BuildContext context, {int? productId}) =>
      Navigator.of(context).pushNamed(Routes.tryOn, arguments: {'id': productId});

  /// Convenience helpers — strongly-typed nav wrappers.
  static Future<T?> push<T>(BuildContext context, Widget page) =>
      Navigator.of(context).push<T>(MaterialPageRoute(builder: (_) => page));

  static Future<T?> pushNamed<T>(BuildContext context, String name,
          {Object? arguments}) =>
      Navigator.of(context).pushNamed<T>(name, arguments: arguments);

  static void goProduct(BuildContext context, int productId) =>
      Navigator.of(context).pushNamed(Routes.product, arguments: {'id': productId});
}
