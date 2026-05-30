import 'dart:async';
import 'dart:convert';

import 'package:animated_text_kit/animated_text_kit.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:carousel_slider/carousel_slider.dart';
import 'package:colorful_safe_area/colorful_safe_area.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_countdown_timer/current_remaining_time.dart';
import 'package:flutter_countdown_timer/flutter_countdown_timer.dart';
import 'package:flutter_rating_bar/flutter_rating_bar.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:like_button/like_button.dart';
import 'package:modal_bottom_sheet/modal_bottom_sheet.dart';
import 'package:nyoba/models/shipping_method_model.dart';
import 'package:nyoba/pages/home/home_screen.dart';
import 'package:nyoba/pages/notification/notification_screen.dart';
import 'package:nyoba/pages/order/cart_screen.dart';
import 'package:nyoba/pages/product/custom_coupon_screen.dart';
import 'package:nyoba/pages/product/page_view_review.dart';
import 'package:nyoba/pages/product/product_more_screen.dart';
import 'package:nyoba/pages/product/shipping_method_screen.dart';
import 'package:nyoba/pages/search/search_screen.dart';
import 'package:nyoba/pages/wishlist/wishlist_screen.dart';
import 'package:nyoba/provider/app_provider.dart';
import 'package:nyoba/provider/coupon_provider.dart';
import 'package:nyoba/provider/flash_sale_provider.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/notification_provider.dart';
import 'package:nyoba/provider/notify_provider.dart';
import 'package:nyoba/provider/order_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/provider/review_provider.dart';
import 'package:nyoba/provider/shipping_provider.dart';
import 'package:nyoba/provider/user_provider.dart';
import 'package:nyoba/provider/wishlist_provider.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/utils/share_link.dart';
import 'package:nyoba/widgets/container_card.dart';
import 'package:nyoba/widgets/home/card_item_small.dart';
import 'package:nyoba/widgets/home/grid_item.dart';
import 'package:nyoba/widgets/product/grid_item_shimmer.dart';
import 'package:nyoba/widgets/product/product_detail_chat.dart';
import 'package:nyoba/widgets/product/product_detail_description.dart';
import 'package:nyoba/widgets/product/product_detail_modal.dart';
import 'package:nyoba/widgets/product/product_detail_shimmer.dart';
import 'package:nyoba/widgets/product/product_detail_shipping.dart';
import 'package:nyoba/widgets/product/product_detail_specification.dart';
import 'package:nyoba/widgets/product/product_detail_variant.dart';
import 'package:nyoba/widgets/product/product_photoview.dart';
import 'package:nyoba/widgets/youtube/youtube_player.dart';
import 'package:provider/provider.dart';
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:shimmer/shimmer.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../../app_localizations.dart';
import '../../models/product_model.dart';
import '../../utils/utility.dart';
import '../../widgets/product_review/product_review_modal.dart';
import 'featured_products/all_featured_product_screen.dart';
import 'product_review_screen.dart';

class ProductDetail extends StatefulWidget {
  final String? productId;
  final String? slug;
  final bool? isFromSplashScreen;
  ProductDetail(
      {Key? key, this.productId, this.slug, this.isFromSplashScreen = false})
      : super(key: key);

  @override
  _ProductDetailState createState() => _ProductDetailState();
}

