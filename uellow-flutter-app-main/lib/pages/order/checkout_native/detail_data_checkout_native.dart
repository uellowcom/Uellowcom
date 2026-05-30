import 'dart:convert';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:colorful_safe_area/colorful_safe_area.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/models/cart_model.dart';
import 'package:nyoba/pages/order/checkout_native/address_checkout_native.dart';
import 'package:nyoba/pages/order/checkout_native/payment_method_screen.dart';
import 'package:nyoba/provider/checkout_provider.dart';
import 'package:nyoba/widgets/container_card.dart';
import 'package:provider/provider.dart';

import '../../../app_localizations.dart';
import '../../../models/checkout_data_model.dart';
import '../../../models/coupon_model.dart';
import '../../../provider/app_provider.dart';
import '../../../provider/coupon_provider.dart';
import '../../../provider/order_provider.dart';
import '../../../provider/wallet_provider.dart';
import '../../../services/session.dart';
import '../../../utils/currency_format.dart';
import '../../../utils/utility.dart';
import '../../../widgets/webview/checkout_webview.dart';
import '../coupon_screen.dart';
import '../order_success_screen.dart';

class DetailDataCheckoutNative extends StatefulWidget {
  final List<CartProductItem> line;
  final CartModel cart;
  final bool? isFromBuyNow;
  final Future<dynamic> Function()? removeOrderedItems;

  const DetailDataCheckoutNative(
      {super.key,
      required this.line,
      required this.cart,
      this.isFromBuyNow = false,
      this.removeOrderedItems});

  @override
  State<DetailDataCheckoutNative> createState() =>
      _DetailDataCheckoutNativeState();
}

class _DetailDataCheckoutNativeState extends State<DetailDataCheckoutNative> {
  CheckoutProvider? checkoutProvider;
  AppNotifier? appNotifier;

  bool chooseShipping = false;
  int qtyTotal = 0;
  String coupon = "";
  List<Map<String, dynamic>> coupons = [];
  double couponMount = 0;
  double shipCost = 0;
  bool payWithWallet = false;
  bool isWallet = false;
  double wallet = 0;
  double total = 0;
  bool payWithPoint = false;

  int indexSelectedPayment = 0;
  String? choosenPaymentMethod, choosenPaymentMethodTitle;

  List<SearchCouponModel> products = [];
  List<String> billing = [];

