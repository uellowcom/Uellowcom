/* Dart Package */
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:animated_text_kit/animated_text_kit.dart';
import 'package:colorful_safe_area/colorful_safe_area.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
// import 'package:draggable_widget/draggable_widget.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:internet_connection_checker/internet_connection_checker.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/pages/blog/blog_detail_screen.dart';
import 'package:nyoba/pages/category/brand_product_screen.dart';
import 'package:nyoba/pages/notification/notification_screen.dart';
import 'package:nyoba/pages/order/coupon_screen.dart';
import 'package:nyoba/pages/order/my_order_screen.dart';
import 'package:nyoba/pages/product/product_detail_screen.dart';
import 'package:nyoba/pages/product/product_more_screen.dart';
import 'package:nyoba/pages/search/search_screen.dart';
import 'package:nyoba/provider/coupon_provider.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/notification_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/provider/wallet_provider.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/widgets/draggable/draggable_widget.dart';
import 'package:nyoba/widgets/draggable/model/anchor_docker.dart';
/* Widget  */
import 'package:nyoba/widgets/home/banner/banner_container.dart';
import 'package:nyoba/widgets/home/banner/banner_pop_image.dart';
import 'package:nyoba/widgets/home/flashsale/flash_sale_countdown.dart';
import 'package:nyoba/widgets/product/grid_item_shimmer.dart';
import 'package:provider/provider.dart';
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:shimmer/shimmer.dart';
import 'package:url_launcher/url_launcher_string.dart';

import '../../app_localizations.dart';
import '../../provider/app_provider.dart';
/* Helper */
import '../../utils/utility.dart';
import '../../widgets/home/card_item_small.dart';
import '../../widgets/home/categories/badge_category.dart';
import '../../widgets/home/grid_item.dart';

class LobbyScreen extends StatefulWidget {
  LobbyScreen({Key? key}) : super(key: key);

  @override
  _LobbyScreenState createState() => _LobbyScreenState();
}