class _ProductDetailState extends State<ProductDetail>
    with TickerProviderStateMixin {
  late AnimationController _colorAnimationController;
  late AnimationController _textAnimationController;

  final overviewKey = new GlobalKey();
  final reviewKey = new GlobalKey();
  final productKey = new GlobalKey();
  final descKey = new GlobalKey();
  ValueNotifier<bool>? tab = ValueNotifier(false);
  ValueNotifier<GlobalKey> valueKey = ValueNotifier(new GlobalKey());

  int itemCount = 10;

  bool? isWishlist = false;

  int cartCount = 0;
  TextEditingController reviewController = new TextEditingController();

  double rating = 0;

  String order = 'desc';
  String orderBy = 'latest';

  int endTime = DateTime.now().millisecondsSinceEpoch + 1000 * 30;
  bool isFlashSale = false;

  ProductModel? productModel;
  final CarouselSliderController _controller = CarouselSliderController();
  int _current = 0;

  RefreshController _refreshController =
      RefreshController(initialRefresh: false);

  List<double> variantPrices = [];

  ScrollController _scrollController = new ScrollController();
  int page = 1;

  TextEditingController emailController = TextEditingController();
  Completer<WebViewController> _controllerWeb = Completer<WebViewController>();
  WebViewController? webController;
  double height = 1;

  @override
  void initState() {
    super.initState();
    final product = Provider.of<ProductProvider>(context, listen: false);
    printLog("==== 1 ${jsonEncode(product.selectedCountry)}");
    printLog("==== 2 ${jsonEncode(product.currentPosition)}");
    valueKey.value = overviewKey;
    _scrollController.addListener(() {
      if (_scrollController.position.pixels > 100) {
        tab!.value = true;
      } else if (_scrollController.position.pixels <= 100) {
        tab!.value = false;
      }
      if (_scrollController.position.pixels <= 700) {
        valueKey.value = overviewKey;
      }
      if (_scrollController.position.pixels > 700) {
        valueKey.value = reviewKey;
      }
      if (_scrollController.position.pixels >= 1020) {
        valueKey.value = productKey;
      }
      if (_scrollController.position.pixels ==
          _scrollController.position.maxScrollExtent) {
        if (product.listCategoryProduct.length % 8 == 0) {
          setState(() {
            page++;
          });
          loadLikeProduct();
        }
      }
    });
    _colorAnimationController =
        AnimationController(vsync: this, duration: Duration(seconds: 0));
    _textAnimationController =
        AnimationController(vsync: this, duration: Duration(seconds: 0));
    loadReviewAll();
    loadDetail();
    loadMoreProduct();
    WidgetsFlutterBinding.ensureInitialized()
        .addPostFrameCallback((timeStamp) async {
      context
          .read<CouponProvider>()
          .fetchCoupon(context: context, page: 1, productId: widget.productId);
      await context
          .read<ProductProvider>()
          .getShippingMethod(
              context: context,
              country: product.selectedCountry?.code ?? product.currentPosition,
              productId: widget.productId,
              qty: 1)
          .then((value) {
        if (value) {
          context
              .read<ProductProvider>()
              .setCountry(product.responseShippingCountry);
        }
      });
    });
  }

  @override
  void setState(fn) {
    if (mounted) {
      super.setState(fn);
    }
  }

  loadMoreProduct() async {
    await Provider.of<ProductProvider>(context, listen: false)
        .fetchFeaturedProducts(
            context: context, page: page, order: order, orderBy: orderBy);
    await Provider.of<FlashSaleProvider>(context, listen: false)
        .fetchFlashSale(context);
  }

  checkFlashSale() {
    final flashsale = Provider.of<FlashSaleProvider>(context, listen: false);
    if (flashsale.flashSales.isNotEmpty) {
      setState(() {
        endTime = DateTime.parse(flashsale.flashSales[0].endDate!)
            .millisecondsSinceEpoch;
      });
    }

    if (flashsale.flashSaleProducts.isNotEmpty) {
      flashsale.flashSaleProducts.forEach((element) {
        if (productModel!.id.toString() == element.id.toString()) {
          setState(() {
            isFlashSale = true;
          });
        }
      });
    }
  }

  bool scrollListener(ScrollNotification scrollInfo) {
    if (scrollInfo.metrics.axis == Axis.vertical) {
      _colorAnimationController.animateTo(scrollInfo.metrics.pixels / 350);
      _textAnimationController
          .animateTo((scrollInfo.metrics.pixels - 350) / 50);
      return true;
    } else {
      return false;
    }
  }

  Future<void> loadDetail() async {
    printLog("masuk load detail");
    final productProvider =
        Provider.of<ProductProvider>(context, listen: false);
    final shipping = Provider.of<ShippingProvider>(context, listen: false);

    loadCartCount();
    if (widget.slug == null) {
      await Provider.of<ProductProvider>(context, listen: false)
          .fetchProductDetail(widget.productId, context)
          .then((value) async {
        setState(() {
          productModel = checkDiscountRules(context, value!);
          printLog("${jsonEncode(productModel)}", name: 'Product Model');
          productModel!.isSelected = false;
        });

        if (mounted) shipping.checkShipping(context, productModel!);
        if (mounted) checkFlashSale();

        if (Session.data.getBool('isLogin')!)
          await productProvider.hitViewProducts(widget.productId, context).then(
              (value) async =>
                  await productProvider.fetchRecentProducts(context));
      });
    } else {
      await Provider.of<ProductProvider>(context, listen: false)
          .fetchProductDetailSlug(widget.slug, context)
          .then((value) {
        setState(() {
          productModel = checkDiscountRules(context, value!);
          productModel!.isSelected = false;
          productProvider.loadingDetail = false;
          printLog(productModel.toString(), name: 'Product Model');
        });
        shipping.checkShipping(context, productModel!);
        checkFlashSale();
      });
    }
    loadReviewProduct();
    if (mounted) secondLoad();
  }

  secondLoad() {
    final wishlist = Provider.of<WishlistProvider>(context, listen: false);
    if (Session.data.getBool('isLogin')!) {
      final Future<Map<String, dynamic>?> checkWishlist =
          wishlist.checkWishlistProduct(
              context: context, productId: productModel!.id.toString());

      checkWishlist.then((value) {
        printLog('Cek Wishlist Success');
        setState(() {
          isWishlist = value!['message'];
        });
      });
    }
    // loadReviewProduct();
  }

  Future<bool?> setWishlist(bool? isLiked) async {
    if (Session.data.getBool('isLogin')!) {
      setState(() {
        isWishlist = !isWishlist!;
        isLiked = isWishlist;
      });
      final wishlist = Provider.of<WishlistProvider>(context, listen: false);

      final Future<Map<String, dynamic>?> setWishlist = wishlist
          .setWishlistProduct(context, productId: productModel!.id.toString());

      setWishlist.then((value) {
        print("200");
      });
    } else {
      Navigator.push(
          context, MaterialPageRoute(builder: (context) => WishList()));
    }
    return isLiked;
  }

  Future<dynamic> loadCartCount() async {
    await Provider.of<OrderProvider>(context, listen: false)
        .loadCartCount()
        .then((value) {
      setState(() {
        cartCount = value;
      });
    });
  }

  loadReviewAll() async {
    await Provider.of<ReviewProvider>(context, listen: false)
        .fetchReviewProduct(widget.productId, context);
  }

  loadReviewProduct() async {
    if (productModel == null) {
      await Provider.of<ReviewProvider>(context, listen: false)
          .fetchReviewProductLimit(widget.productId.toString(), context)
          .then((value) => loadLikeProduct());
    } else {
      await Provider.of<ReviewProvider>(context, listen: false)
          .fetchReviewProductLimit(productModel!.id.toString(), context)
          .then((value) => loadLikeProduct());
    }
  }

  loadLikeProduct() async {
    if (mounted) {
      printLog("masuk load like product");
      await Provider.of<ProductProvider>(context, listen: false)
          .fetchCategoryProduct(productModel!.categories![0].id.toString(),
              page, 'desc', 'popularity', context);
    }
  }

  refresh() async {
    this.setState(() {});
    await loadReviewProduct();
    if (context.read<CouponProvider>().choosenIndex == null) {
      webController?.loadUrl(Uri.dataFromString(
              '${(Provider.of<CouponProvider>(context, listen: false).coupons[0].couponHtml!)}',
              mimeType: 'text/html',
              encoding: Encoding.getByName('utf-8'))
          .toString());
    } else {
      webController?.loadUrl(Uri.dataFromString(
              '${(Provider.of<CouponProvider>(context, listen: false).coupons[context.read<CouponProvider>().choosenIndex!].couponHtml!)}',
              mimeType: 'text/html',
              encoding: Encoding.getByName('utf-8'))
          .toString());
    }
    await loadDetail().then((value) {
      this.setState(() {});
      _refreshController.refreshCompleted();
    });
  }

  // loadBadges() {
  //   if (productModel?.badges != [] && productModel!.badges != null) {
  //     for (var i in productModel!.badges!) {
  //       var position = i.position!.split('-');
  //       listBadges.add(Positioned(
  //           top: position.contains('top')
  //               ? 0
  //               : position.contains('middle')
  //                   ? 50
  //                   : null,
  //           bottom: position.contains('bottom') ? 0 : null,
  //           left: position.contains('left')
  //               ? 10
  //               : position.contains("center")
  //                   ? 50
  //                   : null,
  //           right: position.contains('right') ? 10 : null,
  //           child: Container(
  //             child: Image.network(
  //               i.image!,
  //             ),
  //           )));
  //     }
  //   }
  //   printLog("load badges finish");
  // }

  @override
  void dispose() {
    super.dispose();
    _scrollController.dispose();
    tab?.dispose();
    valueKey.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final product = Provider.of<ProductProvider>(context, listen: false);
    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;
    Widget buildWishlistBtn = LikeButton(
      size: 25,
      onTap: setWishlist,
      circleColor: CircleColor(start: primaryColor, end: secondaryColor),
      bubblesColor: BubblesColor(
        dotPrimaryColor: primaryColor,
        dotSecondaryColor: secondaryColor,
      ),
      isLiked: isWishlist,
      likeBuilder: (bool isLiked) {
        if (!isLiked) {
          return Icon(
            Icons.favorite_border,
            color: Colors.grey,
            size: 25,
          );
        }
        return Icon(
          Icons.favorite,
          color: Colors.red,
          size: 25,
        );
      },
    );

    return ListenableProvider.value(
      value: product,
      child: Consumer<ProductProvider>(builder: (context, value, child) {
        if (value.loadingDetail || productModel == null) {
          return ProductDetailShimmer();
        }
        List<Widget> itemSlider = [
          Icon(
            Icons.broken_image_outlined,
            size: 80,
          )
        ];
        if (productModel != null) {
          if (productModel!.images!.isNotEmpty ||
              productModel!.videos!.isNotEmpty) {
            itemSlider = [
              if (productModel!.yith!.video != "")
                Container(
                  child: YoutubePlayerWidget(
                    url: productModel!.yith!.video,
                  ),
                ),
              InkWell(
                onTap: () {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (context) => ProductPhotoView(
                                image: productModel!.images![0].src,
                              )));
                },
                child: AspectRatio(
                  aspectRatio: 1 / 1,
                  child: CachedNetworkImage(
                    imageUrl: productModel!.images![0].src!,
                    placeholder: (context, url) => customLoading(),
                    errorWidget: (context, url, error) => Icon(
                      Icons.image_not_supported_rounded,
                      size: 25,
                    ),
                  ),
                ),
              ),
              for (var i = 1; i < productModel!.images!.length; i++)
                InkWell(
                    onTap: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (context) => ProductPhotoView(
                                    image: productModel!.images![i].src,
                                  )));
                    },
                    child: AspectRatio(
                      aspectRatio: 1 / 1,
                      child: CachedNetworkImage(
                        imageUrl: productModel!.images![i].src!,
                        placeholder: (context, url) => customLoading(),
                        errorWidget: (context, url, error) => Icon(
                          Icons.image_not_supported_rounded,
                          size: 25,
                        ),
                      ),
                    ))
            ];
          }
        }
        return ColorfulSafeArea(
          color: Colors.white,
          child: WillPopScope(
            onWillPop: () async {
              if (widget.isFromSplashScreen == true) {
                Navigator.of(context)
                    .pushReplacement(MaterialPageRoute(builder: (_) {
                  return HomeScreen();
                }));
              } else {
                Navigator.pop(context);
              }
              return true;
            },
            child: Scaffold(
              backgroundColor: HexColor("FAFAFA"),
              appBar: appBar(productModel!) as PreferredSizeWidget?,
              body: Stack(
                children: [
                  SmartRefresher(
                    controller: _refreshController,
                    scrollController: _scrollController,
                    onRefresh: refresh,
                    child: SingleChildScrollView(
                      physics: ScrollPhysics(),
                      child: Column(
                        children: [
                          ValueListenableBuilder<bool>(
                            valueListenable: tab!,
                            builder: (context, value, child) {
                              if (!value) {
                                return SizedBox.shrink();
                              }
                              return Container(
                                key: overviewKey,
                                height: 40,
                              );
                            },
                          ),
                          Stack(
                            children: [
                              CarouselSlider(
                                options: CarouselOptions(
                                    enableInfiniteScroll: false,
                                    viewportFraction: 1,
                                    aspectRatio: 1 / 1,
                                    onPageChanged: (index, reason) {
                                      setState(() {
                                        _current = index;
                                      });
                                    }),
                                carouselController: _controller,
                                items: itemSlider,
                              ),
                              Positioned(
                                  bottom: 10,
                                  right: 10,
                                  child: Container(
                                    padding:
                                        EdgeInsets.symmetric(horizontal: 5),
                                    decoration: BoxDecoration(
                                        color: Colors.black.withOpacity(0.4),
                                        borderRadius:
                                            BorderRadius.circular(10)),
                                    child: Text(
                                      "${_current + 1} / ${itemSlider.length}",
                                      style: TextStyle(
                                          color: Colors.white, fontSize: 12),
                                    ),
                                  ))
                            ],
                          ),
                          Visibility(
                              visible: isFlashSale,
                              child: Container(
                                  alignment: Alignment.center,
                                  child: CountdownTimer(
                                    endTime: endTime,
                                    widgetBuilder:
                                        (_, CurrentRemainingTime? time) {
                                      if (time == null) {
                                        return Container();
                                      } else {
                                        int? hours = time.hours ?? 0;
                                        if (time.days != null &&
                                            time.days != 0) {
                                          hours =
                                              (time.days! * 24) + time.hours!;
                                        } else if (time.hours != null) {
                                          hours = time.hours;
                                        } else if (time.hours == null) {
                                          hours = 0;
                                        } else if (time.hours == null &&
                                            time.min == null &&
                                            time.sec == null) {
                                          return Text(
                                              '${AppLocalizations.of(context)!.translate('flashsale_end')}');
                                        }
                                        return Container(
                                          width: double.infinity,
                                          height: 50,
                                          decoration: BoxDecoration(
                                              image: DecorationImage(
                                                  fit: BoxFit.cover,
                                                  image: AssetImage(
                                                      "images/product_detail/bg_flashsale.png"))),
                                          child: Row(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.center,
                                            mainAxisAlignment:
                                                MainAxisAlignment.spaceBetween,
                                            children: [
                                              Container(
                                                padding: EdgeInsets.symmetric(
                                                    horizontal: 10),
                                                child: Column(
                                                  crossAxisAlignment:
                                                      CrossAxisAlignment.start,
                                                  mainAxisAlignment:
                                                      MainAxisAlignment.center,
                                                  children: [
                                                    Text(
                                                      "${AppLocalizations.of(context)!.translate('flashsale_end_in')}",
                                                      style: TextStyle(
                                                          color: Colors.black,
                                                          fontWeight:
                                                              FontWeight.w700,
                                                          fontSize: 14),
                                                    ),
                                                    Text(
                                                        "${productModel!.totalSold} ${AppLocalizations.of(context)!.translate('item_sold')}",
                                                        style: TextStyle(
                                                            color: Colors.black,
                                                            fontSize: 10)),
                                                  ],
                                                ),
                                              ),
                                              SizedBox(
                                                  width: MediaQuery.of(context)
                                                          .size
                                                          .width -
                                                      340),
                                              Expanded(
                                                // height: 30.h,
                                                // padding: EdgeInsets.symmetric(
                                                //     horizontal: 10),
                                                child: Row(
                                                  children: [
                                                    Expanded(
                                                      child: Container(
                                                        alignment:
                                                            Alignment.center,
                                                        padding: EdgeInsets
                                                            .symmetric(
                                                                horizontal: 4,
                                                                vertical: 3),
                                                        decoration: BoxDecoration(
                                                            color: Colors.black,
                                                            borderRadius:
                                                                BorderRadius
                                                                    .circular(
                                                                        5)),
                                                        width: hours! < 100
                                                            ? 35.w
                                                            : 40.w,
                                                        height: 30.h,
                                                        child: Text(
                                                          hours < 10
                                                              ? "0$hours"
                                                              : "$hours",
                                                          textAlign:
                                                              TextAlign.center,
                                                          style: TextStyle(
                                                              color:
                                                                  primaryColor,
                                                              fontWeight:
                                                                  FontWeight
                                                                      .bold,
                                                              fontSize:
                                                                  responsiveFont(
                                                                      12)),
                                                        ),
                                                      ),
                                                    ),
                                                    Container(
                                                      margin:
                                                          EdgeInsets.symmetric(
                                                              horizontal: 5),
                                                      child: Text(
                                                        ":",
                                                        style: TextStyle(
                                                            color: Colors.black,
                                                            fontWeight:
                                                                FontWeight.w700,
                                                            fontSize:
                                                                responsiveFont(
                                                                    12)),
                                                      ),
                                                    ),
                                                    Expanded(
                                                      child: Container(
                                                        alignment:
                                                            Alignment.center,
                                                        padding:
                                                            EdgeInsets.all(3),
                                                        decoration: BoxDecoration(
                                                            color: Colors.black,
                                                            borderRadius:
                                                                BorderRadius
                                                                    .circular(
                                                                        5)),
                                                        width: 30.w,
                                                        height: 30.h,
                                                        child: Text(
                                                          time.min == null
                                                              ? "00"
                                                              : time.min! < 10
                                                                  ? "0${time.min}"
                                                                  : "${time.min}",
                                                          textAlign:
                                                              TextAlign.center,
                                                          style: TextStyle(
                                                              color:
                                                                  primaryColor,
                                                              fontWeight:
                                                                  FontWeight
                                                                      .bold,
                                                              fontSize:
                                                                  responsiveFont(
                                                                      12)),
                                                        ),
                                                      ),
                                                    ),
                                                    Container(
                                                      margin:
                                                          EdgeInsets.symmetric(
                                                              horizontal: 5),
                                                      child: Text(
                                                        ":",
                                                        style: TextStyle(
                                                            color: Colors.black,
                                                            fontWeight:
                                                                FontWeight.w700,
                                                            fontSize:
                                                                responsiveFont(
                                                                    12)),
                                                      ),
                                                    ),
                                                    Expanded(
                                                      child: Container(
                                                        alignment:
                                                            Alignment.center,
                                                        padding:
                                                            EdgeInsets.all(3),
                                                        decoration: BoxDecoration(
                                                            color: Colors.black,
                                                            borderRadius:
                                                                BorderRadius
                                                                    .circular(
                                                                        5)),
                                                        width: 30.w,
                                                        height: 30.h,
                                                        child: Text(
                                                          time.sec! < 10
                                                              ? "0${time.sec}"
                                                              : "${time.sec}",
                                                          textAlign:
                                                              TextAlign.center,
                                                          style: TextStyle(
                                                              color:
                                                                  primaryColor,
                                                              fontWeight:
                                                                  FontWeight
                                                                      .bold,
                                                              fontSize:
                                                                  responsiveFont(
                                                                      12)),
                                                        ),
                                                      ),
                                                    )
                                                  ],
                                                ),
                                              ),
                                              SizedBox(width: 10)
                                            ],
                                          ),
                                        );
                                      }
                                    },
                                  ))),
                          Container(
                              color: Colors.white,
                              child: firstPart(buildWishlistBtn)),
                          // Container(
                          //   margin: EdgeInsets.only(bottom: 15),
                          //   width: double.infinity,
                          //   height: 5,
                          //   color: HexColor("EEEEEE"),
                          // ),
                          Consumer<CouponProvider>(
                            builder: (context, value, child) => value
                                        .coupons.isEmpty &&
                                    !Provider.of<HomeProvider>(context,
                                            listen: false)
                                        .smartCoupon
                                ? Container()
                                : value.coupons.isEmpty
                                    ? Container()
                                    : Container(
                                        width:
                                            MediaQuery.of(context).size.width,
                                        height: height,
                                        // constraints: BoxConstraints(
                                        //     maxHeight: 160, minHeight: 100),
                                        child: Stack(
                                          children: [
                                            WebView(
                                              zoomEnabled: false,
                                              initialUrl: value.choosenIndex ==
                                                      null
                                                  ? Uri.dataFromString(
                                                          '${(value.coupons[0].couponHtml!)}',
                                                          mimeType: 'text/html',
                                                          encoding: Encoding
                                                              .getByName(
                                                                  'utf-8'))
                                                      .toString()
                                                  : Uri.dataFromString(
                                                          '${(value.coupons[value.choosenIndex!].couponHtml!)}',
                                                          mimeType: 'text/html',
                                                          encoding: Encoding
                                                              .getByName(
                                                                  'utf-8'))
                                                      .toString(),
                                              gestureRecognizers: Set()
                                                ..add(Factory<
                                                        VerticalDragGestureRecognizer>(
                                                    () =>
                                                        VerticalDragGestureRecognizer())),
                                              onWebViewCreated: (controller) {
                                                webController = controller;
                                                // _controllerWeb
                                                //     .complete(webController);
                                              },
                                              onPageFinished: (url) async {
                                                var x = await webController
                                                    ?.runJavascriptReturningResult(
                                                        "document.querySelector('#sc-cc').scrollHeight")
                                                    .then((value) {
                                                  return jsonDecode(value);
                                                });
                                                double? y = double.tryParse(
                                                    x.toString());
                                                printLog('parse : $y --- $x');
                                                setState(() {
                                                  height =
                                                      y != null ? y + 10 : 150;
                                                });
                                              },
                                              javascriptMode:
                                                  JavascriptMode.unrestricted,
                                            ),
                                            GestureDetector(
                                              onTap: () {
                                                Navigator.push(
                                                    context,
                                                    MaterialPageRoute(
                                                      builder: (context) =>
                                                          CustomCouponScreen(),
                                                    )).then((val) {
                                                  webController?.loadUrl(
                                                      Uri.dataFromString(
                                                              '${(value.coupons[value.choosenIndex!].couponHtml!)}',
                                                              mimeType:
                                                                  'text/html',
                                                              encoding: Encoding
                                                                  .getByName(
                                                                      'utf-8'))
                                                          .toString());
                                                  setState(() {});
                                                });
                                              },
                                              child: Container(
                                                width: MediaQuery.of(context)
                                                    .size
                                                    .width,
                                                height: 150,
                                                color: Colors.transparent,
                                              ),
                                            )
                                          ],
                                        ),
                                      ),
                          ),
                          Visibility(
                              visible: productModel!.type == 'variable',
                              child: Column(
                                children: [
                                  // Container(
                                  //   width: double.infinity,
                                  //   height: 1,
                                  //   color: HexColor("EEEEEE"),
                                  // ),
                                  ContainerCard(
                                    child: ProductDetailVariant(
                                      productModel: productModel!,
                                      loadCount: loadCartCount,
                                    ),
                                  ),
                                ],
                              )),
                          // Container(
                          //   width: double.infinity,
                          //   height: 1,
                          //   color: HexColor("EEEEEE"),
                          // ),
                          Container(
                            margin: EdgeInsets.fromLTRB(10, 10, 10, 3),
                            padding: EdgeInsets.symmetric(
                                horizontal: 10, vertical: 5),
                            width: double.infinity,
                            decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(10),
                                color: Colors.white),
                            child: ProductDetailSpecification(
                                productModel: productModel!),
                          ),
                          // ContainerCard(
                          //   child: ProductDetailSpecification(
                          //       productModel: productModel!),
                          // ),
                          // Container(
                          //   width: double.infinity,
                          //   height: 1,
                          //   color: HexColor("EEEEEE"),
                          // ),
                          Container(
                            margin: EdgeInsets.symmetric(
                                horizontal: 10, vertical: 3),
                            padding: EdgeInsets.symmetric(
                                horizontal: 10, vertical: 5),
                            width: double.infinity,
                            decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(10),
                                color: Colors.white),
                            child: ProductDetailDescription(
                              key: reviewKey,
                              productModel: productModel!,
                            ),
                          ),
                          // ContainerCard(
                          //   child:
                          // ),
                          // Container(
                          //   width: double.infinity,
                          //   height: 1,
                          //   color: HexColor("EEEEEE"),
                          // ),
                          productModel!.shippingPrice != null
                              ? Column(
                                  children: [
                                    ProductDetailShipping(
                                        productModel: productModel!),
                                    Container(
                                      margin: EdgeInsets.only(bottom: 15),
                                      width: double.infinity,
                                      height: 5,
                                      color: HexColor("EEEEEE"),
                                    ),
                                  ],
                                )
                              : Container(),
                          SizedBox(
                            height: 15,
                          ),
                          Consumer<ProductProvider>(
                            builder: (context, value, child) => value
                                            .responseShippingInfo ==
                                        "" &&
                                    value.shippingMethods.isEmpty
                                ? Container()
                                : Container(
                                    padding: EdgeInsets.only(
                                        left: 15, right: 15, bottom: 15),
                                    // height: MediaQuery.of(context).size.height /
                                    //     4.5,
                                    child: Column(
                                      mainAxisAlignment:
                                          MainAxisAlignment.start,
                                      children: [
                                        Row(
                                          mainAxisAlignment:
                                              MainAxisAlignment.spaceBetween,
                                          children: [
                                            Text(
                                              "${AppLocalizations.of(context)!.translate('choose_delivery')}",
                                              style: TextStyle(
                                                  fontSize: responsiveFont(12),
                                                  color: Colors.grey[500],
                                                  fontWeight: FontWeight.w500),
                                            ),
                                            GestureDetector(
                                              onTap: () {
                                                Navigator.push(
                                                    context,
                                                    MaterialPageRoute(
                                                      builder: (context) =>
                                                          ShippingMethodScreen(
                                                        productModel:
                                                            productModel,
                                                      ),
                                                    ));
                                              },
                                              child: Row(
                                                children: [
                                                  Icon(Icons
                                                      .location_on_outlined),
                                                  Text(
                                                      " ${AppLocalizations.of(context)!.translate('deliver_to')} ${value.selectedCountry?.name}")
                                                ],
                                              ),
                                            )
                                          ],
                                        ),
                                        SizedBox(
                                          height: 10,
                                        ),
                                        value.loadingShipping
                                            ? Shimmer.fromColors(
                                                child: Container(
                                                  width: double.infinity,
                                                  height: 40,
                                                  decoration: BoxDecoration(
                                                      borderRadius:
                                                          BorderRadius.circular(
                                                              10),
                                                      color: Colors.white),
                                                ),
                                                baseColor: Colors.grey[300]!,
                                                highlightColor:
                                                    Colors.grey[100]!)
                                            : value.responseShippingInfo != ""
                                                ? Text(
                                                    value.responseShippingInfo,
                                                    style: TextStyle(
                                                        fontWeight:
                                                            FontWeight.w600),
                                                  )
                                                : _buildShipping(value
                                                        .shippingMethods[
                                                    value.selectedShipping]),
                                      ],
                                    ),
                                  ),
                          ),
                          thirdPart(),
                          Container(
                            margin: EdgeInsets.symmetric(vertical: 15),
                            width: double.infinity,
                            height: 5,
                            color: HexColor("EEEEEE"),
                          ),
                          commentPart(),
                          SizedBox(
                            height: 15,
                          ),
                          Container(
                            width: double.infinity,
                            height: 5,
                            color: HexColor("EBEBEB"),
                          ),
                          featuredProduct(),
                          Container(
                            color: HexColor("EBEBEB"),
                            height: 15,
                          ),
                          onSaleProduct(),
                          Container(
                            color: HexColor("EBEBEB"),
                            height: 15,
                          ),
                          sameCategoryProduct(),
                          if (product.loadingBrand && page != 1)
                            customLoading(),
                          Container(
                            height: 70.h,
                            color: Colors.grey[200],
                          ),
                        ],
                      ),
                    ),
                  ),
                  ValueListenableBuilder<bool>(
                    valueListenable: tab!,
                    builder: (context, value, child) {
                      if (!value) {
                        return SizedBox.shrink();
                      }
                      return ValueListenableBuilder<GlobalKey>(
                        valueListenable: valueKey,
                        builder: (context, value, child) => Positioned(
                          top: 0,
                          right: 0,
                          left: 0,
                          child: Container(
                            width: MediaQuery.of(context).size.width,
                            height: 40,
                            padding: EdgeInsets.symmetric(
                                horizontal: 10, vertical: 10),
                            alignment: Alignment.center,
                            color: Colors.white,
                            child: ListView(
                                shrinkWrap: true,
                                physics: ScrollPhysics(),
                                scrollDirection: Axis.horizontal,
                                children: [
                                  GestureDetector(
                                    onTap: () {
                                      valueKey.value = overviewKey;
                                      Scrollable.ensureVisible(
                                          overviewKey.currentContext!,
                                          duration: Duration(seconds: 1));
                                    },
                                    child: Text(
                                      "${AppLocalizations.of(context)!.translate('overview')}",
                                      style: TextStyle(
                                          color: overviewKey == value
                                              ? Colors.black
                                              : Colors.grey,
                                          fontSize: 12,
                                          fontWeight: overviewKey == value
                                              ? FontWeight.w700
                                              : null),
                                    ),
                                  ),
                                  // SizedBox(
                                  //   width: 15,
                                  // ),
                                  // Text(
                                  //   "Specification",
                                  //   style: TextStyle(color: Colors.grey, fontSize: 12),
                                  // ),
                                  SizedBox(
                                    width: 15,
                                  ),
                                  GestureDetector(
                                    onTap: () {
                                      valueKey.value = descKey;
                                      showMaterialModalBottomSheet(
                                        context: context,
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.vertical(
                                            top: Radius.circular(12),
                                          ),
                                        ),
                                        clipBehavior:
                                            Clip.antiAliasWithSaveLayer,
                                        expand: false,
                                        backgroundColor: Theme.of(context)
                                            .colorScheme
                                            .surface,
                                        builder: (context) =>
                                            ProductDetailDescription(
                                          productModel: productModel,
                                        ).buildBodyDescription(context),
                                      );
                                    },
                                    child: Text(
                                      "${AppLocalizations.of(context)!.translate('description')}",
                                      style: TextStyle(
                                          color: descKey == value
                                              ? Colors.black
                                              : Colors.grey,
                                          fontSize: 12,
                                          fontWeight: descKey == value
                                              ? FontWeight.w700
                                              : null),
                                    ),
                                  ),
                                  SizedBox(
                                    width: 15,
                                  ),
                                  GestureDetector(
                                      onTap: () {
                                        valueKey.value = reviewKey;
                                        Scrollable.ensureVisible(
                                            reviewKey.currentContext!,
                                            duration: Duration(seconds: 1));
                                      },
                                      child: Text(
                                        "${AppLocalizations.of(context)!.translate('review')}",
                                        style: TextStyle(
                                            color: reviewKey == value
                                                ? Colors.black
                                                : Colors.grey,
                                            fontSize: 12,
                                            fontWeight: reviewKey == value
                                                ? FontWeight.w700
                                                : null),
                                      )),
                                  SizedBox(
                                    width: 15,
                                  ),
                                  GestureDetector(
                                    onTap: () {
                                      valueKey.value = productKey;
                                      Scrollable.ensureVisible(
                                          productKey.currentContext!,
                                          duration: Duration(seconds: 1));
                                    },
                                    child: Text(
                                      "${AppLocalizations.of(context)!.translate('featured_products')}",
                                      style: TextStyle(
                                          color: productKey == value
                                              ? Colors.black
                                              : Colors.grey,
                                          fontSize: 12,
                                          fontWeight: productKey == value
                                              ? FontWeight.w700
                                              : null),
                                    ),
                                  ),
                                ]),
                          ),
                        ),
                      );
                    },
                  ),
                  Align(
                    alignment: Alignment.bottomCenter,
                    child: Container(
                      padding: EdgeInsets.symmetric(horizontal: 15),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        boxShadow: <BoxShadow>[
                          BoxShadow(
                            color: Colors.black54,
                            blurRadius: 15.0,
                          )
                        ],
                      ),
                      height: 45.h,
                      width: double.infinity,
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          ProductDetailChat(productModel: productModel!),
                          SizedBox(width: 5.w),
                          Row(
                            children: [
                              Container(
                                decoration: BoxDecoration(
                                    borderRadius: locale == Locale('ar')
                                        ? BorderRadius.only(
                                            bottomRight: Radius.circular(15),
                                            topRight: Radius.circular(15))
                                        : BorderRadius.only(
                                            bottomLeft: Radius.circular(15),
                                            topLeft: Radius.circular(15),
                                          ),
                                    gradient: LinearGradient(
                                        begin: Alignment.centerLeft,
                                        end: Alignment.centerRight,
                                        colors: productModel!.stockStatus !=
                                                    'outofstock' &&
                                                productModel!.productStock! >= 1
                                            ? [
                                                HexColor("FFC200"),
                                                HexColor("FF8329")
                                              ]
                                            : [Colors.grey, Colors.grey])),
                                width: 130.w,
                                height: 30.h,
                                child: TextButton(
                                    onPressed: () {
                                      if (productModel!.stockStatus !=
                                              'outofstock' &&
                                          productModel!.productStock! >= 1) {
                                        showMaterialModalBottomSheet(
                                          context: context,
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.vertical(
                                              top: Radius.circular(12),
                                            ),
                                          ),
                                          enableDrag: false,
                                          clipBehavior:
                                              Clip.antiAliasWithSaveLayer,
                                          backgroundColor: Theme.of(context)
                                              .colorScheme
                                              .surface,
                                          builder: (context) =>
                                              ProductDetailModal(
                                                  productModel: productModel,
                                                  type: "add",
                                                  loadCount: loadCartCount),
                                        );
                                      } else {
                                        snackBar(context,
                                            message:
                                                AppLocalizations.of(context)!
                                                    .translate(
                                                        'product_out_stock')!);
                                      }
                                    },
                                    child: Text(
                                      AppLocalizations.of(context)!
                                          .translate('add_to_cart')!,
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                          fontSize: responsiveFont(9),
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold),
                                    )),
                              ),
                              Container(
                                decoration: BoxDecoration(
                                    borderRadius: locale == Locale('ar')
                                        ? BorderRadius.only(
                                            bottomLeft: Radius.circular(15),
                                            topLeft: Radius.circular(15))
                                        : BorderRadius.only(
                                            bottomRight: Radius.circular(15),
                                            topRight: Radius.circular(15),
                                          ),
                                    gradient: LinearGradient(
                                        begin: Alignment.centerLeft,
                                        end: Alignment.centerRight,
                                        colors: productModel!.stockStatus !=
                                                    'outofstock' &&
                                                productModel!.productStock! >= 1
                                            ? [
                                                HexColor("FF3000"),
                                                HexColor("FF640E")
                                              ]
                                            : [Colors.grey, Colors.grey])),
                                width: 130.w,
                                height: 30.h,
                                child: TextButton(
                                  onPressed: () {
                                    if (productModel!.stockStatus !=
                                            'outofstock' &&
                                        productModel!.productStock! >= 1) {
                                      showMaterialModalBottomSheet(
                                        context: context,
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.vertical(
                                            top: Radius.circular(12),
                                          ),
                                        ),
                                        clipBehavior:
                                            Clip.antiAliasWithSaveLayer,
                                        expand: false,
                                        backgroundColor: Theme.of(context)
                                            .colorScheme
                                            .surface,
                                        builder: (context) =>
                                            ProductDetailModal(
                                                productModel: productModel,
                                                type: "buy",
                                                loadCount: loadCartCount),
                                      );
                                    } else {
                                      snackBar(context,
                                          message: AppLocalizations.of(context)!
                                              .translate('product_out_stock')!);
                                    }
                                  },
                                  child: Text(
                                    AppLocalizations.of(context)!
                                        .translate('buy_now')!,
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                      fontSize: responsiveFont(9),
                                    ),
                                  ),
                                ),
                              )
                            ],
                          )
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }

  Widget sameCategoryProduct() {
    final product = Provider.of<ProductProvider>(context, listen: false);

    return ListenableProvider.value(
        value: product,
        child: Consumer<ProductProvider>(builder: (context, value, child) {
          if (value.loadingCategory && page == 1) {
            return Container(
              padding: EdgeInsets.symmetric(horizontal: 15),
              child: MasonryGridView.count(
                crossAxisCount: 2,
                padding: EdgeInsets.symmetric(horizontal: 15, vertical: 10),
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                shrinkWrap: true,
                itemCount: 6,
                physics: ScrollPhysics(),
                itemBuilder: (context, i) {
                  return GridItemShimmer();
                },
              ),
            );
          }
          return Visibility(
              visible: value.listCategoryProduct.isNotEmpty,
              child: Container(
                color: HexColor('EBEBEB'),
                child: Column(
                  children: [
                    Container(
                      width: double.infinity,
                      margin: EdgeInsets.only(
                          left: 15, bottom: 10, right: 15, top: 10),
                      child: Text(
                        AppLocalizations.of(context)!
                            .translate('you_might_also')!,
                        style: TextStyle(
                            fontSize: responsiveFont(14),
                            fontWeight: FontWeight.w600),
                      ),
                    ),
                    Container(
                        padding: EdgeInsets.symmetric(horizontal: 15),
                        child: MasonryGridView.count(
                          crossAxisCount: 2,
                          mainAxisSpacing: 10,
                          crossAxisSpacing: 10,
                          shrinkWrap: true,
                          itemCount: value.listCategoryProduct.length,
                          physics: ScrollPhysics(),
                          itemBuilder: (context, i) {
                            return GridItem(
                              i: i,
                              itemCount: value.listCategoryProduct.length,
                              product: value.listCategoryProduct[i],
                            );
                          },
                        )),
                    if (value.loadingCategory && page != 1) customLoading()
                  ],
                ),
              ));
        }));
  }

  Widget featuredProduct() {
    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;

    return Consumer<ProductProvider>(builder: (context, value, child) {
      if (value.loadingFeatured) {
        return customLoading();
      }
      return Visibility(
          visible: value.listFeaturedProduct.isNotEmpty,
          child: Container(
            color: HexColor("EBEBEB"),
            child: Column(
              children: [
                Container(
                  width: double.infinity,
                  margin: EdgeInsets.only(left: 15, bottom: 10, right: 15),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        AppLocalizations.of(context)!
                            .translate('featured_products')!,
                        style: TextStyle(
                            fontSize: responsiveFont(14),
                            fontWeight: FontWeight.w600),
                      ),
                      GestureDetector(
                        onTap: () {
                          Navigator.push(
                              context,
                              MaterialPageRoute(
                                  builder: (context) => AllFeaturedProducts()));
                        },
                        child: Text(
                          AppLocalizations.of(context)!.translate('more')!,
                          style: TextStyle(
                              fontSize: responsiveFont(12),
                              fontWeight: FontWeight.w600,
                              color: secondaryColor),
                        ),
                      )
                    ],
                  ),
                ),
                AspectRatio(
                  aspectRatio:
                      locale == Locale('ar') ? 3.h / 2.1.h : 3.h / 2.0.h,
                  child: ListView.separated(
                    itemCount: value.listFeaturedProduct.length,
                    scrollDirection: Axis.horizontal,
                    itemBuilder: (context, i) {
                      return CardItem(
                        product: value.listFeaturedProduct[i],
                        i: i,
                        itemCount: value.listFeaturedProduct.length,
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
            ),
          ));
    });
  }

  Widget onSaleProduct() {
    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;

    return Consumer<FlashSaleProvider>(builder: (context, value, child) {
      return Visibility(
          visible: value.flashSaleProducts.isNotEmpty,
          child: Container(
            color: HexColor("EBEBEB"),
            child: Column(
              children: [
                Container(
                  width: double.infinity,
                  margin: EdgeInsets.only(left: 15, bottom: 10, right: 15),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        "${AppLocalizations.of(context)!.translate('on_sale')}",
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
                                        include: value.flashSales[0].products,
                                        name:
                                            '${AppLocalizations.of(context)!.translate('on_sale')}',
                                      )));
                        },
                        child: Text(
                          AppLocalizations.of(context)!.translate('more')!,
                          style: TextStyle(
                              fontSize: responsiveFont(12),
                              fontWeight: FontWeight.w600,
                              color: secondaryColor),
                        ),
                      )
                    ],
                  ),
                ),
                value.loading
                    ? customLoading()
                    : AspectRatio(
                        aspectRatio:
                            locale == Locale('ar') ? 3.h / 2.1.h : 3.h / 2.0.h,
                        child: ListView.separated(
                          itemCount: value.flashSaleProducts.length,
                          scrollDirection: Axis.horizontal,
                          itemBuilder: (context, i) {
                            return CardItem(
                              product: value.flashSaleProducts[i],
                              i: i,
                              itemCount: value.flashSaleProducts.length,
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
            ),
          ));
    });
  }

  _buildShipping(ShippingMethodModel shipping) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ShippingMethodScreen(
                productModel: productModel,
              ),
            ));
      },
      child: Container(
        padding: EdgeInsets.all(8),
        margin: EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
            border: Border.all(color: Colors.grey[400]!),
            borderRadius: BorderRadius.circular(10),
            color: Colors.grey[200]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          shipping.price! > 0
              ? Text(
                  "${AppLocalizations.of(context)!.translate('delivery')}: ${stringToCurrency(shipping.price!, context)}",
                  style: TextStyle(fontWeight: FontWeight.w600),
                )
              : Text(
                  "${AppLocalizations.of(context)!.translate('free_delivery')}",
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
          HtmlWidget(
            shipping.label ?? "-",
            textStyle:
                TextStyle(fontSize: responsiveFont(8), color: Colors.black),
          ),
          Container(
            padding: EdgeInsets.all(5),
            decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(5),
                color: Colors.grey[300]),
            child: Text(
              shipping.tracking!
                  ? "${AppLocalizations.of(context)!.translate('tracking_available')}"
                  : "${AppLocalizations.of(context)!.translate('tracking_not_available')}",
              style: TextStyle(fontSize: 10),
            ),
          )
        ]),
      ),
    );
  }

  Widget thirdPart() {
    final review = Provider.of<ReviewProvider>(context, listen: false);
    final product = Provider.of<ProductProvider>(context, listen: false);
    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;
    Widget buildReviewImage = Consumer<ReviewProvider>(
      builder: (context, value, child) {
        if (value.isLoadingReview == true) {
          return customLoading();
        }
        if (value.listReviewImage.isEmpty ||
            value.listReviewImage.length == 0) {
          return Container();
        }
        return Container(
          height: 100,
          child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemBuilder: (context, index) {
                if (index == value.listReviewImage.length) {
                  return Center(
                      child: GestureDetector(
                    onTap: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (context) => ProductReview(
                                    productId: productModel!.id.toString(),
                                  )));
                    },
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                            "${AppLocalizations.of(context)!.translate('view_more')}"),
                        Icon(Icons.chevron_right_rounded)
                      ],
                    ),
                  ));
                }
                return GestureDetector(
                  onTap: () {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => PageViewReview(
                                  listReviewImage: value.listReviewImage,
                                )));
                  },
                  child: Container(
                    decoration:
                        BoxDecoration(borderRadius: BorderRadius.circular(10)),
                    width: 100,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: Image.network(
                        value.listReviewImage[index].image!,
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
                );
              },
              separatorBuilder: (context, index) => SizedBox(
                    width: 10,
                  ),
              itemCount: value.listReviewImage.length + 1),
        );
      },
    );

    Widget buildReview = Container(
      child: ListenableProvider.value(
        value: review,
        child: Consumer<ReviewProvider>(builder: (context, value, child) {
          if (value.isLoadingReview) {
            return customLoading();
          }
          if (value.listReviewLimit.isEmpty) {
            return Text(
              AppLocalizations.of(context)!.translate('empty_review_product')!,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12),
            );
          }
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  RatingBarIndicator(
                    rating: double.parse(value.listReviewLimit[0].star!),
                    itemBuilder: (context, index) => Icon(
                      Icons.star,
                      color: Colors.amber,
                    ),
                    itemCount: 5,
                    itemSize: 15,
                    direction: Axis.horizontal,
                  ),
                  SizedBox(
                    width: 10,
                  ),
                  Text(
                    "by ",
                    style: TextStyle(
                        color: HexColor("929292"), fontSize: responsiveFont(9)),
                  ),
                  Text(
                    value.listReviewLimit[0].commentAuthor!,
                    style: TextStyle(fontSize: responsiveFont(9)),
                  )
                ],
              ),
              SizedBox(
                height: 5,
              ),
              HtmlWidget(
                value.listReviewLimit[0].content!,
                textStyle: TextStyle(color: HexColor("464646"), fontSize: 10),
              ),
            ],
          );
        }),
      ),
    );

    return Container(
      margin: EdgeInsets.symmetric(horizontal: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    AppLocalizations.of(context)!.translate('review')!,
                    style: TextStyle(
                        fontSize: responsiveFont(10),
                        fontWeight: FontWeight.w500),
                  ),
                  Row(
                    children: [
                      Container(
                          width: 15.w,
                          height: 15.h,
                          child: Image.asset(
                              "images/product_detail/starGold.png")),
                      Text(
                        " ${product.productDetail!.avgRating} (${product.productDetail!.ratingCount} ${AppLocalizations.of(context)!.translate('review')})",
                        style: TextStyle(fontSize: responsiveFont(10)),
                      ),
                    ],
                  )
                ],
              ),
              GestureDetector(
                onTap: () {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (context) => ProductReview(
                                productId: productModel!.id.toString(),
                              )));
                },
                child: Row(
                  children: [
                    Text(
                      AppLocalizations.of(context)!.translate('see_all')!,
                      style: TextStyle(fontSize: responsiveFont(11)),
                    ),
                    SizedBox(
                      width: 5,
                    ),
                    locale == Locale('ar')
                        ? Icon(
                            Icons.keyboard_arrow_left,
                            size: responsiveFont(20),
                          )
                        : Icon(
                            Icons.keyboard_arrow_right,
                            size: responsiveFont(20),
                          )
                  ],
                ),
              )
            ],
          ),
          SizedBox(
            height: 10,
          ),
          buildReviewImage,
          SizedBox(
            height: 10,
          ),
          buildReview
        ],
      ),
    );
  }

  Widget commentPart() {
    final product = Provider.of<ProductProvider>(context, listen: false);

    Widget buildBtnReview = Container(
      key: productKey,
      child: ListenableProvider.value(
        value: product,
        child: Consumer<ProductProvider>(builder: (context, value, child) {
          if (value.loadAddReview) {
            return InkWell(
              onTap: null,
              child: Container(
                width: 80,
                height: 30,
                padding: EdgeInsets.symmetric(horizontal: 5, vertical: 3),
                decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(3), color: Colors.grey),
                alignment: Alignment.center,
                child: customLoading(),
              ),
            );
          }
          return InkWell(
            // onTap: () async {
            //   if (rating != 0 && reviewController.text.isNotEmpty) {
            //     FocusScopeNode currentFocus = FocusScope.of(context);

            //     if (!currentFocus.hasPrimaryFocus) {
            //       currentFocus.unfocus();
            //     }
            //     await Provider.of<ProductProvider>(context, listen: false)
            //         .addReview(context,
            //             productId: productModel!.id,
            //             rating: rating,
            //             review: reviewController.text)
            //         .then((value) {
            //       setState(() {
            //         reviewController.clear();
            //         rating = 0;
            //       });
            //       loadReviewProduct();
            //     });
            //   } else {
            //     snackBar(context,
            //         message: 'You must set the rating and review first');
            //   }
            // },
            child: Container(
              width: 80,
              height: 30,
              padding: EdgeInsets.symmetric(horizontal: 5, vertical: 3),
              decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(3),
                  color: rating != 0 && reviewController.text.isNotEmpty
                      ? secondaryColor
                      : Colors.grey),
              alignment: Alignment.center,
              child: Text(
                "${AppLocalizations.of(context)!.translate('submit')}"
                    .toUpperCase(),
                style: TextStyle(
                    fontSize: responsiveFont(10),
                    fontWeight: FontWeight.w700,
                    color: Colors.white),
              ),
            ),
          );
        }),
      ),
    );

    return Container(
      margin: EdgeInsets.symmetric(horizontal: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            AppLocalizations.of(context)!.translate('add_review')!,
            style: TextStyle(
                fontSize: responsiveFont(12), fontWeight: FontWeight.w500),
          ),
          SizedBox(
            height: 10,
          ),
          Text(
            AppLocalizations.of(context)!.translate('comment')!,
            style: TextStyle(
                fontSize: responsiveFont(10), fontWeight: FontWeight.w400),
          ),
          SizedBox(
            height: 5,
          ),
          GestureDetector(
            onTap: () {
              showMaterialModalBottomSheet(
                context: context,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.vertical(
                    top: Radius.circular(12),
                  ),
                ),
                clipBehavior: Clip.antiAliasWithSaveLayer,
                backgroundColor: Theme.of(context).colorScheme.surface,
                builder: (context) =>
                    ProductReviewModal(rating: rating, product: productModel),
              ).then((value) => context.read<ProductProvider>().resetReview());
            },
            child: TextField(
              controller: reviewController,
              maxLines: 2,
              enabled: false,
              style: TextStyle(
                fontSize: 10,
              ),
              onChanged: (value) {
                setState(() {});
              },
              decoration: InputDecoration(
                disabledBorder: OutlineInputBorder(
                    borderSide: new BorderSide(color: Colors.grey)),
                border: OutlineInputBorder(
                    borderSide: new BorderSide(color: primaryColor)),
                hintText:
                    AppLocalizations.of(context)!.translate('hint_review'),
                hintStyle: TextStyle(fontSize: 10, color: HexColor('9e9e9e')),
              ),
              textInputAction: TextInputAction.done,
            ),
          ),
          SizedBox(
            height: 10,
          ),
          RatingBar.builder(
            initialRating: rating,
            minRating: 1,
            direction: Axis.horizontal,
            allowHalfRating: false,
            itemCount: 5,
            itemSize: 25,
            itemBuilder: (context, _) => Icon(
              Icons.star,
              color: Colors.amber,
            ),
            onRatingUpdate: (value) {
              print(value);
              setState(() {
                rating = value;
              });
              showMaterialModalBottomSheet(
                context: context,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.vertical(
                    top: Radius.circular(12),
                  ),
                ),
                clipBehavior: Clip.antiAliasWithSaveLayer,
                backgroundColor: Theme.of(context).colorScheme.surface,
                builder: (context) =>
                    ProductReviewModal(rating: rating, product: productModel),
              ).then((value) => context.read<ProductProvider>().resetReview());
            },
          ),
          SizedBox(
            height: 10,
          ),
          buildBtnReview
        ],
      ),
    );
  }

  Widget secondPart(ProductModel model) {
    return Container(
      margin: EdgeInsets.symmetric(horizontal: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            AppLocalizations.of(context)!.translate('description')!,
            style: TextStyle(
                fontSize: responsiveFont(12), fontWeight: FontWeight.w500),
          ),
          SizedBox(
            height: 5,
          ),
          HtmlWidget(
            model.productDescription!,
            textStyle: TextStyle(color: HexColor("929292")),
          ),
        ],
      ),
    );
  }

  Widget firstPart(Widget btnFav) {
    final user = Provider.of<UserProvider>(context, listen: false).user;
    final notifyMe = Provider.of<NotifyProvider>(context, listen: false);
    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;
    return Container(
      margin: EdgeInsets.only(left: 15, right: 15, top: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              productModel!.type == 'simple'
                  ? Row(
                      children: [
                        RichText(
                          text: TextSpan(
                            style: TextStyle(color: Colors.black),
                            children: <TextSpan>[
                              TextSpan(
                                  text: stringToCurrency(
                                      productModel!.productPrice!, context),
                                  style: TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: responsiveFont(15),
                                      color: Colors.black)),
                            ],
                          ),
                        ),
                        Visibility(
                          visible: productModel?.discProduct != 0,
                          child: Row(
                            children: [
                              SizedBox(
                                width: 5,
                              ),
                              RichText(
                                text: TextSpan(
                                  style: TextStyle(color: Colors.black),
                                  children: <TextSpan>[
                                    TextSpan(
                                        text: stringToCurrency(
                                            double.parse(
                                                productModel!.productRegPrice),
                                            context),
                                        style: TextStyle(
                                            decoration:
                                                TextDecoration.lineThrough,
                                            decorationColor: primaryColor,
                                            fontSize: responsiveFont(12),
                                            color: HexColor("C4C4C4"))),
                                  ],
                                ),
                              ),
                              SizedBox(
                                width: 5,
                              ),
                              Container(
                                padding: EdgeInsets.symmetric(
                                    horizontal: 5, vertical: 3),
                                child: Row(
                                  children: [
                                    Text(
                                      "${productModel?.discProduct!.round()}%",
                                      style: TextStyle(
                                          fontSize: responsiveFont(12),
                                          fontWeight: FontWeight.w500,
                                          color: Colors.black),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    )
                  : Row(
                      children: [
                        RichText(
                          text: TextSpan(
                            style: TextStyle(color: Colors.black),
                            children: <TextSpan>[
                              productModel!.variationPrices!.isEmpty
                                  ? TextSpan(
                                      text: '',
                                      style: TextStyle(
                                          fontWeight: FontWeight.w600,
                                          fontSize: responsiveFont(11),
                                          color: secondaryColor))
                                  : productModel!
                                          .variationPricesDisc!.isNotEmpty
                                      ? TextSpan(
                                          text:
                                              '${stringToCurrency(productModel!.variationPricesDisc!.first, context)}',
                                          style: TextStyle(
                                              fontWeight: FontWeight.w600,
                                              fontSize: responsiveFont(15),
                                              color: Colors.black))
                                      : TextSpan(
                                          text:
                                              '${stringToCurrency(productModel!.variationPrices!.first, context)}',
                                          style: TextStyle(
                                              fontWeight: FontWeight.w600,
                                              fontSize: responsiveFont(15),
                                              color: Colors.black)),
                            ],
                          ),
                        ),
                        Visibility(
                          visible: productModel?.discProduct != 0,
                          child: Row(
                            children: [
                              SizedBox(
                                width: 5,
                              ),
                              RichText(
                                text: TextSpan(
                                  style: TextStyle(color: Colors.black),
                                  children: <TextSpan>[
                                    TextSpan(
                                        text: productModel!
                                                .variationPrices!.isEmpty
                                            ? ""
                                            : stringToCurrency(
                                                productModel!
                                                    .variationPrices!.first,
                                                context),
                                        style: TextStyle(
                                            decoration:
                                                TextDecoration.lineThrough,
                                            decorationColor: primaryColor,
                                            fontSize: responsiveFont(12),
                                            color: HexColor("C4C4C4"))),
                                  ],
                                ),
                              ),
                              SizedBox(
                                width: 5,
                              ),
                              Container(
                                padding: EdgeInsets.symmetric(
                                    horizontal: 5, vertical: 3),
                                child: Row(
                                  children: [
                                    Text(
                                      "${productModel?.discProduct!.round()}%",
                                      style: TextStyle(
                                          fontSize: responsiveFont(12),
                                          fontWeight: FontWeight.w500,
                                          color: Colors.black),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
              btnFav
            ],
          ),
          SizedBox(
            height: 5,
          ),
          Text(
            productModel!.productName!,
            style: TextStyle(fontSize: responsiveFont(11)),
          ),
          SizedBox(
            height: 10,
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Row(
                    children: [
                      RatingBarIndicator(
                        rating: double.parse(productModel!.avgRating!),
                        itemBuilder: (context, index) => Icon(
                          Icons.star,
                          color: Colors.amber,
                        ),
                        itemCount: 5,
                        itemSize: 15,
                        direction: Axis.horizontal,
                      ),
                      Text(
                        " ${double.parse(productModel!.avgRating!).toStringAsFixed(1)}",
                        style: TextStyle(fontSize: responsiveFont(10)),
                      ),
                    ],
                  ),
                  Container(
                    margin: EdgeInsets.symmetric(horizontal: 10),
                    height: 11,
                    width: 2,
                    color: Colors.grey[300],
                  ),
                  Text(
                    "${productModel!.totalSold} ${AppLocalizations.of(context)!.translate('sold')}",
                    style: TextStyle(fontSize: responsiveFont(10)),
                  ),
                ],
              ),
              Visibility(
                  visible: productModel?.brand != "",
                  child: Image.network(
                    productModel?.brand ?? "",
                    width: 50.w,
                  ))
            ],
          ),
          SizedBox(
            height: 10,
          ),
          Row(
            children: [
              Text(
                productModel!.stockStatus == 'instock'
                    ? '${AppLocalizations.of(context)!.translate('available')}'
                    : '${AppLocalizations.of(context)!.translate('out_stock')}',
                style: TextStyle(
                    fontSize: responsiveFont(11),
                    fontWeight: FontWeight.bold,
                    color: productModel!.stockStatus == 'instock'
                        ? Colors.green
                        : Colors.red),
              ),
              SizedBox(
                width: 10.w,
              ),
              // productModel!.yith!.text != ""
              //     ? Container(
              //         padding:
              //             EdgeInsets.symmetric(horizontal: 7.w, vertical: 0),
              //         decoration: BoxDecoration(
              //             color: primaryColor,
              //             borderRadius: BorderRadius.only(
              //                 topLeft: Radius.circular(7),
              //                 bottomLeft: Radius.circular(7),
              //                 bottomRight: Radius.circular(7))),
              //         child: Text(
              //           "${productModel!.yith!.text}",
              //           style: TextStyle(fontWeight: FontWeight.w500),
              //         ))
              //     : SizedBox(),
              Visibility(
                visible:
                    productModel?.badges != [] && productModel!.badges != null,
                child: Row(
                  children: [
                    for (var i in productModel!.badges!)
                      Row(
                        children: [
                          Image.network(
                            i.image!,
                            width: 70.w,
                          ),
                          SizedBox(
                            width: 5.w,
                          )
                        ],
                      )
                  ],
                ),
              )
            ],
          ),
          SizedBox(
            height: 10.h,
          ),
          productModel!.stockStatus == 'instock'
              ? SizedBox()
              : InkWell(
                  onTap: () async {
                    if (Session.data.getBool('isLogin') == true) {
                      printLog("${Session.data.getBool('isLogin')}",
                          name: "login");
                      printLog("masuk login");
                      await Provider.of<NotifyProvider>(context, listen: false)
                          .fetchNotifyme(
                              context: context,
                              name: "${user.firstname} ${user.lastname}",
                              email: "${user.email}",
                              productId: productModel!.id.toString());
                      final snackBar = SnackBar(
                        content: Text(notifyMe.isNotifySucceed
                            ? "${AppLocalizations.of(context)!.translate('notify_succees')}"
                            : "${AppLocalizations.of(context)!.translate('notify_failed')}"),
                        backgroundColor: secondaryColor,
                      );
                      ScaffoldMessenger.of(context).showSnackBar(snackBar);
                    } else {
                      showDialog(
                        context: context,
                        builder: (ctx) => AlertDialog(
                          content: Container(
                            height: 150.h,
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                SizedBox(
                                  height: 10.h,
                                ),
                                Text(
                                    "${AppLocalizations.of(context)!.translate('enter_email')}"),
                                TextField(
                                  decoration: InputDecoration(
                                      contentPadding: EdgeInsets.zero),
                                  controller: emailController,
                                ),
                                SizedBox(
                                  height: 30.h,
                                ),
                                Center(
                                  child: InkWell(
                                      onTap: () async {
                                        if (emailController.text != "") {
                                          Navigator.of(context).pop();
                                          await Provider.of<NotifyProvider>(
                                                  context,
                                                  listen: false)
                                              .fetchNotifyme(
                                                  context: context,
                                                  name: "Guest",
                                                  email: emailController.text,
                                                  productId: productModel!.id
                                                      .toString());
                                          emailController.text = "";
                                          final snackBar = SnackBar(
                                            content: Text(notifyMe
                                                    .isNotifySucceed
                                                ? "${AppLocalizations.of(context)!.translate('notify_succees')}"
                                                : "${AppLocalizations.of(context)!.translate('notify_failed')}"),
                                            backgroundColor: secondaryColor,
                                          );
                                          ScaffoldMessenger.of(context)
                                              .showSnackBar(snackBar);
                                        } else {
                                          Navigator.of(context).pop();
                                          final snackBar = SnackBar(
                                            content: Text(
                                                "${AppLocalizations.of(context)!.translate('email_snackbar')}"),
                                            backgroundColor: secondaryColor,
                                          );
                                          ScaffoldMessenger.of(context)
                                              .showSnackBar(snackBar);
                                        }
                                      },
                                      child: Container(
                                        decoration: BoxDecoration(
                                          borderRadius:
                                              BorderRadius.circular(10),
                                          color: secondaryColor,
                                        ),
                                        width: 80.w,
                                        height: 30.h,
                                        child: Center(
                                          child: Text(
                                            "${AppLocalizations.of(context)!.translate('notify_me')}",
                                            style: TextStyle(
                                                fontSize: locale == Locale('ar')
                                                    ? responsiveFont(7)
                                                    : responsiveFont(11),
                                                color: Colors.white),
                                          ),
                                        ),
                                      )),
                                )
                              ],
                            ),
                          ),
                        ),
                      );
                    }
                  },
                  child: Container(
                    height: 30.h,
                    width: 100.w,
                    decoration: BoxDecoration(
                      color: secondaryColor,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Center(
                      child: Text(
                        "${AppLocalizations.of(context)!.translate('notify_me')}",
                        style: TextStyle(
                          fontSize: locale == Locale('ar')
                              ? responsiveFont(7)
                              : responsiveFont(11),
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ),
          Visibility(
            visible: productModel!.productShortDesc != "",
            child: SizedBox(
              height: 10,
            ),
          ),
          HtmlWidget(
            productModel!.productShortDesc!,
            textStyle: TextStyle(
                color: HexColor("929292"), fontSize: responsiveFont(10)),
          ),
        ],
      ),
    );
  }

  Widget appBar(ProductModel model) {
    final animatedText =
        Provider.of<HomeProvider>(context, listen: false).searchBarText;

    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;
    return AppBar(
      elevation: 0,
      backgroundColor: HexColor("#FFFFFF"),
      surfaceTintColor: Colors.transparent,
      leading: IconButton(
        onPressed: () {
          if (widget.isFromSplashScreen == true) {
            Navigator.of(context)
                .pushReplacement(MaterialPageRoute(builder: (_) {
              return HomeScreen();
            }));
          } else {
            Navigator.pop(context);
          }
        },
        icon: Icon(
          Icons.arrow_back,
          color: Colors.black,
        ),
      ),
      title: InkWell(
        onTap: () {
          Navigator.push(
              context, MaterialPageRoute(builder: (context) => SearchScreen()));
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
                                  speed: Duration(milliseconds: 80)),
                              if (animatedText
                                      .description['text_1'].isNotEmpty &&
                                  animatedText.description != null)
                                TyperAnimatedText(
                                    animatedText.description['text_1']),
                              if (animatedText
                                      .description['text_2'].isNotEmpty &&
                                  animatedText.description != null)
                                TyperAnimatedText(
                                    animatedText.description['text_2']),
                              if (animatedText
                                      .description['text_3'].isNotEmpty &&
                                  animatedText.description != null)
                                TyperAnimatedText(
                                    animatedText.description['text_3']),
                              if (animatedText
                                      .description['text_4'].isNotEmpty &&
                                  animatedText.description != null)
                                TyperAnimatedText(
                                    animatedText.description['text_4']),
                              if (animatedText
                                      .description['text_5'].isNotEmpty &&
                                  animatedText.description != null)
                                TyperAnimatedText(
                                    animatedText.description['text_5']),
                            ],
                            onTap: () {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) => SearchScreen()));
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
                                  speed: Duration(milliseconds: 80)),
                            ],
                            onTap: () {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) => SearchScreen()));
                            },
                          ),
                        ),
                ),
              ],
            )),
      ),
      actions: [
        Consumer<NotificationProvider>(
          builder: (context, value, child) {
            return GestureDetector(
              onTap: () {
                Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (context) => NotificationScreen()));
              },
              child: Container(
                width: 43,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Container(
                        width: 43,
                        height: 65,
                        child: Icon(
                          Icons.notifications,
                          color: Colors.black,
                          size: 28,
                        )),
                    Visibility(
                      visible: value.notification.isNotEmpty &&
                          Session.data.getBool('isLogin')!,
                      child: Positioned(
                        right: 0,
                        top: 5,
                        child: Container(
                          padding:
                              EdgeInsets.symmetric(vertical: 3, horizontal: 3),
                          decoration: BoxDecoration(
                            color: primaryColor,
                            shape: BoxShape.circle,
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            value.notification.length > 99
                                ? "99+"
                                : value.unreadNotification.length.toString(),
                            style: TextStyle(
                                fontSize: value.unreadNotification.length > 99
                                    ? responsiveFont(6)
                                    : responsiveFont(8),
                                color: Colors.black),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
        InkWell(
          onTap: () {
            Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (context) => CartScreen(
                          isFromHome: false,
                        )));
          },
          child: Container(
            width: 50,
            padding: EdgeInsets.symmetric(horizontal: 8),
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 50,
                  height: 65,
                  child: Icon(
                    Icons.shopping_cart,
                    color: Colors.black,
                  ),
                ),
                Positioned(
                  right: 0,
                  top: 4,
                  child: Container(
                    padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                        shape: BoxShape.circle, color: primaryColor),
                    alignment: Alignment.center,
                    child: Text(
                      cartCount.toString(),
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.black,
                        fontSize: responsiveFont(9),
                      ),
                    ),
                  ),
                )
              ],
            ),
          ),
        ),
        InkWell(
          onTap: () {
            shareLinks('product', model.link);
          },
          child: Container(
            margin: locale == Locale('ar')
                ? EdgeInsets.only(left: 15)
                : EdgeInsets.only(right: 15),
            child: Icon(
              Icons.share,
              color: Colors.black,
            ),
          ),
        )
      ],
    );
  }

  Widget itemList(
      String title, String discount, String price, String crossedPrice, int i) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
            context, MaterialPageRoute(builder: (context) => ProductDetail()));
      },
      child: Container(
        margin: EdgeInsets.only(
            left: i == 0 ? 15 : 0, right: i == itemCount - 1 ? 15 : 0),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(5)),
        width: MediaQuery.of(context).size.width / 3,
        height: double.infinity,
        child: Card(
          elevation: 5,
          margin: EdgeInsets.only(bottom: 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 4,
                child: Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.only(
                        topRight: Radius.circular(5),
                        topLeft: Radius.circular(5)),
                    color: primaryColor,
                  ),
                  child: Image.asset("images/lobby/laptop.png"),
                ),
              ),
              Expanded(
                  flex: 3,
                  child: Container(
                    margin: EdgeInsets.symmetric(vertical: 3, horizontal: 5),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Flexible(
                          flex: 3,
                          child: Text(
                            title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(fontSize: responsiveFont(10)),
                          ),
                        ),
                        Container(
                          height: 5,
                        ),
                        Flexible(
                          flex: 1,
                          child: Container(
                            child: Text(
                              price,
                              style: TextStyle(
                                  fontSize: responsiveFont(10),
                                  color: secondaryColor,
                                  fontWeight: FontWeight.w600),
                            ),
                          ),
                        ),
                        Container(
                          height: 5,
                        ),
                      ],
                    ),
                  )),
            ],
          ),
        ),
      ),
    );
  }
}
