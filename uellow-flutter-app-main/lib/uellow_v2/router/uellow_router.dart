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
    Routes.splash:   (ctx) => const SplashScreen(),
    Routes.home:     (ctx) => const HomeScreen(),
    Routes.cart:     (ctx) => const CartScreen(),
    Routes.checkout: (ctx) => const CheckoutScreen(),
    Routes.account:  (ctx) => const AccountScreen(),
    Routes.category: (ctx) => const CategoryScreen(),
    Routes.search:   (ctx) => const SearchScreen(),
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
    }
    return null;
  }

  /// Convenience helpers — strongly-typed nav wrappers.
  static Future<T?> push<T>(BuildContext context, Widget page) =>
      Navigator.of(context).push<T>(MaterialPageRoute(builder: (_) => page));

  static Future<T?> pushNamed<T>(BuildContext context, String name,
          {Object? arguments}) =>
      Navigator.of(context).pushNamed<T>(name, arguments: arguments);

  static void goProduct(BuildContext context, int productId) =>
      Navigator.of(context).pushNamed(Routes.product, arguments: {'id': productId});
}
