import 'dart:convert';

import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:intl/intl.dart';
import 'package:nyoba/models/additional_menus_model.dart';
import 'package:nyoba/models/banner_mini_model.dart';
import 'package:nyoba/models/banner_model.dart';
import 'package:nyoba/models/billing_address_model.dart';
import 'package:nyoba/models/categories_model.dart';
import 'package:nyoba/models/discount_model.dart';
import 'package:nyoba/models/general_settings_model.dart';
import 'package:nyoba/models/home_model.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/models/shipping_country_model.dart';
import 'package:nyoba/provider/category_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/services/home_api.dart';
import 'package:nyoba/services/product_api.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:provider/provider.dart';

import '../app_localizations.dart';
import '../models/customize_banner_model.dart';

class HomeProvider with ChangeNotifier {
  bool isReload = false;
  bool loading = false;
  bool isWalletActive = false;
  bool isBannerPopChanged = false;
  bool isGiftActive = false;
  bool smartCoupon = false;
  String giftBoxImage = 'images/lobby/gift-coupon.gif';

  Color? flashSaleBGColorPrimary;
  Color? flashSaleBGColorSecondary;
  String? flashSaleBgImage = '';
  Color? flashSaleText;

  bool? isCheckoutNative = false;
  bool guestCheckoutActive = false;

  /*List Additional Menus*/
  List<AdditionalMenusModel> additionalMenus = [];

  /*List billing address*/
  List<BillingAddress> billingAddress = [];

  /*List Main Slider Banner Model*/
  List<BannerModel> banners = [];

  /*List Banner Mini Product Model*/
  List<BannerMiniModel> bannerSpecial = [];
  List<BannerMiniModel> bannerLove = [];

  /*Banner PopUp*/
  List<BannerMiniModel> bannerPopUp = [];

  // Banner Categories
  List<BannerMiniModel> bannerCategories = [];

  /*Categories Home*/
  List<ProductCategoryModel> newCategories = [];

  /*List Home Mini Categories Model*/
  List<CategoriesModel> categories = [];

  /*List Intro Page Model*/
  List<GeneralSettingsModel> intro = [];

  /*General Settings Model*/
  GeneralSettingsModel splashscreen = new GeneralSettingsModel();
  GeneralSettingsModel logo = new GeneralSettingsModel();
  GeneralSettingsModel wa = new GeneralSettingsModel();
  GeneralSettingsModel sms = new GeneralSettingsModel();
  GeneralSettingsModel phone = new GeneralSettingsModel();
  GeneralSettingsModel about = new GeneralSettingsModel();
  GeneralSettingsModel currency = new GeneralSettingsModel();
  GeneralSettingsModel formatCurrency = new GeneralSettingsModel();
  GeneralSettingsModel privacy = new GeneralSettingsModel();
  GeneralSettingsModel terms = new GeneralSettingsModel();
  GeneralSettingsModel image404 = new GeneralSettingsModel();
  GeneralSettingsModel imageThanksOrder = new GeneralSettingsModel();
  GeneralSettingsModel imageNoTransaction = new GeneralSettingsModel();
  GeneralSettingsModel imageSearchEmpty = new GeneralSettingsModel();
  GeneralSettingsModel imageNoLogin = new GeneralSettingsModel();
  GeneralSettingsModel searchBarText = new GeneralSettingsModel();
  GeneralSettingsModel sosmedLink = new GeneralSettingsModel();

  bool? isBarcodeActive = false;

  /*Flash Sales Model*/
  List<FlashSaleHomeModel> flashSales = [];

  /*Extend Product Model*/
  List<ProductExtendHomeModel> specialProducts = [];
  List<ProductExtendHomeModel> bestProducts = [];
  List<ProductExtendHomeModel> recommendationProducts = [];
  List<ProductModel> tempProducts = [];

  /*Intro Page Status*/
  String? introStatus;

  /*App Color*/
  List<GeneralSettingsModel> appColors = [];

  bool loadingMore = false;

  bool? isLoadHomeSuccess = true;

  PackageInfo? packageInfo;

  Discount? discount;
  List<dynamic> a2wCountries = [];
  String? selectedCountries;
  String? selectedCountriesName;

  bool isPhotoReviewActive = false;
  int? photoMaxFiles = 2;
  int? photoMaxSize = 1000;