class _LobbyScreenState extends State<LobbyScreen>
    with TickerProviderStateMixin {
  AnimationController? _colorAnimationController;
  AnimationController? _textAnimationController;
  Animation? _colorTween, _titleColorTween, _iconColorTween, _moveTween;

  RefreshController _refreshController =
      RefreshController(initialRefresh: false);

  int itemCount = 10;
  int itemCategoryCount = 9;
  int? clickIndex = 0;
  int page = 1;
  String? selectedCategory;
  ScrollController _scrollController = new ScrollController();
  late StreamSubscription subscription;
  var isDeviceConnected = false;

  late ProductProvider products;
  late HomeProvider home;

  @override
  void initState() {
    super.initState();
    printLog('Init', name: 'Init Home');
    getConnectivity();

    products = Provider.of<ProductProvider>(context, listen: false);
    home = Provider.of<HomeProvider>(context, listen: false);
    _scrollController.addListener(() {
      if (_scrollController.position.pixels >=
              _scrollController.position.maxScrollExtent - 1500 &&
          products.isLastBestDeals == false) {
        if (Platform.isIOS && page == 20) {
          return;
        }

        // printLog("masuk max screen -200");
        if (!products.loadingBestDeals && products.listBestDeal.isNotEmpty) {
          setState(() {
            page++;
          });
          loadBestDeals();
        }
      }
    });
    _colorAnimationController =
        AnimationController(vsync: this, duration: Duration(seconds: 0));
    _colorTween = ColorTween(
      begin: primaryColor.withOpacity(0.0),
      end: primaryColor.withOpacity(1.0),
    ).animate(_colorAnimationController!);
    _titleColorTween = ColorTween(
      begin: Colors.white,
      end: HexColor("ED625E"),
    ).animate(_colorAnimationController!);
    _iconColorTween = ColorTween(begin: Colors.white, end: HexColor("#4A3F35"))
        .animate(_colorAnimationController!);
    _textAnimationController =
        AnimationController(vsync: this, duration: Duration(seconds: 0));
    _moveTween = Tween(
      begin: Offset(0, 0),
      end: Offset(-25, 0),
    ).animate(_colorAnimationController!);

    WidgetsBinding.instance.addPostFrameCallback((timeStamp) {
      loadHome();
    });

    if (home.isReload) {
      WidgetsBinding.instance.addPostFrameCallback((timeStamp) {
        refreshHome();
      });
    }

    if (Session.data.containsKey('isLogin') == true &&
        Session.data.getBool('isLogin')!) {
      loadRecentProduct();
      loadWallet();
      loadCoupon();
    }

    loadBestDeals();
    loadNotif();
  }

  @override
  void setState(fn) {
    if (mounted) {
      super.setState(fn);
    }
  }

  int item = 6;

  getConnectivity() {
    subscription = Connectivity().onConnectivityChanged.listen((result) async {
      // isDeviceConnected = await InternetConn
      isDeviceConnected = await InternetConnectionChecker().hasConnection;
      if (!isDeviceConnected) {
        showDialogBox();
      }
    });
  }

  showDialogBox() {
    showDialog(
      barrierDismissible: false,
      context: context,
      barrierColor: Colors.black54,
      builder: (context) => WillPopScope(
        child: Dialog.fullscreen(
          child: Container(
            height: double.infinity,
            width: double.infinity,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Image.asset(
                  "images/something-wrong.jpg",
                  width: 200,
                ),
                Text(
                  "Oops! Something went wrong",
                  style: TextStyle(fontWeight: FontWeight.w500),
                ),
                SizedBox(
                  height: 12,
                ),
                Text(
                  "This doesn't seem right! Let us try to sort this out.",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: responsiveFont(10),
                    fontWeight: FontWeight.w500,
                    color: Colors.black54,
                  ),
                ),
                SizedBox(
                  height: 16.h,
                ),
                GestureDetector(
                  onTap: () async {
                    Navigator.pop(context, "Cancel");
                    isDeviceConnected =
                        await InternetConnectionChecker().hasConnection;
                    if (!isDeviceConnected) {
                      showDialogBox();
                    }
                  },
                  child: Container(
                    width: 100,
                    alignment: Alignment.center,
                    padding: EdgeInsets.symmetric(vertical: 10),
                    // margin: EdgeInsets.symmetric(horizontal: 50),
                    decoration: BoxDecoration(
                      color: Colors.blue[800],
                      borderRadius: BorderRadius.all(Radius.circular(5)),
                    ),
                    child: Text("Retry", style: TextStyle(color: Colors.white)),
                  ),
                )
              ],
            ),
          ),
        ),
        onWillPop: () async => false,
      ),
    );
  }

  loadNotif() async {
    if (Session.data.containsKey('isLogin')) {
      if (Session.data.getBool('isLogin')!)
        await Provider.of<NotificationProvider>(context, listen: false)
            .fetchNotifications(context: context);
    }
  }

  loadNewProduct(bool loading) async {
    this.setState(() {});
    await products.fetchNewProducts(
        context: context, clickIndex == 0 ? '' : clickIndex.toString());
  }

  loadRecentProduct() async {
    await products.fetchRecentProducts(context);
  }

  loadHome() async {
    await home.fetchHomeData(context);

    if (home.bannerPopUp.first.image != null &&
        home.bannerPopUp.first.image != "" &&
        home.isBannerPopChanged) {
      await showDialog(context: context, builder: (_) => BannerPopImage())
          .then((value) {
        home.changePopBannerStatus(false);
        printLog("Close Banner");
      });
    }
  }

  loadWallet() async {
    if (Session.data.getBool('isLogin')!)
      await Provider.of<WalletProvider>(context, listen: false)
          .fetchBalance(context);
  }

  refreshHome() async {
    if (mounted) {
      context.read<WalletProvider>().changeWalletStatus();
      loadWallet();
      await home.fetchHome(context);
      loadNewProduct(true);
      loadCoupon();
      loadNotif();
      _refreshController.refreshCompleted();
      await home.changeIsReload();
    }
  }

  loadBestDeals() async {
    await products.fetchBestDeals(
        context: context,
        clickIndex == 0 ? '' : clickIndex.toString(),
        page: page);
  }

  loadCoupon() async {
    await Provider.of<CouponProvider>(context, listen: false)
        .fetchCoupon(page: 1, context: context)
        .then((value) => this.setState(() {}));
  }

  @override
  void dispose() {
    super.dispose();
    _scrollController.dispose();
  }

  final dragController = DragController();

  @override
  Widget build(BuildContext context) {
    final coupons = Provider.of<CouponProvider>(context, listen: false);
    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;

    Widget buildNewProducts = Container(
      child: ListenableProvider.value(
        value: products,
        child: Consumer<ProductProvider>(builder: (context, value, child) {
          if (value.loadingNew) {
            return Container(
                height: MediaQuery.of(context).size.height / 3.0,
                child: shimmerProductItemSmall());
          }
          return AspectRatio(
            aspectRatio: locale == Locale('ar') ? 6.h / 4.1.h : 6.h / 4.0.h,
            child: ListView.separated(
              itemCount: value.listNewProduct.length,
              scrollDirection: Axis.horizontal,
              itemBuilder: (context, i) {
                return CardItem(
                  product: value.listNewProduct[i],
                  i: i,
                  itemCount: value.listNewProduct.length,
                );
              },
              separatorBuilder: (BuildContext context, int index) {
                return SizedBox(
                  width: 5,
                );
              },
            ),
          );
        }),
      ),
    );

    Widget buildRecentProducts = Container(
      child: ListenableProvider.value(
        value: products,
        child: Consumer<ProductProvider>(builder: (context, value, child) {
          return Visibility(
              visible: value.listRecentProduct.isNotEmpty,
              child: Column(
                children: [
                  Container(
                    margin: EdgeInsets.only(left: 15, right: 15, bottom: 10),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          AppLocalizations.of(context)!
                              .translate('recent_view')!,
                          style: TextStyle(
                              fontSize: responsiveFont(14),
                              fontWeight: FontWeight.w600),
                        ),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                                context,
                                MaterialPageRoute(
                                    builder: (context) => ProductMoreScreen(
                                          name: AppLocalizations.of(context)!
                                              .translate('recent_view')!,
                                          include: value.productRecent,
                                        )));
                          },
                          child: Text(
                            AppLocalizations.of(context)!.translate('more')!,
                            style: TextStyle(
                              fontSize: responsiveFont(12),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  AspectRatio(
                    aspectRatio:
                        locale == Locale('ar') ? 6.h / 4.1.h : 6.h / 4.0.h,
                    child: ListView.separated(
                      itemCount: value.listRecentProduct.length,
                      scrollDirection: Axis.horizontal,
                      itemBuilder: (context, i) {
                        return CardItem(
                          product: value.listRecentProduct[i],
                          i: i,
                          itemCount: value.listRecentProduct.length,
                        );
                      },
                      separatorBuilder: (BuildContext context, int index) {
                        return SizedBox(
                          width: 5,
                        );
                      },
                    ),
                  )
                ],
              ));
        }),
      ),
    );

    Widget buildRecommendation = Container(
        color: HexColor('EBEBEB'),
        child: ListView(
          shrinkWrap: true,
          // physics: ScrollPhysics(),
          primary: false,
          children: [
            Container(
              margin: EdgeInsets.only(left: 15, right: 15),
              child: Text(
                home.recommendationProducts[0].title!,
                style: TextStyle(
                    fontSize: responsiveFont(14), fontWeight: FontWeight.w600),
              ),
            ),
            Container(
                margin: EdgeInsets.only(left: 15, right: 15),
                child: Text(
                  home.recommendationProducts[0].description ?? "",
                  style: TextStyle(
                    fontSize: responsiveFont(12),
                    color: Colors.black,
                  ),
                  textAlign: TextAlign.justify,
                )),
            //recommendation item
            Container(
              child: MasonryGridView.count(
                crossAxisCount: 2,
                padding: EdgeInsets.symmetric(horizontal: 15, vertical: 10),
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                shrinkWrap: true,
                itemCount: home.recommendationProducts[0].products!.length,
                physics: ScrollPhysics(),
                itemBuilder: (context, i) {
                  return GridItem(
                    i: i,
                    itemCount: home.recommendationProducts[0].products!.length,
                    product: home.recommendationProducts[0].products![i],
                  );
                },
              ),
            )
          ],
        ));

    return ColorfulSafeArea(
      color: primaryColor,
      child: Scaffold(
        resizeToAvoidBottomInset: false,
        backgroundColor: HexColor("EBEBEB"),
        body: Stack(
          children: [
            SmartRefresher(
              controller: _refreshController,
              scrollController: _scrollController,
              onRefresh: refreshHome,
              child: SingleChildScrollView(
                physics: ScrollPhysics(),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      color: Colors.white,
                      child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Stack(
                              children: [
                                Column(
                                  children: [
                                    SizedBox(
                                      height: 55.h,
                                    ),
                                    Consumer<HomeProvider>(
                                        builder: (context, value, child) {
                                      if (value.loading) {
                                        return Container();
                                      } else {
                                        return Container(
                                          height: MediaQuery.of(context)
                                                  .size
                                                  .height /
                                              21,
                                          child: ListView.separated(
                                              itemCount:
                                                  value.newCategories.length,
                                              scrollDirection: Axis.horizontal,
                                              itemBuilder: (context, i) {
                                                return GestureDetector(
                                                    onTap: () {
                                                      printLog(
                                                          "${jsonEncode(value.newCategories[i].id)}");
                                                      Navigator.push(
                                                          context,
                                                          MaterialPageRoute(
                                                            builder: (context) =>
                                                                BrandProducts(
                                                              isNeedSub: true,
                                                              brandName: value
                                                                  .newCategories[
                                                                      i]
                                                                  .name,
                                                              categoryId: value
                                                                  .newCategories[
                                                                      i]
                                                                  .id
                                                                  .toString(),
                                                              withFilter: true,
                                                            ),
                                                          ));
                                                      // if (value
                                                      //         .productCategories[
                                                      //             i]
                                                      //         .id ==
                                                      //     clickIndex) {
                                                      //   setState(() {
                                                      //     page = 1;
                                                      //     clickIndex = 0;
                                                      //     selectedCategory =
                                                      //         AppLocalizations.of(
                                                      //                 context)!
                                                      //             .translate(
                                                      //                 'new_product');
                                                      //   });
                                                      // } else {
                                                      // setState(() {
                                                      //   page = 1;
                                                      //   clickIndex = value
                                                      //       .newCategories[i]
                                                      //       .id;
                                                      //   selectedCategory = value
                                                      //       .newCategories[i]
                                                      //       .name;
                                                      // });
                                                      // }
                                                      // loadNewProduct(true);
                                                      // loadBestDeals();
                                                      // setState(() {});
                                                    },
                                                    child: tabCategory(
                                                        value.newCategories[i],
                                                        i,
                                                        value.newCategories
                                                            .length));
                                              },
                                              separatorBuilder:
                                                  (BuildContext context,
                                                      int index) {
                                                return SizedBox(
                                                  width: 1.w,
                                                );
                                              }),
                                        );
                                      }
                                    }),
                                    Consumer<HomeProvider>(
                                        builder: (context, value, child) {
                                      return BannerContainer(
                                        contentHeight:
                                            MediaQuery.of(context).size.height,
                                        dataSliderLength: value.banners.length,
                                        dataSlider: value.banners,
                                        loading: customLoading(),
                                      );
                                    }),
                                  ],
                                ),
                                appBar(),
                              ],
                            ),
                            // wallet
                            // WalletCard(showBtnMore: true),
                            Visibility(
                                visible: home.customizeBannerMiniCategories
                                        .isNotEmpty &&
                                    home.customizeBannerMiniCategories
                                        .containsKey('before'),
                                child: Column(
                                  children: [
                                    for (var i
                                        in home.customizeBannerMiniCategories[
                                                'before'] ??
                                            [])
                                      customizeBanner(
                                          image: i['image'] ?? '',
                                          redirectTo: i['redirectTo'] ?? '',
                                          redirectType: i['redirectType'] ?? '',
                                          type: 'before'),
                                  ],
                                )),
                            Container(
                              height: 5.h,
                            ),
                            //category section
                            Consumer<HomeProvider>(
                                builder: (context, value, child) {
                              return BadgeCategory(
                                value.categories,
                              );
                            }),
                            Visibility(
                                visible: home.customizeBannerMiniCategories
                                        .isNotEmpty &&
                                    home.customizeBannerMiniCategories
                                        .containsKey('after'),
                                child: Column(
                                  children: [
                                    for (var i
                                        in home.customizeBannerMiniCategories[
                                                'after'] ??
                                            [])
                                      customizeBanner(
                                          image: i['image'] ?? '',
                                          redirectTo: i['redirectTo'] ?? '',
                                          redirectType: i['redirectType'] ?? '',
                                          type: 'after')
                                  ],
                                )),
                            Visibility(
                                visible:
                                    home.customizeBannerFlashSale.isNotEmpty &&
                                        home.customizeBannerFlashSale
                                            .containsKey('before'),
                                child: Column(
                                  children: [
                                    for (var i in home.customizeBannerFlashSale[
                                            'before'] ??
                                        [])
                                      customizeBanner(
                                          image: i['image'] ?? '',
                                          redirectTo: i['redirectTo'] ?? '',
                                          redirectType: i['redirectType'] ?? '',
                                          type: 'before')
                                  ],
                                )),
                            //flash sale countdown & card product item
                            Consumer<HomeProvider>(
                                builder: (context, value, child) {
                              if (value.flashSales.isEmpty) {
                                return Container();
                              }
                              return FlashSaleCountdown(
                                dataFlashSaleCountDown: home.flashSales,
                                dataFlashSaleProducts:
                                    home.flashSales[0].products,
                                textAnimationController:
                                    _textAnimationController,
                                colorAnimationController:
                                    _colorAnimationController,
                                colorTween: _colorTween,
                                iconColorTween: _iconColorTween,
                                moveTween: _moveTween,
                                titleColorTween: _titleColorTween,
                                loading: home.loading,
                              );
                            }),
                          ]),
                    ),
                    Visibility(
                        visible: home.customizeBannerFlashSale.isNotEmpty &&
                            home.customizeBannerFlashSale.containsKey('after'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerFlashSale['after'] ?? [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'after')
                          ],
                        )),
                    Visibility(
                        visible: home.customizeBannerNewProduct.isNotEmpty &&
                            home.customizeBannerNewProduct
                                .containsKey('before'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerNewProduct['before'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'before')
                          ],
                        )),
                    Container(
                      width: double.infinity,
                      margin: EdgeInsets.only(
                          left: 15, bottom: 10, right: 15, top: 15),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            AppLocalizations.of(context)!
                                .translate('new_product')!,
                            style: TextStyle(
                                fontSize: responsiveFont(14),
                                fontWeight: FontWeight.w600),
                          ),
                          GestureDetector(
                            onTap: () {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) => BrandProducts(
                                            isNeedSub: true,
                                            withFilter: false,
                                            categoryId: clickIndex == 0
                                                ? ''
                                                : clickIndex.toString(),
                                            brandName: selectedCategory ??
                                                AppLocalizations.of(context)!
                                                    .translate('new_product'),
                                            sortIndex: 1,
                                          )));
                            },
                            child: Text(
                              AppLocalizations.of(context)!.translate('more')!,
                              style: TextStyle(
                                fontSize: responsiveFont(12),
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    // Consumer<CategoryProvider>(
                    //     builder: (context, value, child) {
                    //   if (value.loading) {
                    //     return Container();
                    //   } else {
                    //     return Container(
                    //       height: MediaQuery.of(context).size.height / 21,
                    //       child: ListView.separated(
                    //           itemCount: value.productCategories.length,
                    //           scrollDirection: Axis.horizontal,
                    //           itemBuilder: (context, i) {
                    //             return GestureDetector(
                    //                 onTap: () {
                    //                   if (value.productCategories[i].id ==
                    //                       clickIndex) {
                    //                     setState(() {
                    //                       clickIndex = 0;
                    //                       selectedCategory =
                    //                           AppLocalizations.of(context)!
                    //                               .translate('new_product');
                    //                     });
                    //                   } else {
                    //                     setState(() {
                    //                       clickIndex =
                    //                           value.productCategories[i].id;
                    //                       selectedCategory =
                    //                           value.productCategories[i].name;
                    //                     });
                    //                   }
                    //                   loadNewProduct(true);
                    //                   setState(() {});
                    //                 },
                    //                 child: tabCategory(
                    //                     value.productCategories[i],
                    //                     i,
                    //                     value.productCategories.length));
                    //           },
                    //           separatorBuilder:
                    //               (BuildContext context, int index) {
                    //             return SizedBox(
                    //               width: 8,
                    //             );
                    //           }),
                    //     );
                    //   }
                    // }),
                    Container(
                      height: 10,
                    ),
                    buildNewProducts,
                    Visibility(
                        visible: home.customizeBannerNewProduct.isNotEmpty &&
                            home.customizeBannerNewProduct.containsKey('after'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerNewProduct['after'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'after')
                          ],
                        )),
                    Visibility(
                      visible: !home.customizeBannerBannerSpecial.isNotEmpty,
                      child: Container(
                        height: 15,
                      ),
                    ),
                    Visibility(
                        visible: home.customizeBannerBannerSpecial.isNotEmpty &&
                            home.customizeBannerBannerSpecial
                                .containsKey('before'),
                        child: Column(
                          children: [
                            for (var i in home
                                    .customizeBannerBannerSpecial['before'] ??
                                [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'before')
                          ],
                        )),
                    SizedBox(
                      height: 8.h,
                    ),
                    Container(
                      margin: EdgeInsets.symmetric(
                        horizontal: 15,
                      ),
                      child: Text(
                        "${AppLocalizations.of(context)!.translate('special_promo')}",
                        style: TextStyle(
                            fontSize: responsiveFont(14),
                            fontWeight: FontWeight.w600),
                      ),
                    ),
                    //Mini Banner Item start Here
                    Consumer<HomeProvider>(builder: (context, value, child) {
                      return Container(
                        margin: EdgeInsets.only(
                            left: 15, right: 15, top: 10, bottom: 15),
                        child: GridView.builder(
                          primary: false,
                          shrinkWrap: true,
                          itemCount: value.bannerSpecial.length,
                          gridDelegate:
                              SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisSpacing: 10,
                                  mainAxisSpacing: 10,
                                  crossAxisCount: 2,
                                  childAspectRatio: 2 / 1),
                          itemBuilder: (context, i) {
                            return Container(
                              decoration: BoxDecoration(
                                  color: primaryColor,
                                  borderRadius: BorderRadius.circular(5)),
                              child: InkWell(
                                onTap: () {
                                  if (value.bannerSpecial[i].linkTo ==
                                      'product') {
                                    Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                            builder: (context) => ProductDetail(
                                                  productId: value
                                                      .bannerSpecial[i].product
                                                      .toString(),
                                                )));
                                  } else if (value.bannerSpecial[i].linkTo ==
                                      'category') {
                                    Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                            builder: (context) => BrandProducts(
                                                  isNeedSub: true,
                                                  withFilter: false,
                                                  categoryId: value
                                                      .bannerSpecial[i].product
                                                      .toString(),
                                                  brandName: value
                                                      .bannerSpecial[i].name,
                                                )));
                                  }
                                },
                                child: Image.network(
                                    value.bannerSpecial[i].image!),
                              ),
                            );
                          },
                        ),
                      );
                    }),
                    Visibility(
                        visible: home.customizeBannerBannerSpecial.isNotEmpty &&
                            home.customizeBannerBannerSpecial
                                .containsKey('after'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerBannerSpecial['after'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'after')
                          ],
                        )),
                    Visibility(
                        visible:
                            home.customizeBannerProductSpecial.isNotEmpty &&
                                home.customizeBannerProductSpecial
                                    .containsKey('before'),
                        child: Column(
                          children: [
                            for (var i in home
                                    .customizeBannerProductSpecial['before'] ??
                                [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'before')
                          ],
                        )),
                    //special for you item
                    Consumer<HomeProvider>(builder: (context, value, child) {
                      return Column(
                        children: [
                          Container(
                              width: double.infinity,
                              margin: EdgeInsets.only(
                                  left: 15, bottom: 10, right: 15),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment:
                                        MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        value.specialProducts[0].title!,
                                        style: TextStyle(
                                            fontSize: responsiveFont(14),
                                            fontWeight: FontWeight.w600),
                                      ),
                                      GestureDetector(
                                        onTap: () {
                                          Navigator.push(
                                              context,
                                              MaterialPageRoute(
                                                  builder: (context) =>
                                                      ProductMoreScreen(
                                                        include: products
                                                            .productSpecial
                                                            .products,
                                                        name: value
                                                            .specialProducts[0]
                                                            .title,
                                                      )));
                                        },
                                        child: Text(
                                          AppLocalizations.of(context)!
                                              .translate('more')!,
                                          style: TextStyle(
                                            fontSize: responsiveFont(12),
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  Text(
                                    value.specialProducts[0].description ?? "",
                                    style: TextStyle(
                                      fontSize: responsiveFont(12),
                                      color: Colors.black,
                                    ),
                                    textAlign: TextAlign.justify,
                                  )
                                ],
                              )),
                          AspectRatio(
                            aspectRatio: locale == Locale('ar')
                                ? 6.h / 4.1.h
                                : 6.h / 4.0.h,
                            child: value.loading
                                ? shimmerProductItemSmall()
                                : ListView.separated(
                                    itemCount: value
                                        .specialProducts[0].products!.length,
                                    scrollDirection: Axis.horizontal,
                                    itemBuilder: (context, i) {
                                      return CardItem(
                                        product: value
                                            .specialProducts[0].products![i],
                                        i: i,
                                        itemCount: value.specialProducts[0]
                                            .products!.length,
                                      );
                                    },
                                    separatorBuilder:
                                        (BuildContext context, int index) {
                                      return SizedBox(
                                        width: 5,
                                      );
                                    },
                                  ),
                          ),
                        ],
                      );
                    }),
                    Visibility(
                        visible:
                            home.customizeBannerProductSpecial.isNotEmpty &&
                                home.customizeBannerProductSpecial
                                    .containsKey('after'),
                        child: Column(
                          children: [
                            for (var i in home
                                    .customizeBannerProductSpecial['after'] ??
                                [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'after')
                          ],
                        )),
                    Visibility(
                      visible: !home.customizeBannerProductBest.isNotEmpty,
                      child: Container(
                        height: 10,
                      ),
                    ),
                    Visibility(
                        visible: home.customizeBannerProductBest.isNotEmpty &&
                            home.customizeBannerProductBest
                                .containsKey('before'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerProductBest['before'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'before')
                          ],
                        )),
                    SizedBox(
                      height: 10.h,
                    ),
                    Stack(
                      children: [
                        Container(
                          color: primaryColor,
                          width: double.infinity,
                          height: MediaQuery.of(context).size.height / 3.5,
                        ),
                        Consumer<HomeProvider>(
                            builder: (context, value, child) {
                          if (value.loading) {
                            return Column(
                              children: [
                                Shimmer.fromColors(
                                    child: Container(
                                      width: double.infinity,
                                      margin: EdgeInsets.only(
                                          left: 15, right: 15, top: 10),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            mainAxisAlignment:
                                                MainAxisAlignment.spaceBetween,
                                            children: [
                                              Container(
                                                width: 150,
                                                height: 10,
                                                color: Colors.white,
                                              )
                                            ],
                                          ),
                                          Container(
                                            height: 2,
                                          ),
                                          Container(
                                            width: 100,
                                            height: 8,
                                            color: Colors.white,
                                          )
                                        ],
                                      ),
                                    ),
                                    baseColor: Colors.grey[300]!,
                                    highlightColor: Colors.grey[100]!),
                                Container(
                                  height: 10,
                                ),
                                Container(
                                  height:
                                      MediaQuery.of(context).size.height / 3.0,
                                  child: shimmerProductItemSmall(),
                                )
                              ],
                            );
                          }
                          return Column(
                            children: [
                              Container(
                                width: double.infinity,
                                margin: EdgeInsets.only(
                                    left: 15, right: 15, top: 10),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceBetween,
                                      children: [
                                        Text(
                                          value.bestProducts[0].title!,
                                          style: TextStyle(
                                              color: Colors.black,
                                              fontSize: responsiveFont(14),
                                              fontWeight: FontWeight.w600),
                                        ),
                                        GestureDetector(
                                          onTap: () {
                                            Navigator.push(
                                                context,
                                                MaterialPageRoute(
                                                    builder: (context) =>
                                                        ProductMoreScreen(
                                                          name: value
                                                              .bestProducts[0]
                                                              .title,
                                                          include: products
                                                              .productBest
                                                              .products,
                                                        )));
                                          },
                                          child: Text(
                                            AppLocalizations.of(context)!
                                                .translate('more')!,
                                            style: TextStyle(
                                                fontSize: responsiveFont(12),
                                                fontWeight: FontWeight.w600,
                                                color: Colors.black),
                                          ),
                                        ),
                                      ],
                                    ),
                                    Text(
                                      value.bestProducts[0].description ?? "",
                                      style: TextStyle(
                                        fontSize: responsiveFont(12),
                                        color: Colors.black,
                                      ),
                                      textAlign: TextAlign.justify,
                                    )
                                  ],
                                ),
                              ),
                              Container(
                                height: 10,
                              ),
                              AspectRatio(
                                aspectRatio: locale == Locale('ar')
                                    ? 6.h / 4.1.h
                                    : 6.h / 4.0.h,
                                child: ListView.separated(
                                  itemCount:
                                      value.bestProducts[0].products!.length,
                                  scrollDirection: Axis.horizontal,
                                  itemBuilder: (context, i) {
                                    return CardItem(
                                      product:
                                          value.bestProducts[0].products![i],
                                      i: i,
                                      itemCount: value
                                          .bestProducts[0].products!.length,
                                    );
                                  },
                                  separatorBuilder:
                                      (BuildContext context, int index) {
                                    return SizedBox(
                                      width: 5,
                                    );
                                  },
                                ),
                              )
                            ],
                          );
                        }),
                      ],
                    ),
                    Visibility(
                        visible: home.customizeBannerProductBest.isNotEmpty &&
                            home.customizeBannerProductBest
                                .containsKey('after'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerProductBest['after'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'after')
                          ],
                        )),
                    Visibility(
                        visible: home.customizeBannerBannerLove.isNotEmpty &&
                            home.customizeBannerBannerLove
                                .containsKey('before'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerBannerLove['before'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'before')
                          ],
                        )),
                    Container(
                      margin: EdgeInsets.only(
                          left: 15, right: 15, top: 10.h, bottom: 10),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            "${AppLocalizations.of(context)!.translate('love_these_items')}",
                            style: TextStyle(
                                fontSize: responsiveFont(14),
                                fontWeight: FontWeight.w600),
                          ),
                          /*GestureDetector(
                            onTap: () {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) => AllProducts()));
                            },
                            child: Text(
                              "More",
                              style: TextStyle(
                                  fontSize: responsiveFont(12),
                                  fontWeight: FontWeight.w600,
                                  color: secondaryColor),
                            ),
                          ),*/
                        ],
                      ),
                    ),
                    //Mini Banner Item start Here
                    Consumer<HomeProvider>(builder: (context, value, child) {
                      return Container(
                        margin: EdgeInsets.only(
                            left: 15, right: 15, top: 10, bottom: 15),
                        child: GridView.builder(
                          primary: false,
                          shrinkWrap: true,
                          itemCount: value.bannerLove.length,
                          gridDelegate:
                              SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisSpacing: 10,
                                  mainAxisSpacing: 10,
                                  crossAxisCount: 2,
                                  childAspectRatio: 2 / 1),
                          itemBuilder: (context, i) {
                            return Container(
                              decoration: BoxDecoration(
                                  color: primaryColor,
                                  borderRadius: BorderRadius.circular(5)),
                              child: InkWell(
                                  onTap: () {
                                    if (value.bannerLove[i].product != null &&
                                        value.bannerLove[i].linkTo ==
                                            "product") {
                                      Navigator.push(
                                          context,
                                          MaterialPageRoute(
                                              builder: (context) =>
                                                  ProductDetail(
                                                    productId: value
                                                        .bannerLove[i].product
                                                        .toString(),
                                                  )));
                                    } else if (value.bannerLove[i].linkTo ==
                                        "category") {
                                      Navigator.push(
                                          context,
                                          MaterialPageRoute(
                                              builder: (context) =>
                                                  BrandProducts(
                                                    isNeedSub: true,
                                                    withFilter: false,
                                                    categoryId: value
                                                        .bannerLove[i].product
                                                        .toString(),
                                                    brandName: value
                                                        .bannerLove[i].name,
                                                  )));
                                    }
                                  },
                                  child: Image.network(
                                      value.bannerLove[i].image!)),
                            );
                          },
                        ),
                      );
                    }),
                    Visibility(
                        visible: home.customizeBannerBannerLove.isNotEmpty &&
                            home.customizeBannerBannerLove.containsKey('after'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerBannerLove['after'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'after')
                          ],
                        )),
                    Visibility(
                        visible: home.customizeBannerRecentlyView.isNotEmpty &&
                            home.customizeBannerRecentlyView
                                .containsKey('before'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerRecentlyView['before'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'before')
                          ],
                        )),
                    //recently viewed item
                    buildRecentProducts,
                    Visibility(
                        visible: home.customizeBannerRecentlyView.isNotEmpty &&
                            home.customizeBannerRecentlyView
                                .containsKey('after'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerRecentlyView['after'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'after')
                          ],
                        )),
                    Visibility(
                      visible:
                          !home.customizeBannerProductRecomendation.isNotEmpty,
                      child: Container(
                        height: 5,
                      ),
                    ),
                    Visibility(
                      visible:
                          !home.customizeBannerProductRecomendation.isNotEmpty,
                      child: Container(
                        width: double.infinity,
                        height: 7,
                        color: HexColor("EBEBEB"),
                      ),
                    ),
                    Visibility(
                        visible: home.customizeBannerProductRecomendation
                                .isNotEmpty &&
                            home.customizeBannerProductRecomendation
                                .containsKey('before'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerProductRecomendation[
                                        'before'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'before')
                          ],
                        )),
                    SizedBox(
                      height: 10.h,
                    ),
                    buildRecommendation,
                    Visibility(
                        visible: home.customizeBannerProductRecomendation
                                .isNotEmpty &&
                            home.customizeBannerProductRecomendation
                                .containsKey('after'),
                        child: Column(
                          children: [
                            for (var i
                                in home.customizeBannerProductRecomendation[
                                        'after'] ??
                                    [])
                              customizeBanner(
                                  image: i['image'] ?? '',
                                  redirectTo: i['redirectTo'] ?? '',
                                  redirectType: i['redirectType'] ?? '',
                                  type: 'after')
                          ],
                        )),
                    // Visibility(
                    //   visible:
                    //       !home.customizeBannerProductRecomendation.isNotEmpty,
                    //   child: Container(
                    //     width: double.infinity,
                    //     height: 5,
                    //     color: HexColor("FFFFFF"),
                    //   ),
                    // ),
                    SizedBox(
                      height: 10.h,
                    ),
                    bestDealProduct()
                  ],
                ),
              ),
            ),
            Consumer<HomeProvider>(
              builder: (context, value, child) {
                return Visibility(
                    visible: coupons.coupons.isNotEmpty && value.isGiftActive,
                    child: DraggableWidget(
                      bottomMargin: 160.h,
                      topMargin: 60,
                      intialVisibility: true,
                      horizontalSpace: 3,
                      verticalSpace: 30,
                      normalShadow: BoxShadow(
                        color: Colors.transparent,
                        offset: Offset(0, 10),
                        blurRadius: 0,
                      ),
                      shadowBorderRadius: 50,
                      child: GestureDetector(
                          onTap: () {
                            Navigator.push(
                                context,
                                MaterialPageRoute(
                                    builder: (context) => CouponScreen()));
                          },
                          child: Container(
                              height: 100,
                              width: 100,
                              child: Image.network(value.giftBoxImage))),
                      initialPosition: AnchoringPosition.bottomRight,
                      dragController: dragController,
                    ));
              },
            )
          ],
        ),
      ),
    );
  }

  Widget customizeBanner(
      {required String image,
      required String redirectType,
      required String redirectTo,
      required String type}) {
    return GestureDetector(
      onTap: () async {
        printLog('$redirectType');
        if (redirectType == 'product') {
          Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (context) => ProductDetail(
                        productId: redirectTo,
                      )));
        } else if (redirectType == 'category') {
          Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (context) => BrandProducts(
                        isNeedSub: true,
                        withFilter: false,
                        categoryId: redirectTo,
                        brandName: redirectType,
                      )));
        } else if (redirectType == 'blog') {
          Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (context) => BlogDetail(
                        slug: redirectTo,
                      )));
        } else if (redirectType == 'attribute') {
          Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (context) => BrandProducts(
                        isNeedSub: true,
                        withFilter: false,
                        categoryId: redirectTo,
                        brandName: redirectType,
                      )));
        } else if (redirectType == 'url') {
          if (await canLaunchUrlString(redirectTo)) {
            await launchUrlString(redirectTo,
                mode: LaunchMode.externalApplication);
          } else {
            snackBar(context,
                color: Colors.red, message: 'Could not launch $redirectTo');
            throw 'Could not launch $redirectTo';
          }
        }
      },
      child: Container(
        margin: type == 'before'
            ? EdgeInsets.symmetric(horizontal: 12.w, vertical: 5.h)
            : EdgeInsets.only(right: 12.w, left: 12.w, top: 5.h),
        child: Image.network(
          image,
          fit: BoxFit.cover,
        ),
      ),
    );
  }

  Widget tabCategory(ProductCategoryModel model, int i, int count) {
    return Container(
      margin: EdgeInsets.only(
          left: i == 0 ? 10 : 0, right: i == count - 1 ? 10 : 0),
      child: Tab(
        child: Container(
            padding: EdgeInsets.symmetric(horizontal: 14, vertical: 5),
            decoration: BoxDecoration(
              // color: clickIndex == model.id
              //     ? primaryColor.withOpacity(0.5)
              //     : Colors.white,
              border: Border(
                bottom: BorderSide(
                    width: 1.5,
                    color: clickIndex == model.id
                        ? secondaryColor
                        : Colors.transparent),
              ),
              // borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              convertHtmlUnescape(model.name!),
              style: TextStyle(
                  fontSize: 13,
                  color: clickIndex == model.id ? Colors.black : Colors.black),
            )),
      ),
    );
  }

  Widget appBar() {
    final animatedText =
        Provider.of<HomeProvider>(context, listen: false).searchBarText;
    return Material(
      elevation: 0,
      child: Container(
        width: MediaQuery.of(context).size.width,
        decoration: BoxDecoration(
          color: Colors.white,
        ),
        child: Container(
          height: 60.h,
          padding: EdgeInsets.only(left: 15, right: 10, top: 15),
          child: Row(
            children: [
              Expanded(
                  flex: 4,
                  child: InkWell(
                    onTap: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (context) => SearchScreen()));
                    },
                    child: Container(
                        padding: EdgeInsets.symmetric(horizontal: 10),
                        width: 200.w,
                        height: 30.h,
                        decoration: BoxDecoration(
                            // border: Border.all(color: Colors.black),
                            borderRadius: BorderRadius.circular(5),
                            color: Colors.grey[100]),
                        alignment: Alignment.centerLeft,
                        child: Row(
                          children: [
                            Icon(
                              Icons.search,
                              color: Colors.black45,
                            ),
                            SizedBox(
                              width: 5,
                            ),
                            Expanded(
                              child: animatedText.description != null
                                  ? DefaultTextStyle(
                                      style: TextStyle(
                                          fontSize: responsiveFont(12),
                                          color: Colors.black45),
                                      child: AnimatedTextKit(
                                        isRepeatingAnimation: true,
                                        repeatForever: true,
                                        animatedTexts: [
                                          TyperAnimatedText(
                                              AppLocalizations.of(context)!
                                                  .translate('search')!,
                                              speed:
                                                  Duration(milliseconds: 80)),
                                          if (animatedText.description['text_1']
                                                  .isNotEmpty &&
                                              animatedText.description != null)
                                            TyperAnimatedText(animatedText
                                                .description['text_1']),
                                          if (animatedText.description['text_2']
                                                  .isNotEmpty &&
                                              animatedText.description != null)
                                            TyperAnimatedText(animatedText
                                                .description['text_2']),
                                          if (animatedText.description['text_3']
                                                  .isNotEmpty &&
                                              animatedText.description != null)
                                            TyperAnimatedText(animatedText
                                                .description['text_3']),
                                          if (animatedText.description['text_4']
                                                  .isNotEmpty &&
                                              animatedText.description != null)
                                            TyperAnimatedText(animatedText
                                                .description['text_4']),
                                          if (animatedText.description['text_5']
                                                  .isNotEmpty &&
                                              animatedText.description != null)
                                            TyperAnimatedText(animatedText
                                                .description['text_5']),
                                        ],
                                        onTap: () {
                                          Navigator.push(
                                              context,
                                              MaterialPageRoute(
                                                  builder: (context) =>
                                                      SearchScreen()));
                                        },
                                      ),
                                    )
                                  : DefaultTextStyle(
                                      style: TextStyle(
                                          fontSize: responsiveFont(12),
                                          color: Colors.black45),
                                      child: AnimatedTextKit(
                                        isRepeatingAnimation: true,
                                        repeatForever: true,
                                        animatedTexts: [
                                          TyperAnimatedText(
                                              AppLocalizations.of(context)!
                                                  .translate('search')!,
                                              speed:
                                                  Duration(milliseconds: 80)),
                                        ],
                                        onTap: () {
                                          Navigator.push(
                                              context,
                                              MaterialPageRoute(
                                                  builder: (context) =>
                                                      SearchScreen()));
                                        },
                                      ),
                                    ),
                            )
                          ],
                        )),
                  )),
              Container(
                width: 10.w,
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // GestureDetector(
                  //   onTap: () {
                  //     Navigator.push(
                  //         context,
                  //         MaterialPageRoute(
                  //             builder: (context) => SocmedScreen()));
                  //   },
                  //   child: Container(
                  //       width: 23.w,
                  //       child: Image.asset("images/lobby/icon-cs-app-bar.png")),
                  // ),
                  // GestureDetector(
                  //   onTap: () {
                  //     Navigator.push(context,
                  //         MaterialPageRoute(builder: (context) => WishList()));
                  //   },
                  //   child: Container(
                  //       margin: EdgeInsets.only(left: 10),
                  //       width: 27.w,
                  //       child: Image.asset("images/lobby/heart.png")),
                  // ),
                  GestureDetector(
                    onTap: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (context) => MyOrder(
                                    fromAccountScreen: false,
                                  )));
                    },
                    child: Container(
                      // w
                      // margin: EdgeInsets.symmetric(horizontal: 10),
                      width: 25.w,
                      height: 20.h,
                      child: Image.asset('images/lobby/file.png'),
                    ),
                  ),
                  SizedBox(
                    width: 7.w,
                  ),
                  Consumer<NotificationProvider>(
                    builder: (context, value, child) {
                      return Stack(
                        children: [
                          GestureDetector(
                            onTap: () {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) =>
                                          NotificationScreen()));
                            },
                            child: Container(
                                width: 25.w,
                                height: 20.h,
                                child: Image.asset('images/lobby/bell.png')),
                          ),
                          Visibility(
                            visible: value.notification.isNotEmpty &&
                                Session.data.getBool('isLogin')!,
                            child: Positioned(
                              right: 0,
                              top: 0,
                              child: Container(
                                // padding: EdgeInsets.all(3.w),
                                padding: EdgeInsets.symmetric(
                                    horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: primaryColor,
                                  shape: BoxShape.circle,
                                ),
                                child: Center(
                                  child: Text(
                                    value.notification.length > 99
                                        ? "99+"
                                        : value.unreadNotification.length
                                            .toString(),
                                    style: TextStyle(
                                        fontSize:
                                            value.unreadNotification.length > 99
                                                ? 6.h
                                                : 8.h,
                                        color: Colors.black),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      );
                    },
                  )
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget bestDealProduct() {
    final product = Provider.of<ProductProvider>(context, listen: false);

    return ListenableProvider.value(
        value: product,
        child: Consumer<ProductProvider>(builder: (context, value, child) {
          if (value.loadingBestDeals && page == 1) {
            return Container(
              padding: EdgeInsets.symmetric(horizontal: 15, vertical: 10),
              child: GridView.builder(
                  shrinkWrap: true,
                  physics: ScrollPhysics(),
                  itemCount: 6,
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisSpacing: 10,
                      mainAxisSpacing: 10,
                      crossAxisCount: 2,
                      childAspectRatio: 55 / 125),
                  itemBuilder: (context, i) {
                    return GridItemShimmer();
                  }),
            );
          }
          return Container(
            color: HexColor("EBEBEB"),
            child: Visibility(
                visible: value.listBestDeal.isNotEmpty,
                child: Column(
                  children: [
                    Container(
                      width: double.infinity,
                      margin: EdgeInsets.only(
                          left: 15, bottom: 3, right: 15, top: 3),
                      child: Text(
                        AppLocalizations.of(context)!.translate('best_deals')!,
                        style: TextStyle(
                            fontSize: responsiveFont(14),
                            fontWeight: FontWeight.w600),
                      ),
                    ),
                    Container(
                      child: MasonryGridView.count(
                        crossAxisCount: 2,
                        padding:
                            EdgeInsets.symmetric(horizontal: 15, vertical: 10),
                        mainAxisSpacing: 10,
                        crossAxisSpacing: 10,
                        shrinkWrap: true,
                        itemCount: value.listBestDeal.length,
                        primary: false,
                        // physics: NeverScrollableScrollPhysics(),
                        itemBuilder: (context, i) {
                          return GridItem(
                            i: i,
                            itemCount: value.listBestDeal.length,
                            product: value.listBestDeal[i],
                          );
                        },
                      ),
                    ),
                    if (value.loadingBestDeals && page != 1) customLoading()
                  ],
                )),
          );
        }));
  }
}