  @override
  void initState() {
    // TODO: implement initState
    super.initState();
    printLog("line : ${jsonEncode(widget.line)}");
    printLog("cart : ${jsonEncode(widget.cart)}");
    checkoutProvider = Provider.of<CheckoutProvider>(context, listen: false);
    appNotifier = Provider.of<AppNotifier>(context, listen: false);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      loadData();
    });
    for (int i = 0; i < widget.line.length; i++) {
      qtyTotal += widget.line[i].quantity!;
    }
  }

  loadData() async {
    coupons.clear();
    final couponP = Provider.of<CouponProvider>(context, listen: false);
    final checkoutP = Provider.of<CheckoutProvider>(context, listen: false);
    setState(() {
      if (couponP.couponUsed != null) {
        if (couponP.couponUsed!.discountType == "percent") {
          couponMount = checkoutP.subTotal! *
              (double.parse(couponP.couponUsed!.amount.toString()) / 100);
          printLog("${checkoutP.subTotal} - ${couponP.couponUsed!.amount}");
          printLog("coupon mount: $couponMount");
        } else {
          couponMount = double.parse(couponP.couponUsed!.amount.toString());
        }
        coupon = Provider.of<CouponProvider>(context, listen: false)
            .couponUsed!
            .code!;
        coupons.add({"code": coupon});
      }
    });
    String countryId = Session.data.getString("country_id") ?? "";
    String stateId = Session.data.getString("state_id") ?? "";
    String postcode = Session.data.getString("postcode") ?? "";
    String city = Session.data.getString("city") ?? "";
    String subdistrict = Session.data.getString("subdistrict") ?? "";
    await Provider.of<CheckoutProvider>(context, listen: false)
        .getCheckoutData(
            context: context,
            line: widget.line,
            countryId: countryId,
            postcode: postcode,
            stateId: stateId,
            city: city,
            subdistrict: subdistrict)
        .then((value) {
      getProductCart();
      Provider.of<CheckoutProvider>(context, listen: false)
          .calculateTotal(
        disc: couponMount,
        wallet: wallet,
        isWallet: payWithWallet,
      )
          .then((value) {
        wallet = double.parse(
            Provider.of<WalletProvider>(context, listen: false).walletBalance!);
        total =
            Provider.of<CheckoutProvider>(context, listen: false).grandTotal!;
        if (wallet >= total) {
          isWallet = true;
        } else if (wallet == 0) {
          isWallet = true;
        }
        if (!Session.data.getBool("isLogin")!) {
          isWallet = true;
        }
        context.read<CheckoutProvider>().checkPoin(coupon: couponMount);
        printLog(wallet.toString(), name: "wallet");
      });
    });
    printLog(isWallet.toString(), name: "wallet");
    printLog("ship : ${json.encode(checkoutProvider!.shiped)}");
    printLog("payment : ${json.encode(checkoutProvider!.payment)}");
    codCondition();
  }

  codCondition() {
    List<bool> isContainNotSupportCOD = [];
    widget.line.forEach((element) {
      printLog("cod: ${element.codPayment}");
      if (element.codPayment == true) {
        isContainNotSupportCOD.add(true);
      } else {
        isContainNotSupportCOD.add(false);
      }
    });

    printLog("is contain cod: $isContainNotSupportCOD");
    if (!isContainNotSupportCOD.contains(true)) {
      List<PaymentMethod> listPaymentMethod =
          context.read<CheckoutProvider>().paymentMethods;
      listPaymentMethod
          .removeWhere((element) => element.title == "Cash on delivery");
      context
          .read<CheckoutProvider>()
          .removeCOD(listPaymentMethod: listPaymentMethod);
    }
  }

  Future<void> getProductCart() async {
    products.clear();
    if (checkoutProvider!.lineItems != null) {
      for (int i = 0; i < checkoutProvider!.lineItems.length; i++) {
        products.add(SearchCouponModel(
            id: checkoutProvider!.lineItems[i].productId,
            quantity: checkoutProvider!.lineItems[i].qty,
            variationId: checkoutProvider!.lineItems[i].variantId));
      }
    }
  }

  // loadData() async {
  //   await Provider.of<CheckoutProvider>(context, listen: false).getCheckoutData(
  //     city: widget.city,
  //     countryId: widget.countryId,
  //     line: widget.line,
  //     postcode: widget.postCode,
  //     stateId: widget.stateId,
  //     subdistrict: widget.subdistrict,
  //   );
  // }

  Future onFinishBuyNow() async {
    await Navigator.pushReplacement(
        context, MaterialPageRoute(builder: (context) => OrderSuccess()));
  }

  placeOrder() async {
    final couponProvider = Provider.of<CouponProvider>(context, listen: false);

    CartModel cart = widget.cart;
    cart.listItem = [];

    for (var i in widget.line) {
      printLog("${i.a2wShipping}", name: "a2wshipping");
      if (i.a2wShipping != null &&
          i.a2wShipping != [] &&
          i.a2wShipping!.isNotEmpty) {
        printLog("masuk if");
        printLog("${i.a2wShipping}", name: "a2wshipping");
        cart.listItem?.add(CartProductItem(
            productId: i.productId,
            quantity: i.quantity,
            variationId: i.variationId,
            a2wShippingMethod: i.a2wShipping![0]['method'],
            a2wShipping: []));
      } else {
        printLog("masuk else");
        cart.listItem?.add(CartProductItem(
            productId: i.productId,
            quantity: i.quantity,
            variationId: i.variationId,
            a2wShippingMethod: "",
            a2wShipping: []));
      }
      // cart.listItem?.add(CartProductItem(
      //     productId: i.productId,
      //     quantity: i.quantity,
      //     variationId: i.variationId,
      //     a2wShippingMethod: "",
      //     a2wShipping: []));
    }
    //init list coupon
    cart.listCoupon = [];

    if (couponProvider.couponUsed != null) {
      cart.listCoupon!
          .add(new CartCoupon(code: couponProvider.couponUsed!.code));
    }

    //Encode Json
    final jsonOrder = json.encode(cart);
    printLog(jsonOrder, name: 'Json Order');

    //Convert Json to bytes
    var bytes = utf8.encode(jsonOrder);

    //Convert bytes to base64
    var order = base64.encode(bytes);

    await Provider.of<OrderProvider>(context, listen: false)
        .checkout(order, context)
        .then((value) async {
      printLog(value, name: 'Link Order');
      await Navigator.push(
          context,
          MaterialPageRoute(
              builder: (context) => CheckoutWebView(
                    url: value,
                    // onFinish: onFinishBuyNow,
                    onFinish: widget.removeOrderedItems, fromOrder: true,
                  )));
    });
  }

  @override
  Widget build(BuildContext context) {
    final grandTotal = Provider.of<CheckoutProvider>(
      context,
    ).grandTotal;
    return WillPopScope(
      onWillPop: () async {
        if (widget.isFromBuyNow == true) {
          Provider.of<CouponProvider>(context, listen: false).couponUsed = null;
          Navigator.pop(context);
        } else {
          Navigator.pop(context);
        }
        return true;
      },
      child: ColorfulSafeArea(
        color: Colors.white,
        child: Scaffold(
          backgroundColor: Colors.grey[200],
          appBar: AppBar(
            leading: GestureDetector(
              onTap: () {
                if (widget.isFromBuyNow == true) {
                  Provider.of<CouponProvider>(context, listen: false)
                      .couponUsed = null;
                }
                Navigator.pop(context);
              },
              child: Directionality(
                textDirection: TextDirection.ltr,
                child: Icon(
                  Session.data.getString('language_code') == 'ar'
                      ? Icons.arrow_forward_ios_outlined
                      : Icons.arrow_back_ios_new_outlined,
                  color: Colors.black,
                ),
              ),
            ),
            centerTitle: true,
            elevation: 0,
            title: Text(
              "${AppLocalizations.of(context)!.translate('place_order')}",
              style: TextStyle(color: Colors.black),
            ),
            backgroundColor: Colors.white,
          ),
          body: Column(
            children: [
              Expanded(child: Consumer<CheckoutProvider>(
                builder: (context, value, child) {
                  if (value.loading) {
                    return customLoading();
                  }
                  return ListView(
                    children: [
                      buildAddressCard(),
                      ContainerCard(child: listProduct()),
                      Visibility(
                        visible: Session.data.getBool('isLogin')! &&
                            (grandTotal! > wallet) &&
                            wallet != 0,
                        child: ContainerCard(
                          child: Row(children: [
                            Checkbox(
                              value: payWithWallet,
                              activeColor: primaryColor,
                              onChanged: (value) {
                                Provider.of<CheckoutProvider>(context,
                                        listen: false)
                                    .calculateTotal(
                                  disc: couponMount,
                                  wallet: wallet,
                                  isWallet: value,
                                );
                                setState(() {
                                  payWithWallet = value!;
                                });
                              },
                            ),
                            Text(
                              '${AppLocalizations.of(context)!.translate('pay_by_wallet')} (${AppLocalizations.of(context)!.translate('balance')} ${stringToCurrency(wallet, context)})',
                              style: TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ]),
                        ),
                      ),
                      ContainerCard(child: buildSummary()),
                      ContainerCard(
                        child: Column(
                          children: [
                            Align(
                              alignment: Alignment.centerLeft,
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.payment_outlined,
                                    size: 20,
                                  ),
                                  SizedBox(
                                    width: 10,
                                  ),
                                  Text(
                                    "Safe Payments",
                                    style: TextStyle(
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            SizedBox(
                              height: 10,
                            ),
                            SizedBox(
                              height: 40,
                              child: ListView.separated(
                                shrinkWrap: true,
                                scrollDirection: Axis.horizontal,
                                itemCount: value.paymentMethods.length,
                                itemBuilder: (context, index) {
                                  return CachedNetworkImage(
                                    imageUrl:
                                        value.paymentMethods[index].image!,
                                    width: 50,
                                    height: 30,
                                    errorWidget: (context, url, error) => Icon(
                                      Icons.image_not_supported_rounded,
                                      size: 25,
                                    ),
                                  );
                                },
                                separatorBuilder: (context, index) => SizedBox(
                                  width: 10,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  );
                },
              )),
              Align(
                  alignment: FractionalOffset.bottomCenter,
                  child: buildBottomBarCart())
            ],
          ),
        ),
      ),
    );
  }

  Widget listProduct() {
    List<LineItem> discountRulesItem = checkoutProvider!.lineItems
        .map((e) => checkLineItemDiscountRules(context, e))
        .toList();
    ;
    List<LineItem> validLineItem =
        isLineItemDiscountRuleValid(context, discountRulesItem);
    printLog("valid line item: ${jsonEncode(validLineItem)}");
    return Container(
      child: ListView.builder(
        physics: ScrollPhysics(),
        shrinkWrap: true,
        itemCount: validLineItem.length,
        itemBuilder: (context, index) {
          return Column(
            children: [
              itemProduct(validLineItem[index], index),
              index != validLineItem.length - 1
                  ? Divider(
                      color: HexColor("#d5d5d5"),
                      thickness: 1,
                    )
                  : Container()
            ],
          );
        },
      ),
    );
  }

  Widget itemProduct(LineItem item, int index) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      child: Row(children: [
        Container(
          margin: EdgeInsets.symmetric(horizontal: 10),
          width: 70,
          height: 70,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(10),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: CachedNetworkImage(
              imageUrl: item.image!,
              fit: BoxFit.fill,
              placeholder: (context, url) => customLoading(),
              errorWidget: (context, url, error) => Icon(
                Icons.image_not_supported_rounded,
                size: 25,
              ),
            ),
          ),
        ),
        Expanded(
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              "${item.name}",
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
              softWrap: true,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            Visibility(
              visible: item.variation != "",
              child: Container(
                width: MediaQuery.of(context).size.width - 120,
                child: Text(
                  "${item.variation}",
                  maxLines: 2,
                  softWrap: true,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
            Text(
              "${item.qty} ${AppLocalizations.of(context)!.translate('items')} ${item.weight == 0 ? "" : "(${item.weight}kg)"}",
              style: TextStyle(fontSize: 12),
            ),
            Text(
              "${stringToCurrency(double.parse("${item.price}"), context)}",
              style: TextStyle(fontSize: 12),
            ),
          ]),
        ),
      ]),
    );
  }

  Widget buildSummary() {
    return Container(
      margin: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      padding: EdgeInsets.only(right: 10),
      child: Consumer<CheckoutProvider>(
        builder: (context, value, child) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    "${AppLocalizations.of(context)!.translate('item_subtotal')}",
                    style: TextStyle(
                        color: appNotifier!.isDarkMode
                            ? null
                            : HexColor("#6e6e6e")),
                  ),
                  Spacer(),
                  Text(
                    !widget.isFromBuyNow!
                        ? "${stringToCurrency(value.newSubTotal!, context)}"
                        : "${stringToCurrency(value.subTotal!, context)}",
                    style: TextStyle(
                        color: appNotifier!.isDarkMode
                            ? null
                            : HexColor("#6e6e6e")),
                  )
                ],
              ),
              Row(
                children: [
                  Text(
                    "${AppLocalizations.of(context)!.translate('shipping_cost')}",
                    style: TextStyle(
                        color: appNotifier!.isDarkMode
                            ? null
                            : HexColor("#6e6e6e")),
                  ),
                  Spacer(),
                  Text(
                    "${stringToCurrency(value.shippingLines[0].cost!, context)}",
                    // "${stringToCurrency(widget.line[0].a2wShipping, context)}",
                    style: TextStyle(
                        color: appNotifier!.isDarkMode
                            ? null
                            : HexColor("#6e6e6e")),
                  )
                ],
              ),
              Row(
                children: [
                  Text(
                    "${AppLocalizations.of(context)!.translate('coupon_code')}",
                    style: TextStyle(
                        color: appNotifier!.isDarkMode
                            ? null
                            : HexColor("#6e6e6e")),
                  ),
                  Spacer(),
                  GestureDetector(
                    onTap: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) =>
                                CouponScreen(products: products),
                          )).then((value) async {
                        final couponP =
                            Provider.of<CouponProvider>(context, listen: false);
                        final checkoutP = Provider.of<CheckoutProvider>(context,
                            listen: false);
                        setState(() {
                          printLog("${couponP.couponUsed!}",
                              name: "coupon used");
                          coupons.clear();
                          coupon = couponP.couponUsed!.code!;
                          coupons.add({"code": coupon});
                          if (couponP.couponUsed!.discountType == "percent") {
                            couponMount = checkoutP.subTotal! *
                                (double.parse(Provider.of<CouponProvider>(
                                            context,
                                            listen: false)
                                        .couponUsed!
                                        .amount
                                        .toString()) /
                                    100);
                          } else {
                            couponMount = double.parse(
                                Provider.of<CouponProvider>(context,
                                        listen: false)
                                    .couponUsed!
                                    .amount
                                    .toString());
                          }
                        });
                        printLog("$couponMount", name: "couponMount");
                        Provider.of<CheckoutProvider>(context, listen: false)
                            .calculateTotal(
                          disc: couponMount,
                          wallet: wallet,
                          isWallet: payWithWallet,
                        );
                        print("coupon : $coupon");
                      });
                    },
                    child: Row(
                      children: [
                        Text(
                          "${AppLocalizations.of(context)!.translate('add_coupon')}",
                          style: TextStyle(
                              fontSize: responsiveFont(8),
                              color: appNotifier!.isDarkMode
                                  ? null
                                  : HexColor("#6e6e6e")),
                        ),
                        Icon(
                          Icons.arrow_forward_ios_outlined,
                          size: 15,
                          color: appNotifier!.isDarkMode
                              ? null
                              : HexColor("#6e6e6e"),
                        )
                      ],
                    ),
                  ),
                ],
              ),
              SizedBox(
                height: 20.h,
              ),
              Row(
                children: [
                  Text(
                    "${AppLocalizations.of(context)!.translate('total_price')!} ($qtyTotal ${AppLocalizations.of(context)!.translate('items')!})",
                    style: TextStyle(
                        color: appNotifier!.isDarkMode
                            ? null
                            : HexColor("#6e6e6e")),
                  ),
                  Spacer(),
                  Text(
                    !widget.isFromBuyNow!
                        ? "${stringToCurrency(((value.total! - value.subTotal!) + value.newSubTotal!), context)}"
                        : "${stringToCurrency(value.total!, context)}",
                    style: TextStyle(
                        color: appNotifier!.isDarkMode
                            ? null
                            : HexColor("#6e6e6e")),
                  )
                ],
              ),
              // Visibility(
              //   visible: chooseShipping,
              //   child: Row(
              //     children: [
              //       Container(
              //         width: 240,
              //         child: Text(
              //           "${AppLocalizations.of(context)!.translate('total_shipping')!} (${value.shipping})",
              //           style: TextStyle(
              //               color: appNotifier!.isDarkMode
              //                   ? null
              //                   : HexColor("#6e6e6e")),
              //           maxLines: 2,
              //         ),
              //       ),
              //       Spacer(),
              //       Text(
              //         "${value.shippingCost}",
              //         style: TextStyle(
              //             color: appNotifier!.isDarkMode
              //                 ? null
              //                 : HexColor("#6e6e6e")),
              //       )
              //     ],
              //   ),
              // ),
              Visibility(
                visible: coupon != "",
                child: Row(
                  children: [
                    Text(
                      "${AppLocalizations.of(context)!.translate('total_disc')!} ($coupon)",
                      style: TextStyle(
                          color: appNotifier!.isDarkMode
                              ? null
                              : HexColor("#6e6e6e")),
                    ),
                    Spacer(),
                    Text(
                      couponMount > value.subTotal!
                          ? "-${stringToCurrency(value.subTotal!, context)}"
                          : "-${stringToCurrency(couponMount, context)}",
                      style: TextStyle(
                          color: appNotifier!.isDarkMode ? null : Colors.red),
                    )
                  ],
                ),
              ),
              Visibility(
                visible: payWithWallet,
                child: Row(
                  children: [
                    Text(
                      "${AppLocalizations.of(context)!.translate('via_wallet')}",
                      style: TextStyle(
                          color: appNotifier!.isDarkMode
                              ? null
                              : HexColor("#6e6e6e")),
                    ),
                    Spacer(),
                    Text(
                      "-${stringToCurrency(wallet, context)}",
                      style: TextStyle(
                          color: appNotifier!.isDarkMode ? null : Colors.red),
                    )
                  ],
                ),
              ),
              Visibility(
                visible: payWithPoint,
                child: Row(
                  children: [
                    Text(
                      "Point Redemption",
                      style: TextStyle(
                          color: appNotifier!.isDarkMode
                              ? null
                              : HexColor("#6e6e6e")),
                    ),
                    Spacer(),
                    Text(
                      "-${stringToCurrency(value.pointsRedemption!.totalDisc!, context)}",
                      style: TextStyle(
                          color: appNotifier!.isDarkMode ? null : Colors.red),
                    )
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  buildBottomBarCart() {
    final grandTotal = Provider.of<CheckoutProvider>(
      context,
    ).grandTotal;
    return Column(
      children: [
        Container(
          width: double.infinity,
          height: 1,
          color: HexColor("DDDDDD"),
        ),
        Consumer<CheckoutProvider>(
          builder: (context, value, child) {
            return Material(
                elevation: 5,
                color: Colors.white,
                child: Container(
                  padding: EdgeInsets.only(
                      left: Session.data.getString('language_code') == 'ar'
                          ? 0
                          : 10,
                      right: Session.data.getString('language_code') == 'ar'
                          ? 10
                          : 0),
                  width: MediaQuery.of(context).size.width,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                              '${AppLocalizations.of(context)!.translate('total')}  ',
                              style: TextStyle(fontWeight: FontWeight.bold)),
                          Text(
                            !widget.isFromBuyNow!
                                ? '${stringToCurrency(((value.newTotal! - value.subTotal!) + value.newSubTotal!), context)}'
                                : '${stringToCurrency(value.newTotal!, context)}',
                            style: TextStyle(
                                color: appNotifier!.isDarkMode
                                    ? null
                                    : HexColor("#6e6e6e")),
                          ),
                        ],
                      ),
                      TextButton(
                        onPressed: () {
                          // UIBlock.block(
                          //   context,
                          //   backgroundColor: Colors.black54,
                          //   customLoaderChild:
                          //       LoadingAnimationWidget.staggeredDotsWave(
                          //           color: primaryColor, size: 80),
                          //   childBuilder: (BuildContext context) {
                          //     return Padding(
                          //       padding: const EdgeInsets.all(8.0),
                          //       child: Center(
                          //         child: Column(
                          //           mainAxisAlignment: MainAxisAlignment.center,
                          //           children: [
                          //             LoadingAnimationWidget.staggeredDotsWave(
                          //                 color: primaryColor, size: 80),
                          //             Text(
                          //               AppLocalizations.of(context)!
                          //                   .translate('place_order_text')!,
                          //               // "Mohon menunggu sebentar.\n\nSaat ini sistem sedang\nmemproses transaksi Anda.\n\nJangan menutup aplikasi\nsampai transaksi selesai.",
                          //               style: TextStyle(
                          //                   color: Colors.white,
                          //                   fontWeight: FontWeight.bold),
                          //               textAlign: TextAlign.center,
                          //             ),
                          //             SizedBox(
                          //               height: 10,
                          //             ),
                          //             Visibility(
                          //               visible: value.isAlertSet,
                          //               child: GestureDetector(
                          //                 onTap: () {
                          //                   value.setAlert();
                          //                   Navigator.push(
                          //                       context,
                          //                       MaterialPageRoute(
                          //                         builder: (context) => MyOrder(
                          //                             // fromNative: true,
                          //                             ),
                          //                       ));
                          //                 },
                          //                 child: Container(
                          //                   padding: EdgeInsets.all(8),
                          //                   decoration: BoxDecoration(
                          //                       borderRadius:
                          //                           BorderRadius.circular(10),
                          //                       color: primaryColor),
                          //                   child: Text(
                          //                     AppLocalizations.of(context)!
                          //                         .translate('check_order')!,
                          //                     style: TextStyle(
                          //                         color: Colors.white),
                          //                   ),
                          //                 ),
                          //               ),
                          //             ),
                          //           ],
                          //         ),
                          //       ),
                          //     );
                          //   },
                          // );
                          // placeOrder();
                          printLog("${(grandTotal! <= wallet)}");
                          if (!Session.data.getBool("isLogin")!) {
                            if (billing.isEmpty) {
                              snackBar(context,
                                  message: "Please complete the address first");
                            } else {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) => PaymentMethodScreen(
                                          line: widget.line,
                                          coupons: coupons,
                                          payWithWallet: grandTotal <= wallet
                                              ? true
                                              : false,
                                          isWalletPartial: payWithWallet,
                                          removeOrderedItems:
                                              widget.removeOrderedItems,
                                          userBilling: UserData(
                                              firstName: billing[0],
                                              lastName: billing[1],
                                              company: billing[2],
                                              address1: billing[6],
                                              address2: billing[7],
                                              city: billing[5],
                                              postcode: billing[8],
                                              phone: billing[9],
                                              email: billing[10],
                                              country: billing[11],
                                              state: billing[12]))));
                            }
                          } else {
                            if (value.user?.firstName == "" ||
                                value.user?.lastName == "" ||
                                value.user?.address1 == "" ||
                                value.user?.city == "" ||
                                value.user?.postcode == "" ||
                                value.user?.phone == "" ||
                                value.user?.email == "" ||
                                value.user?.country == "") {
                              snackBar(context,
                                  message: "Please complete the address first");
                            } else {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) => PaymentMethodScreen(
                                          line: widget.line,
                                          coupons: coupons,
                                          payWithWallet: grandTotal <= wallet
                                              ? true
                                              : false,
                                          isWalletPartial: payWithWallet,
                                          removeOrderedItems:
                                              widget.removeOrderedItems,
                                          userBilling: UserData(
                                              firstName: value.user?.firstName,
                                              company: value.user?.company,
                                              lastName: value.user?.lastName,
                                              address1: value.user?.address1,
                                              address2: value.user?.address2,
                                              city: value.user?.city,
                                              postcode: value.user?.postcode,
                                              phone: value.user?.phone,
                                              email: value.user?.email,
                                              country: value.user?.country,
                                              state: value.user?.state,
                                              stateName: value.user?.stateName,
                                              countryName:
                                                  value.user?.countryName))));
                            }
                          }
                        },
                        style: TextButton.styleFrom(
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(5)),
                            padding: EdgeInsets.all(15),
                            backgroundColor: primaryColor),
                        child: Text(
                          AppLocalizations.of(context)!.translate('checkout')!,
                          style: TextStyle(color: Colors.black),
                        ),
                      )
                    ],
                  ),
                ));
          },
        )
      ],
    );
  }

  Widget buildAddressCard() {
    int borderColor = 15;
    return GestureDetector(
      onTap: () async {
        if (Session.data.getBool('isLogin')!) {
          Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => AddressCheckoutNative(
                  title: 'billing',
                ),
              )).then((value) {
            loadData();
          });
        } else if (billing.isNotEmpty) {
          printLog(billing.toString(), name: "billing");
          await Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => AddressCheckoutNative(
                  billingEmpty: false,
                  title: 'billing',
                  isGuest: true,
                  billing: billing,
                ),
              )).then((value) {
            if (value != null) {
              billing.clear();
              billing = value;
              setState(() {});
              loadData();
            }
          });
        } else {
          Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => AddressCheckoutNative(
                  title: "billing",
                  isGuest: true,
                  billingEmpty: true,
                ),
              )).then((value) {
            if (value != null) {
              billing.clear();
              billing = value;
              setState(() {
                loadData();
              });
            }
            printLog("billing : $value");
          });
        }
      },
      child: Container(
          constraints: BoxConstraints(minHeight: 50),
          margin: EdgeInsets.only(left: 10.w, right: 10.w, top: 10.h),
          padding: EdgeInsets.only(left: 5.w, right: 5.w, top: 5.h),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(10)),
          child: Consumer<CheckoutProvider>(
            builder: (context, value, child) {
              return Column(
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.location_on_outlined,
                        size: 30,
                      ),
                      SizedBox(
                        width: 10.w,
                      ),
                      Expanded(child: buildAddress(value.user!)),
                      Icon(
                        Icons.arrow_forward_ios_rounded,
                        color: Colors.grey,
                      )
                    ],
                  ),
                  SizedBox(
                    height: 5.h,
                  ),
                  Container(
                    height: 3.h,
                    child: ListView.builder(
                      physics: NeverScrollableScrollPhysics(),
                      scrollDirection: Axis.horizontal,
                      itemCount: borderColor,
                      itemBuilder: (context, index) {
                        if (index % 2 == 0) {
                          return Row(
                            children: [
                              Container(
                                height: 3.h,
                                width: 22.w,
                                color: primaryColor,
                              ),
                              SizedBox(
                                width: 6.w,
                              )
                            ],
                          );
                        } else {
                          return Row(
                            children: [
                              Container(
                                height: 3.h,
                                width: 22.w,
                                color: Colors.grey,
                              ),
                              SizedBox(
                                width: 6.w,
                              )
                            ],
                          );
                        }
                      },
                    ),
                  )
                ],
              );
            },
          )),
    );
  }

  Widget buildAddress(UserData user) {
    return user.firstName != null &&
            Session.data.getBool('isLogin')! &&
            user.firstName != ""
        ? Container(
            width: MediaQuery.of(context).size.width,
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.start,
                children: [
                  Text(
                    user.firstName! + " " + user.lastName!,
                    // " ${user.company != null && user.company != "" ? "(${user.company})" : ""}",
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                  Text(
                    user.phone!,
                    style: TextStyle(fontSize: 12),
                  ),
                  Text(
                    user.email!,
                    style: TextStyle(fontSize: 12),
                  ),
                  Text(
                    user.address1! + ", " + "${user.address2 ?? ""}",
                    style: TextStyle(fontSize: 12),
                  ),
                  Text(
                    user.city! + " - " + (user.stateName!),
                    style: TextStyle(fontSize: 12),
                  ),
                  Text(
                    (user.countryName!) + " - " + user.postcode!,
                    style: TextStyle(fontSize: 12),
                  ),
                ]),
          )
        : !Session.data.getBool('isLogin')! && billing.isNotEmpty
            ? Container(
                width: MediaQuery.of(context).size.width,
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        billing[0] + " " + billing[1],
                        style: TextStyle(fontSize: 12),
                      ),
                      Text(billing[9], style: TextStyle(fontSize: 12)),
                      Text(billing[10], style: TextStyle(fontSize: 12)),
                      // Text(billing[2] == "" ? "-" : billing[2]),
                      Text(billing[6] + ", " + billing[7],
                          style: TextStyle(fontSize: 12)),
                      Text(billing[5] + " - " + billing[4],
                          style: TextStyle(fontSize: 12)),
                      Text(billing[3] + " - " + billing[8],
                          style: TextStyle(fontSize: 12)),
                    ]),
              )
            : Container(
                child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        AppLocalizations.of(context)!
                            .translate('pls_add_change_addr')!,
                        style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            color: Colors.red),
                      ),
                    ]),
              );
  }
}
