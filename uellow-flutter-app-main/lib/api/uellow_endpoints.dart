// Endpoint paths for the v2 API. Centralized so refactors are
// one-line changes and tests/mocks don't have to chase string literals.

class EP {
  EP._();

  // ── Auth
  static const authLogin     = '/api/mobile/v2/auth/login';
  static const authRegister  = '/api/mobile/v2/auth/register';
  static const authOtpReq    = '/api/mobile/v2/auth/otp/request';
  static const authOtpVerify = '/api/mobile/v2/auth/otp/verify';
  static const authForgot    = '/api/mobile/v2/auth/forgot';
  static const authLogout    = '/api/mobile/v2/auth/logout';
  static const authMe        = '/api/mobile/v2/auth/me';

  // ── Profile
  static const profileUpdate         = '/api/mobile/v2/profile/update';
  static const profileChangePassword = '/api/mobile/v2/profile/change-password';
  static const profileDelete         = '/api/mobile/v2/profile/delete';

  // ── Home
  static const home = '/api/mobile/v2/home';

  // ── Products
  static const products             = '/api/mobile/v2/products';
  static const productsTopSelling   = '/api/mobile/v2/products/top-selling';
  static const productsRecommended  = '/api/mobile/v2/products/recommended';
  static const productsRecentlyViewed = '/api/mobile/v2/products/recently-viewed';

  // ── Categories
  static const categories      = '/api/mobile/v2/categories';
  static const categoriesTree  = '/api/mobile/v2/categories/tree';

  // ── Cart
  static const cart              = '/api/mobile/v2/cart';
  static const cartAdd           = '/api/mobile/v2/cart/add';
  static const cartUpdate        = '/api/mobile/v2/cart/update';
  static const cartRemove        = '/api/mobile/v2/cart/remove';
  static const cartClear         = '/api/mobile/v2/cart/clear';
  static const cartApplyCoupon   = '/api/mobile/v2/cart/apply-coupon';
  static const cartRemoveCoupon  = '/api/mobile/v2/cart/remove-coupon';

  // ── Orders
  static const orders            = '/api/mobile/v2/orders';
  static const shippingMethods   = '/api/mobile/v2/orders/shipping-methods';
  static const paymentMethods    = '/api/mobile/v2/orders/payment-methods';
  static const checkoutSummary   = '/api/mobile/v2/orders/checkout/summary';
  static const checkoutConfirm   = '/api/mobile/v2/orders/checkout/confirm';

  // ── Addresses
  static const addresses       = '/api/mobile/v2/addresses';
  static const addressesCreate = '/api/mobile/v2/addresses/create';

  // ── Wishlist
  static const wishlist       = '/api/mobile/v2/wishlist';
  static const wishlistAdd    = '/api/mobile/v2/wishlist/add';
  static const wishlistRemove = '/api/mobile/v2/wishlist/remove';

  // ── Search
  static const search        = '/api/mobile/v2/search';
  static const searchPopular = '/api/mobile/v2/search/popular';

  // ── Reviews
  static const reviewsCreate = '/api/mobile/v2/reviews/create';
  static const reviewsMine   = '/api/mobile/v2/reviews/mine';

  // ── Loyalty / Wallet
  static const loyalty            = '/api/mobile/v2/loyalty';
  static const walletBalance      = '/api/mobile/v2/wallet/balance';
  static const walletTransactions = '/api/mobile/v2/wallet/transactions';

  // ── Notifications
  static const notifications         = '/api/mobile/v2/notifications';
  static const notificationsRegister = '/api/mobile/v2/notifications/register-device';

  // ── Beena AI
  static const beenaConfig = '/api/mobile/v2/beena/config';
  static const beenaChat   = '/api/mobile/v2/beena/chat';

  // ── App settings
  static const appSettings       = '/api/mobile/v2/app/settings';
  static const appLanguages      = '/api/mobile/v2/app/languages';
  static const appCountries      = '/api/mobile/v2/app/countries';
  static const appStates         = '/api/mobile/v2/app/states';
  static const appVersionCheck   = '/api/mobile/v2/app/version-check';

  // ── Multi-country / multi-website routing
  static String appGeo()           => '/api/mobile/v2/app/geo';
  static String appCountriesList() => '/api/mobile/v2/app/countries-list';
  static String appSetCountry()    => '/api/mobile/v2/app/set-country';

  // ── Flash sale
  static String flashSales()       => '/api/mobile/v2/flash-sales';

  // ── Vendors
  static String vendors()          => '/api/mobile/v2/vendors';
  static String vendor(int id)     => '/api/mobile/v2/vendors/$id';
  static String vendorProducts(int id) => '/api/mobile/v2/vendors/$id/products';

  // ── Search v2
  static String searchBarcode()    => '/api/mobile/v2/search/barcode';
  static String searchImage()      => '/api/mobile/v2/search/image';

  // ── Account aggregate
  static String accountOverview()  => '/api/mobile/v2/account/overview';

  // ── Shipping
  static String shippingZones()    => '/api/mobile/v2/shipping/zones';
  static String shippingCompanies() => '/api/mobile/v2/shipping/companies';
  static String shippingTrack(int orderId) => '/api/mobile/v2/shipping/track/$orderId';
  static String shippingPrefs()    => '/api/mobile/v2/shipping/preferences';
  static String shippingPrefsSave() => '/api/mobile/v2/shipping/preferences/save';

  // ── Product extra
  static String productReviewers(int id) => '/api/mobile/v2/products/$id/reviewers';
}