  List<CustomizeBannerModel> customizeBanner = [];
  Map<String, List<Map>> customizeBannerMiniCategories = {};
  Map<String, List<Map>> customizeBannerFlashSale = {};
  Map<String, List<Map>> customizeBannerBannerSpecial = {};
  Map<String, List<Map>> customizeBannerBannerLove = {};
  Map<String, List<Map>> customizeBannerProductSpecial = {};
  Map<String, List<Map>> customizeBannerProductBest = {};
  Map<String, List<Map>> customizeBannerProductRecomendation = {};
  Map<String, List<Map>> customizeBannerNewProduct = {};
  Map<String, List<Map>> customizeBannerRecentlyView = {};

  Future<void> fetchHomeData(context) async {
    await fetchProductCategories(context);
  }

  Future<void> fetchProductCategories(context) async {
    final categories = Provider.of<CategoryProvider>(context, listen: false);
    if (categories.productCategories.isEmpty) {
      Future.wait([
        categories.fetchProductCategories(context),
        fetchNewProducts(context)
      ]);
    }
  }

  Future<void> fetchNewProducts(context) async {
    final product = Provider.of<ProductProvider>(context, listen: false);
    await product.fetchNewProducts('', page: 1, context: context);
  }

  Future<bool?> fetchHome(context) async {
    // try {
    loading = true;
    await HomeAPI().homeDataApi(context).then((data) {
      printLog("${data.statusCode}", name: "STATUS CODE");
      // if (data.statusCode == 304) {
      //   final responseJson = json.decode(Session.data.getString('homeAPI')!);

      //   /*Add Data Main Slider*/
      //   banners.clear();
      //   for (Map item in responseJson['main_slider']) {
      //     banners.add(BannerModel.fromJson(item));
      //   }
      //   banners = new List.from(banners.reversed);
      //   /*End*/

      //   /*Add Data Mini Categories Home*/
      //   categories.clear();
      //   for (Map item in responseJson['mini_categories']) {
      //     categories.add(CategoriesModel.fromJson(item));
      //   }
      //   categories = new List.from(categories.reversed);
      //   // categories.add(new CategoriesModel(
      //   //     image: 'images/lobby/viewMore.png',
      //   //     categories: null,
      //   //     id: "view_more",
      //   //     titleCategories:
      //   //         AppLocalizations.of(context)!.translate('view_more')));
      //   /*End*/

      //   /*Add Data Flash Sales Home*/
      //   for (Map item in responseJson['products_flash_sale']) {
      //     flashSales.add(FlashSaleHomeModel.fromJson(item));
      //   }
      //   /*End*/

      //   /*Add Data Mini Banner Home*/
      //   bannerSpecial.clear();
      //   bannerLove.clear();
      //   for (Map item in responseJson['mini_banner']) {
      //     if (item['type'] == 'Special Promo') {
      //       bannerSpecial.add(BannerMiniModel.fromJson(item));
      //     } else if (item['type'] == 'Love These Items') {
      //       bannerLove.add(BannerMiniModel.fromJson(item));
      //     }
      //   }
      //   /*End*/

      //   /*Add Data Special Products*/
      //   specialProducts.clear();
      //   for (Map item in responseJson['products_special']) {
      //     specialProducts.add(ProductExtendHomeModel.fromJson(item));
      //   }
      //   /*End*/

      //   /*Add Data Best Products*/
      //   bestProducts.clear();
      //   for (Map item in responseJson['products_our_best_seller']) {
      //     bestProducts.add(ProductExtendHomeModel.fromJson(item));
      //   }
      //   /*End*/

      //   /*Add Data Banner PopUp*/
      //   if (responseJson['popup_promo'] != null) {
      //     bannerPopUp.clear();
      //     isBannerPopChanged = false;
      //     for (Map item in responseJson['popup_promo']) {
      //       bannerPopUp.add(BannerMiniModel.fromJson(item));
      //     }
      //     final DateTime now = DateTime.now();
      //     final DateFormat formatter = DateFormat('yyyy-MM-dd');
      //     final String formatted = formatter.format(now);
      //     if (Session.data.containsKey('image_popup_date')) {
      //       if (formatted != Session.data.getString('image_popup_date')) {
      //         isBannerPopChanged = true;
      //       }
      //     } else {
      //       isBannerPopChanged = true;
      //     }
      //     Session.data.setString('image_popup_date', formatted);
      //   }
      //   /*End*/

      //   /*Add Data Categories*/
      //   if (responseJson['categories'] != null) {
      //     newCategories.clear();
      //     for (Map item in responseJson['categories']) {
      //       newCategories.add(ProductCategoryModel.fromJson(item));
      //     }
      //   }
      //   /*End*/

      //   /*Add Data Recommendation Products*/
      //   recommendationProducts.clear();
      //   for (Map item in responseJson['products_recomendation']) {
      //     recommendationProducts.add(ProductExtendHomeModel.fromJson(item));
      //   }
      //   /*End*/

      //   /*Add Data General Settings*/
      //   for (Map item in responseJson['general_settings']['empty_image']) {
      //     if (item['title'] == '404_images') {
      //       image404 = GeneralSettingsModel.fromJson(item);
      //     } else if (item['title'] == 'thanks_order') {
      //       imageThanksOrder = GeneralSettingsModel.fromJson(item);
      //     } else if (item['title'] == 'no_transaksi' ||
      //         item['title'] == 'empty_transaksi') {
      //       imageNoTransaction = GeneralSettingsModel.fromJson(item);
      //     } else if (item['title'] == 'search_empty') {
      //       imageSearchEmpty = GeneralSettingsModel.fromJson(item);
      //     } else if (item['title'] == 'login_required') {
      //       imageNoLogin = GeneralSettingsModel.fromJson(item);
      //     }
      //   }

      //   printLog(imageNoTransaction.toString());

      //   logo = GeneralSettingsModel.fromJson(
      //       responseJson['general_settings']['logo']);
      //   wa = GeneralSettingsModel.fromJson(
      //       responseJson['general_settings']['wa']);
      //   sms = GeneralSettingsModel.fromJson(
      //       responseJson['general_settings']['sms']);
      //   phone = GeneralSettingsModel.fromJson(
      //       responseJson['general_settings']['phone']);
      //   about = GeneralSettingsModel.fromJson(
      //       responseJson['general_settings']['about']);
      //   currency = GeneralSettingsModel.fromJson(
      //       responseJson['general_settings']['currency']);
      //   formatCurrency = GeneralSettingsModel.fromJson(
      //       responseJson['general_settings']['format_currency']);
      //   privacy = GeneralSettingsModel.fromJson(
      //       responseJson['general_settings']['privacy_policy']);
      //   terms = GeneralSettingsModel.fromJson(
      //       responseJson['general_settings']['term_condition']);
      //   if (responseJson['general_settings']['searchbar_text'] != null) {
      //     searchBarText = GeneralSettingsModel.fromJson(
      //         responseJson['general_settings']['searchbar_text']);
      //   }
      //   if (responseJson['general_settings']['photoreviews'] != null) {
      //     isPhotoReviewActive =
      //         responseJson['general_settings']['photoreviews']['status'];
      //     photoMaxFiles =
      //         responseJson['general_settings']['photoreviews']['maxfiles'];
      //     photoMaxSize =
      //         responseJson['general_settings']['photoreviews']['maxsize'];
      //   }
      //   if (responseJson['general_settings']['sosmed_link'] != null) {
      //     sosmedLink = GeneralSettingsModel.fromJson(
      //         responseJson['general_settings']['sosmed_link']);
      //   }
      //   if (responseJson['general_settings']['terawallet'] != null) {
      //     isWalletActive = responseJson['general_settings']['terawallet'];
      //   }
      //   if (responseJson['general_settings']['barcode_active'] != null) {
      //     isBarcodeActive =
      //         responseJson['general_settings']['barcode_active'];
      //   }
      //   if (responseJson['general_settings']['gift_box_v2'] != null) {
      //     if (responseJson['general_settings']['gift_box_v2']['status'] !=
      //         null) {
      //       isGiftActive =
      //           responseJson['general_settings']['gift_box_v2']['status'];
      //     }
      //     if (responseJson['general_settings']['gift_box_v2']['image'] !=
      //         null) {
      //       giftBoxImage =
      //           responseJson['general_settings']['gift_box_v2']['image'];
      //     }
      //   }
      //   if (responseJson['general_settings']['checkout_native'] != null) {
      //     isCheckoutNative =
      //         responseJson['general_settings']['checkout_native'];
      //   }

      //   if (responseJson['general_settings']['guest_checkout'] != null) {
      //     guestCheckoutActive =
      //         responseJson['general_settings']['guest_checkout'] == 'disable'
      //             ? false
      //             : true;
      //   }

      //   if (responseJson['app_color'] != []) {
      //     for (var i in responseJson['app_color']) {
      //       if (i['title'] == 'flash_bg_primary') {
      //         flashSaleBGColorPrimary = HexColor(i['description']);
      //       } else if (i['title'] == 'flash_bg_secondary') {
      //         flashSaleBGColorSecondary = HexColor(i['description']);
      //       } else if (i['title'] == 'flash_text_color') {
      //         flashSaleText = HexColor(i['description']);
      //       }
      //     }
      //   }

      //   billingAddress.clear();
      //   if (responseJson['general_settings']['additional_billing_address'] !=
      //       null) {
      //     printLog(
      //         "MASUK 1: ${json.encode(responseJson['general_settings']['additional_billing_address'])}");
      //     for (Map item in responseJson['general_settings']
      //         ['additional_billing_address']) {
      //       billingAddress.add(BillingAddress.fromJson(item));
      //     }
      //     printLog("MASUK : ${json.encode(billingAddress)}");
      //   }
      //   /*End*/

      //   if (responseJson['additional_menus'] != null) {
      //     additionalMenus = [];
      //     printLog("masuk");
      //     responseJson['additional_menus'].forEach((v) {
      //       additionalMenus.add(AdditionalMenusModel.fromJson(v));
      //     });
      //   }

      //   if (responseJson['customize_banner'] != null) {
      //     customizeBanner.clear();
      //     responseJson['customize_banner'].forEach((value) {
      //       customizeBanner.add(CustomizeBannerModel.fromJson(value));
      //     });
      //   }

      //   if (customizeBanner.isNotEmpty || customizeBanner != []) {
      //     customizeBannerMiniCategories.clear();
      //     customizeBannerFlashSale.clear();
      //     customizeBannerBannerSpecial.clear();
      //     customizeBannerBannerLove.clear();
      //     customizeBannerBannerSpecial.clear();
      //     customizeBannerProductBest.clear();
      //     customizeBannerProductRecomendation.clear();
      //     customizeBannerNewProduct.clear();
      //     customizeBannerRecentlyView.clear();

      //     for (var banner in customizeBanner) {
      //       if (banner.sectionType == 'mini_categories') {
      //         customizeBannerMiniCategories['type'] = true;
      //         if (banner.sectionPosition == 'after') {
      //           customizeBannerMiniCategories['after'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         } else if (banner.sectionPosition == 'before') {
      //           customizeBannerMiniCategories['before'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         }
      //       } else if (banner.sectionType == 'flash_sale') {
      //         customizeBannerFlashSale['type'] = true;
      //         if (banner.sectionPosition == 'after') {
      //           customizeBannerFlashSale['after'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         } else if (banner.sectionPosition == 'before') {
      //           customizeBannerFlashSale['before'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         }
      //       } else if (banner.sectionType == 'addon_banner_special') {
      //         customizeBannerBannerSpecial['type'] = true;
      //         if (banner.sectionPosition == 'after') {
      //           customizeBannerBannerSpecial['after'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         } else if (banner.sectionPosition == 'before') {
      //           customizeBannerBannerSpecial['before'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         }
      //       } else if (banner.sectionType == 'addon_banner_love') {
      //         customizeBannerBannerLove['type'] = true;
      //         if (banner.sectionPosition == 'after') {
      //           customizeBannerBannerLove['after'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         } else if (banner.sectionPosition == 'before') {
      //           customizeBannerBannerLove['before'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         }
      //       } else if (banner.sectionType == 'addon_product_special') {
      //         customizeBannerProductSpecial['type'] = true;
      //         if (banner.sectionPosition == 'after') {
      //           customizeBannerProductSpecial['after'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         } else if (banner.sectionPosition == 'before') {
      //           customizeBannerProductSpecial['before'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         }
      //       } else if (banner.sectionType == 'addon_product_best') {
      //         customizeBannerProductBest['type'] = true;
      //         if (banner.sectionPosition == 'after') {
      //           customizeBannerProductBest['after'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         } else if (banner.sectionPosition == 'before') {
      //           customizeBannerProductBest['before'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         }
      //       } else if (banner.sectionType == 'addon_product_recomendation') {
      //         customizeBannerProductRecomendation['type'] = true;
      //         if (banner.sectionPosition == 'after') {
      //           customizeBannerProductRecomendation['after'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         } else if (banner.sectionPosition == 'before') {
      //           customizeBannerProductRecomendation['before'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         }
      //       } else if (banner.sectionType == 'new_product') {
      //         customizeBannerNewProduct['type'] = true;
      //         if (banner.sectionPosition == 'after') {
      //           customizeBannerNewProduct['after'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         } else if (banner.sectionPosition == 'before') {
      //           customizeBannerNewProduct['before'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         }
      //       } else if (banner.sectionType == 'recently_view') {
      //         customizeBannerRecentlyView['type'] = true;
      //         if (banner.sectionPosition == 'after') {
      //           customizeBannerRecentlyView['after'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         } else if (banner.sectionPosition == 'before') {
      //           customizeBannerRecentlyView['before'] = {
      //             'image': banner.image,
      //             'redirectType': banner.redirectType,
      //             'redirectTo': banner.redirectTo
      //           };
      //         }
      //       }
      //     }
      //   }

      //   /*Add Data Intro Page & Splash Screen*/
      //   splashscreen =
      //       GeneralSettingsModel.fromJson(responseJson['splashscreen']);
      //   intro.clear();
      //   for (Map item in responseJson['intro']) {
      //     intro.add(GeneralSettingsModel.fromJson(item));
      //   }
      //   intro = new List.from(intro.reversed);

      //   introStatus = responseJson['intro_page_status'];
      //   /*End*/

      //   /*Set Data App Color*/
      //   if (responseJson['app_color'] != null) {
      //     appColors.clear();
      //     for (Map item in responseJson['app_color']) {
      //       appColors.add(GeneralSettingsModel.fromJson(item));
      //     }
      //   }
      //   /*End*/

      //   a2wCountries.clear();
      //   if (responseJson['general_settings']['ali2woo_contry'] != null &&
      //       responseJson['general_settings']['ali2woo_contry'] != '') {
      //     responseJson['general_settings']['ali2woo_contry']
      //         .forEach((k, v) => a2wCountries.add(ShippingCountry(k, v)));
      //   }

      //   print("Completed");
      //   loading = false;
      //   notifyListeners();
      // } else
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);
        printLog(json.encode(responseJson), name: "RESPONSE HOME");
        Session.data.setString('homeAPI', json.encode(responseJson));
        // final headerJson = data.headers;
        // Session.data.setString("home-revo-etag", headerJson['revo-etag']!);
        printLog(json.encode(data.headers), name: "HEADERS");
        /*Add Data Main Slider*/
        banners.clear();
        for (Map item in responseJson['main_slider']) {
          banners.add(BannerModel.fromJson(item));
        }
        banners = new List.from(banners.reversed);
        /*End*/

        /*Add Data Mini Categories Home*/
        categories.clear();
        for (Map item in responseJson['mini_categories']) {
          categories.add(CategoriesModel.fromJson(item));
        }
        categories = new List.from(categories.reversed);
        // categories.add(new CategoriesModel(
        //     image: 'images/lobby/viewMore.png',
        //     categories: null,
        //     id: "view_more",
        //     titleCategories:
        //         AppLocalizations.of(context)!.translate('view_more')));
        /*End*/

        /*Add Data Flash Sales Home*/
        for (Map item in responseJson['products_flash_sale']) {
          flashSales.add(FlashSaleHomeModel.fromJson(item));
        }
        /*End*/

        /*Add Data Mini Banner Home*/
        bannerSpecial.clear();
        bannerLove.clear();
        for (Map item in responseJson['mini_banner']) {
          if (item['type'] == 'Special Promo') {
            bannerSpecial.add(BannerMiniModel.fromJson(item));
          } else if (item['type'] == 'Love These Items') {
            bannerLove.add(BannerMiniModel.fromJson(item));
          }
        }
        /*End*/

        bannerCategories.clear();
        for (Map item in responseJson['banner_categories']) {
          bannerCategories.add(BannerMiniModel.fromJson(item));
        }
        /*Add Data Special Products*/
        specialProducts.clear();
        for (Map item in responseJson['products_special']) {
          specialProducts.add(ProductExtendHomeModel.fromJson(item));
        }
        /*End*/

        /*Add Data Best Products*/
        bestProducts.clear();
        for (Map item in responseJson['products_our_best_seller']) {
          bestProducts.add(ProductExtendHomeModel.fromJson(item));
        }
        /*End*/

        /*Add Data Banner PopUp*/
        if (responseJson['popup_promo'] != null) {
          bannerPopUp.clear();
          isBannerPopChanged = false;
          for (Map item in responseJson['popup_promo']) {
            bannerPopUp.add(BannerMiniModel.fromJson(item));
          }
          final DateTime now = DateTime.now();
          final DateFormat formatter = DateFormat('yyyy-MM-dd');
          final String formatted = formatter.format(now);
          if (Session.data.containsKey('image_popup_date')) {
            if (formatted != Session.data.getString('image_popup_date')) {
              isBannerPopChanged = true;
            }
          } else {
            isBannerPopChanged = true;
          }
          Session.data.setString('image_popup_date', formatted);
        }
        /*End*/

        /*Add Data Categories*/
        if (responseJson['categories'] != null) {
          newCategories.clear();
          for (Map item in responseJson['categories']) {
            newCategories.add(ProductCategoryModel.fromJson(item));
          }
        }
        /*End*/

        /*Add Data Recommendation Products*/
        recommendationProducts.clear();
        for (Map item in responseJson['products_recomendation']) {
          recommendationProducts.add(ProductExtendHomeModel.fromJson(item));
        }
        /*End*/

        // if (responseJson['flash_sale_bg_image'] != '') {
        //   flashSaleBgImage = responseJson['flash_sale_bg_image'];
        // }

        /*Add Data General Settings*/
        for (Map item in responseJson['general_settings']['empty_image']) {
          if (item['title'] == '404_images') {
            image404 = GeneralSettingsModel.fromJson(item);
          } else if (item['title'] == 'thanks_order') {
            imageThanksOrder = GeneralSettingsModel.fromJson(item);
          } else if (item['title'] == 'no_transaksi' ||
              item['title'] == 'empty_transaksi') {
            imageNoTransaction = GeneralSettingsModel.fromJson(item);
          } else if (item['title'] == 'search_empty') {
            imageSearchEmpty = GeneralSettingsModel.fromJson(item);
          } else if (item['title'] == 'login_required') {
            imageNoLogin = GeneralSettingsModel.fromJson(item);
          }
        }

        printLog(imageNoTransaction.toString());

        logo = GeneralSettingsModel.fromJson(
            responseJson['general_settings']['logo']);
        wa = GeneralSettingsModel.fromJson(
            responseJson['general_settings']['wa']);
        sms = GeneralSettingsModel.fromJson(
            responseJson['general_settings']['sms']);
        phone = GeneralSettingsModel.fromJson(
            responseJson['general_settings']['phone']);
        about = GeneralSettingsModel.fromJson(
            responseJson['general_settings']['about']);
        currency = GeneralSettingsModel.fromJson(
            responseJson['general_settings']['currency']);
        formatCurrency = GeneralSettingsModel.fromJson(
            responseJson['general_settings']['format_currency']);
        privacy = GeneralSettingsModel.fromJson(
            responseJson['general_settings']['privacy_policy']);
        terms = GeneralSettingsModel.fromJson(
            responseJson['general_settings']['term_condition']);
        smartCoupon = responseJson['general_settings']['smart_coupon'];
        if (responseJson['general_settings']['searchbar_text'] != null) {
          searchBarText = GeneralSettingsModel.fromJson(
              responseJson['general_settings']['searchbar_text']);
        }
        if (responseJson['general_settings']['photoreviews'] != null) {
          isPhotoReviewActive =
              responseJson['general_settings']['photoreviews']['status'];
          photoMaxFiles =
              responseJson['general_settings']['photoreviews']['maxfiles'];
          photoMaxSize =
              responseJson['general_settings']['photoreviews']['maxsize'];
        }
        if (responseJson['general_settings']['sosmed_link'] != null) {
          sosmedLink = GeneralSettingsModel.fromJson(
              responseJson['general_settings']['sosmed_link']);
        }
        if (responseJson['general_settings']['terawallet'] != null) {
          isWalletActive = responseJson['general_settings']['terawallet'];
        }
        if (responseJson['general_settings']['barcode_active'] != null) {
          isBarcodeActive = responseJson['general_settings']['barcode_active'];
        }
        if (responseJson['general_settings']['gift_box_v2'] != null) {
          if (responseJson['general_settings']['gift_box_v2']['status'] !=
              null) {
            isGiftActive =
                responseJson['general_settings']['gift_box_v2']['status'];
          }
          if (responseJson['general_settings']['gift_box_v2']['image'] !=
              null) {
            giftBoxImage =
                responseJson['general_settings']['gift_box_v2']['image'];
          }
        }
        if (responseJson['general_settings']['flash_sale_bg_image'] != '') {
          flashSaleBgImage =
              responseJson['general_settings']['flash_sale_bg_image'];
        }
        if (responseJson['general_settings']['checkout_native'] != null) {
          isCheckoutNative =
              responseJson['general_settings']['checkout_native'];
        }

        if (responseJson['general_settings']['guest_checkout'] != null) {
          guestCheckoutActive =
              responseJson['general_settings']['guest_checkout'] == 'disable'
                  ? false
                  : true;
        }

        if (responseJson['app_color'] != []) {
          for (var i in responseJson['app_color']) {
            if (i['title'] == 'flash_bg_primary') {
              flashSaleBGColorPrimary = HexColor(i['description']);
            } else if (i['title'] == 'flash_bg_secondary') {
              flashSaleBGColorSecondary = HexColor(i['description']);
            } else if (i['title'] == 'flash_text_color') {
              flashSaleText = HexColor(i['description']);
            }
          }
        }

        billingAddress.clear();
        if (responseJson['general_settings']['additional_billing_address'] !=
            null) {
          printLog(
              "MASUK 1: ${json.encode(responseJson['general_settings']['additional_billing_address'])}");
          for (Map item in responseJson['general_settings']
              ['additional_billing_address']) {
            billingAddress.add(BillingAddress.fromJson(item));
          }
          printLog("MASUK : ${json.encode(billingAddress)}");
        }
        /*End*/

        if (responseJson['additional_menus'] != null) {
          additionalMenus = [];
          printLog("masuk");
          responseJson['additional_menus'].forEach((v) {
            additionalMenus.add(AdditionalMenusModel.fromJson(v));
          });
        }

        if (responseJson['customize_banner'] != null) {
          customizeBanner.clear();
          responseJson['customize_banner'].forEach((value) {
            customizeBanner.add(CustomizeBannerModel.fromJson(value));
          });
        }

        if (customizeBanner.isNotEmpty || customizeBanner != []) {
          customizeBannerMiniCategories.clear();
          customizeBannerFlashSale.clear();
          customizeBannerBannerSpecial.clear();
          customizeBannerBannerLove.clear();
          customizeBannerBannerSpecial.clear();
          customizeBannerProductBest.clear();
          customizeBannerProductRecomendation.clear();
          customizeBannerNewProduct.clear();
          customizeBannerRecentlyView.clear();

          customizeBannerMiniCategories['after'] = [];
          customizeBannerMiniCategories['before'] = [];
          customizeBannerFlashSale['after'] = [];
          customizeBannerFlashSale['before'] = [];
          customizeBannerBannerSpecial['after'] = [];
          customizeBannerBannerSpecial['before'] = [];
          customizeBannerBannerLove['after'] = [];
          customizeBannerBannerLove['before'] = [];
          customizeBannerBannerSpecial['after'] = [];
          customizeBannerBannerSpecial['before'] = [];
          customizeBannerProductBest['after'] = [];
          customizeBannerProductBest['before'] = [];
          customizeBannerProductRecomendation['after'] = [];
          customizeBannerProductRecomendation['before'] = [];
          customizeBannerNewProduct['after'] = [];
          customizeBannerNewProduct['before'] = [];
          customizeBannerRecentlyView['after'] = [];
          customizeBannerRecentlyView['before'] = [];

          for (var banner in customizeBanner) {
            if (banner.sectionType == 'mini_categories') {
              if (banner.sectionPosition == 'after') {
                customizeBannerMiniCategories['after']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              } else if (banner.sectionPosition == 'before') {
                customizeBannerMiniCategories['before']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              }
            } else if (banner.sectionType == 'flash_sale') {
              if (banner.sectionPosition == 'after') {
                customizeBannerFlashSale['after']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              } else if (banner.sectionPosition == 'before') {
                customizeBannerFlashSale['before']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              }
            } else if (banner.sectionType == 'addon_banner_special') {
              if (banner.sectionPosition == 'after') {
                customizeBannerBannerSpecial['after']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              } else if (banner.sectionPosition == 'before') {
                customizeBannerBannerSpecial['before']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              }
            } else if (banner.sectionType == 'addon_banner_love') {
              if (banner.sectionPosition == 'after') {
                customizeBannerBannerLove['after']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              } else if (banner.sectionPosition == 'before') {
                customizeBannerBannerLove['before']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              }
            } else if (banner.sectionType == 'addon_product_special') {
              if (banner.sectionPosition == 'after') {
                customizeBannerProductSpecial['after']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              } else if (banner.sectionPosition == 'before') {
                customizeBannerProductSpecial['before']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              }
            } else if (banner.sectionType == 'addon_product_best') {
              if (banner.sectionPosition == 'after') {
                customizeBannerProductBest['after']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              } else if (banner.sectionPosition == 'before') {
                customizeBannerProductBest['before']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              }
            } else if (banner.sectionType == 'addon_product_recomendation') {
              if (banner.sectionPosition == 'after') {
                customizeBannerProductRecomendation['after']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              } else if (banner.sectionPosition == 'before') {
                customizeBannerProductRecomendation['before']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              }
            } else if (banner.sectionType == 'new_product') {
              if (banner.sectionPosition == 'after') {
                customizeBannerNewProduct['after']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              } else if (banner.sectionPosition == 'before') {
                customizeBannerNewProduct['before']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              }
            } else if (banner.sectionType == 'recently_view') {
              if (banner.sectionPosition == 'after') {
                customizeBannerRecentlyView['after']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              } else if (banner.sectionPosition == 'before') {
                customizeBannerRecentlyView['before']?.add({
                  'image': banner.image,
                  'redirectType': banner.redirectType,
                  'redirectTo': banner.redirectTo
                });
              }
            }
          }
          printLog("${jsonEncode(customizeBannerMiniCategories)}",
              name: "Customize Banner Mini Categories");
        }

        /*Add Data Intro Page & Splash Screen*/
        splashscreen =
            GeneralSettingsModel.fromJson(responseJson['splashscreen']);
        intro.clear();
        for (Map item in responseJson['intro']) {
          intro.add(GeneralSettingsModel.fromJson(item));
        }
        intro = new List.from(intro.reversed);

        introStatus = responseJson['intro_page_status'];
        /*End*/

        /*Set Data App Color*/
        if (responseJson['app_color'] != null) {
          appColors.clear();
          for (Map item in responseJson['app_color']) {
            appColors.add(GeneralSettingsModel.fromJson(item));
          }
        }
        /*End*/

        a2wCountries.clear();
        if (responseJson['general_settings']['ali2woo_contry'] != null &&
            responseJson['general_settings']['ali2woo_contry'] != '') {
          responseJson['general_settings']['ali2woo_contry']
              .forEach((k, v) => a2wCountries.add(ShippingCountry(k, v)));
        }

        print("Completed");
        loading = false;
        notifyListeners();
      } else {
        loading = false;
        isLoadHomeSuccess = false;
        notifyListeners();
        print("Load Failed");
      }
    });
    return isLoadHomeSuccess;
    // } catch (e) {
    //   loading = false;
    //   isLoadHomeSuccess = false;
    //   notifyListeners();
    //   printLog('Error, $e', name: "Home Load Failed");
    //   return isLoadHomeSuccess;
    // }
  }

  Future<bool> fetchMoreRecommendation(String? productId,
      {int? page, required BuildContext context}) async {
    loadingMore = true;
    String country = base64Encode(
        utf8.encode(context.read<ProductProvider>().currentPosition));
    await ProductAPI()
        .fetchMoreProduct(
      context: context,
      include: productId,
      page: page,
      perPage: 10,
      order: '',
      orderBy: '',
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        if (page == 1) recommendationProducts[0].products!.clear();

        for (Map item in responseJson) {
          recommendationProducts[0].products!.add(ProductModel.fromJson(item));
        }

        loadingMore = false;
        notifyListeners();
      } else {
        print("Load Failed");
        loadingMore = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool?> fetchDiscountRule(context) async {
    loading = true;
    try {
      await HomeAPI().discRuleData(context).then((data) {
        if (data.statusCode == 200) {
          final responseJson = json.decode(data.body);

          discount = new Discount.fromJson(responseJson);
          printLog(responseJson.toString());
          print("Completed");
          loading = false;
          notifyListeners();
        } else {
          loading = false;
          isLoadHomeSuccess = false;
          notifyListeners();
          print("Load Failed");
        }
      });
      return isLoadHomeSuccess;
    } catch (e) {
      loading = false;
      isLoadHomeSuccess = false;
      notifyListeners();
      printLog('Error, $e', name: "Home Disc Load Failed");
      return isLoadHomeSuccess;
    }
  }

  changeGiftBox(bool status) {
    isGiftActive = status;
    notifyListeners();
  }

  changeIsReload() {
    isReload = false;
    notifyListeners();
  }

  setPackageInfo(value) {
    packageInfo = value;
    notifyListeners();
  }

  changeCountries(value) {
    selectedCountries = value;
    a2wCountries.forEach((element) {
      if (element.id == value) {
        selectedCountriesName = element.country;
      }
    });
    notifyListeners();
  }

  changePopBannerStatus(value) {
    isBannerPopChanged = value;
    notifyListeners();
  }
}
