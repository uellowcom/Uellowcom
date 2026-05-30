import 'dart:convert';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:loading_animation_widget/loading_animation_widget.dart';
import 'package:nyoba/pages/order/order_success_screen.dart';
import 'package:nyoba/provider/app_provider.dart';
import 'package:nyoba/provider/checkout_provider.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:nyoba/widgets/container_card.dart';
import 'package:provider/provider.dart';
import 'package:uiblock/uiblock.dart';

import '../../../app_localizations.dart';
import '../../../constant/constants.dart';
import '../../../models/cart_model.dart';
import '../../../models/checkout_data_model.dart';
import '../../../models/checkout_guest_model.dart';
import '../../../models/product_model.dart';
import '../../../provider/order_provider.dart';
import '../../../services/session.dart';
import '../../../widgets/webview/checkout_webview.dart';
import '../my_order_screen.dart';

class PaymentMethodScreen extends StatefulWidget {
  final List<CartProductItem>? line;
  final List<Map<String, dynamic>>? coupons;
  final bool payWithWallet;
  final bool isWalletPartial;
  final UserData? userBilling;
  final Future<dynamic> Function()? removeOrderedItems;

  const PaymentMethodScreen(
      {super.key,
      this.line,
      this.coupons,
      this.userBilling,
      this.removeOrderedItems,
      required this.payWithWallet,
      required this.isWalletPartial});

  @override
  State<PaymentMethodScreen> createState() => _PaymentMethodScreenState();
}

class _PaymentMethodScreenState extends State<PaymentMethodScreen> {
  CheckoutProvider? checkoutProvider;
  List<ProductModel> productCart = [];

  PaymentMethod? payment;
  AppNotifier? appNotifier;

  Future<bool> loadCart() async {
    if (Session.data.containsKey('cart')) {
      List? listCart = await json.decode(Session.data.getString('cart')!);

      setState(() {
        productCart = listCart!
            .map((product) => new ProductModel.fromJson(product))
            .toList();
      });
      if (productCart.isNotEmpty) {
        context
            .read<OrderProvider>()
            .fetchProductCart(productCart, context)
            .then((value) {
          setState(() {
            productCart = value;
          });
        });
      }
      return true;
    }
    return false;
  }

  Future removeOrderedItems() async {
    printLog("LINE : ${json.encode(widget.line)} \n ");
    for (int i = 0; i < widget.line!.length; i++) {
      if (widget.line![i].variationId == null) {
        productCart
            .removeWhere((element) => element.id == widget.line![i].productId);
      } else {
        productCart.removeWhere(
            (element) => element.variantId == widget.line![i].variationId);
      }
    }
    printLog("cart : ${json.encode(productCart)}");
    List<CartProductItem>? line = [];
    for (int i = 0; i < productCart.length; i++) {
      if (!productCart[i].isSelected!) {
        line.add(new CartProductItem(
            productId: productCart[i].id,
            quantity: productCart[i].cartQuantity,
            variationId: productCart[i].variantId == 0
                ? null
                : productCart[i].variantId));
      }
    }
    printLog("line : ${json.encode(line)}");
    // if (Provider.of<HomeProvider>(context, listen: false).syncCart) {
    //   OrderAPI().addCart(action: "create", line: line);
    // }
    saveData();
    // await Provider.of<CouponProvider>(context, listen: false).clearCoupon();
    // await Navigator.pushReplacement(
    //     context, MaterialPageRoute(builder: (context) => OrderSuccess()));
  }

  saveData() async {
    await Session.data.setString('cart', json.encode(productCart));
    printLog(productCart.toString(), name: "Cart Product");
    Provider.of<OrderProvider>(context, listen: false)
        .loadCartCount()
        .then((value) => setState(() {}));
  }

  Future<bool> saveOrderGuest(dynamic value) async {
    if (!Session.data.getBool('isLogin')!) {
      List<CheckoutGuest> listOrder = [];

      if (Session.data.containsKey('order_guest')) {
        List orders = json.decode(Session.data.getString('order_guest')!);

        listOrder =
            orders.map((order) => new CheckoutGuest.fromJson(order)).toList();
      }
      String urlRequest = url +
          "/checkout/order-received/" +
          value['id'].toString() +
          "/?key=" +
          value['order_key'].toString();
      listOrder.add(new CheckoutGuest(
          url: urlRequest,
          createdAt: DateTime.now().toString(),
          orderId: value['id']));
      Session.data.setString('order_guest', json.encode(listOrder));
      printLog("MASUK SINI OI : ${Session.data.getString('order_guest')}");
      return true;
    }
    return false;
  }

  placeOrder() async {
    checkoutProvider!.setNewPayment(payment!);
    checkoutProvider!.setNewShipping(checkoutProvider!.shippingLines[0]);

    if (checkoutProvider!.user == null) {
      UIBlock.unblock(context);
      return snackBar(context,
          message:
              AppLocalizations.of(context)!.translate('pls_enter_shipping')!);
    }
    UserData? userBilling;

    // Checkout Guest
    // if (!Session.data.getBool('isLogin')!) {
    //   userBilling = new UserData(
    //       firstName: billing[0],
    //       lastName: billing[1],
    //       company: billing[2],
    //       country: billing[11],
    //       countryName: billing[3],
    //       address1: billing[6],
    //       address2: billing[7],
    //       city: billing[5],
    //       state: billing[12],
    //       stateName: billing[4],
    //       postcode: billing[8],
    //       phone: billing[9],
    //       email: billing[10],
    //       location: LocationCoordinate.fromJson(json.decode(billing[13])));
    //   Session.data.setString("country_id", "");
    //   Session.data.setString("state_id", "");
    //   Session.data.setString("postcode", "");
    // }
    await Provider.of<CheckoutProvider>(context, listen: false)
        .placeOrder(
            line: widget.line,
            bill: Session.data.getBool('isLogin')!
                ? checkoutProvider!.user!
                : widget.userBilling!,
            ship: checkoutProvider!.shiped,
            pay: checkoutProvider!.payment,
            coupon: widget.coupons,
            partialPayment: widget.isWalletPartial,
            context: context)
        .then((value) {
      printLog("value place: ${json.encode(value)}");
      if (value.containsKey('status') && value['status'] == "error") {
        UIBlock.unblock(context);
        printLog("$value", name: "error");
        if (value.toString().contains("Your wallet balance is low")) {
          return snackBar(context,
              message: AppLocalizations.of(context)!.translate('wallet_low')!);
        }
        return snackBar(context,
            message: AppLocalizations.of(context)!
                .translate('invalid_billing_addr')!);
      } else {
        checkoutProvider!.reset();
        Session.data.setString('order_number', value['id'].toString());
        printLog(Session.data.getString('order_number')!,
            name: "ORDER NUMBER CHECKOUT NATIVE");
        // loadCart().then((data) {
        //   if (data) {
        //     removeOrderedItems();
        //   }
        // });
        printLog(value['payment_link'], name: "PAYMENT LINK");
        if (value['payment_link'] != "") {
          Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => CheckoutWebView(
                  // fromPlaceOrder: true,
                  url: value['payment_link'],
                  isFromNativeCheckout: true, onFinish: removeOrderedItems,
                ),
              ));
          // s_launchUrl(value['payment_link']);
        } else if (value['payment_link'] == "") {
          widget.removeOrderedItems!();
          if (Session.data.getBool('isLogin')!) {
            Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => OrderSuccess(),
                ));
          } else {
            saveOrderGuest(value).then((value) {
              if (value) {
                Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => OrderSuccess(),
                    ));
              }
            });
          }
        }
      }
      if (!value) {
        return snackBar(context,
            message:
                AppLocalizations.of(context)!.translate('failed_place_order')!);
      }
    });
  }

  @override
  void initState() {
    // TODO: implement initState
    super.initState();
    checkoutProvider = Provider.of<CheckoutProvider>(context, listen: false);
    printLog("masuk payment metod init");
    // printLog("====== INI COD =======" + widget.product!.codPayment.toString());
    printLog("${widget.payWithWallet}");
    // if (widget.payWithWallet == false) {
    //   var indexPayment;
    //   printLog("${checkoutProvider!.paymentMethods}");

    //   checkoutProvider!.paymentMethods.forEach((element) {
    //     printLog("${jsonEncode(element.title)}");
    //     if (element.title == "Wallet payment") {
    //       indexPayment = checkoutProvider!.paymentMethods.indexOf(element);
    //     }
    //   });
    //   if (indexPayment != null) {
    //     checkoutProvider!.paymentMethods.removeAt(indexPayment);
    //   }
    //   printLog("${checkoutProvider!.paymentMethods}");
    // }

    // List<bool> isCod = [];

    // for (var i in widget.product!) {
    //   if (i.codPayment! == false) {
    //     isCod.add(false);
    //   } else {
    //     isCod.add(true);
    //   }
    // }

    // if (isCod.contains(false)) {
    //   var indexPayment;
    //   checkoutProvider!.paymentMethods.forEach((element) {
    //     printLog("${jsonEncode(element.title)}");
    //     if (element.title == "Cash on delivery") {
    //       indexPayment = checkoutProvider!.paymentMethods.indexOf(element);
    //     }
    //   });
    //   if (indexPayment != null) {
    //     checkoutProvider!.paymentMethods.removeAt(indexPayment);
    //   }
    //   printLog("${checkoutProvider!.paymentMethods}");
    // } else {
    //   // showDialog(context: context, builder: builder)
    // }
    List<bool> isContainNotSupportCOD = [];
    widget.line!.forEach((element) {
      printLog("cod: ${element.codPayment}");
      if (element.codPayment == true) {
        isContainNotSupportCOD.add(true);
      } else {
        isContainNotSupportCOD.add(false);
      }
    });

    if (isContainNotSupportCOD.contains(false)) {
      var indexPayment;
      printLog("${checkoutProvider!.paymentMethods}");

      checkoutProvider!.paymentMethods.forEach((element) {
        printLog("${jsonEncode(element.title)}");
        if (element.title == "Cash on delivery") {
          indexPayment = checkoutProvider!.paymentMethods.indexOf(element);
        }
      });
      // if (indexPayment != null) {
      //   checkoutProvider!.paymentMethods.removeAt(indexPayment);
      // }
      printLog("${checkoutProvider!.paymentMethods}");
    }

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

    // if (widget.product!.codPayment == false) {

    // }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[200],
      appBar: AppBar(
        leading: GestureDetector(
          onTap: () {
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
          "${AppLocalizations.of(context)!.translate('payment_method')}",
          style: TextStyle(color: Colors.black),
        ),
        backgroundColor: Colors.white,
      ),
      body: Consumer<CheckoutProvider>(
        builder: (context, value, child) {
          return ListView(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const SizedBox(height: 20),
                  Text("Your payment will be"),
                  Text(
                    '${stringToCurrency(value.newTotal!, context)}',
                    style: TextStyle(
                      fontSize: responsiveFont(20),
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              ListView.builder(
                itemCount: value.paymentMethods.length,
                shrinkWrap: true,
                itemBuilder: (context, index) {
                  return Container(
                    margin: EdgeInsets.symmetric(horizontal: 15.w),
                    child: GestureDetector(
                      onTap: () {
                        setState(() {
                          payment = value.paymentMethods[index];
                        });
                        UIBlock.block(
                          context,
                          backgroundColor: Colors.black54,
                          customLoaderChild:
                              LoadingAnimationWidget.staggeredDotsWave(
                                  color: primaryColor, size: 80),
                          childBuilder: (BuildContext context) {
                            return Padding(
                              padding: const EdgeInsets.all(8.0),
                              child: Center(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    LoadingAnimationWidget.staggeredDotsWave(
                                        color: primaryColor, size: 80),
                                    Text(
                                      AppLocalizations.of(context)!
                                          .translate('place_order_text')!,
                                      // "Mohon menunggu sebentar.\n\nSaat ini sistem sedang\nmemproses transaksi Anda.\n\nJangan menutup aplikasi\nsampai transaksi selesai.",
                                      style: TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold),
                                      textAlign: TextAlign.center,
                                    ),
                                    SizedBox(
                                      height: 10,
                                    ),
                                    Visibility(
                                      visible: value.isAlertSet,
                                      child: GestureDetector(
                                        onTap: () {
                                          value.setAlert();
                                          Navigator.push(
                                              context,
                                              MaterialPageRoute(
                                                builder: (context) => MyOrder(
                                                  fromAccountScreen: false,
                                                  // fromNative: true,
                                                ),
                                              ));
                                        },
                                        child: Container(
                                          padding: EdgeInsets.all(8),
                                          decoration: BoxDecoration(
                                              borderRadius:
                                                  BorderRadius.circular(10),
                                              color: primaryColor),
                                          child: Text(
                                            AppLocalizations.of(context)!
                                                .translate('check_order')!,
                                            style:
                                                TextStyle(color: Colors.white),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        );
                        placeOrder();
                      },
                      child: ContainerCard(
                          child: Container(
                        padding: EdgeInsets.symmetric(vertical: 10.h),
                        child: Row(
                          children: [
                            CachedNetworkImage(
                              imageUrl: value.paymentMethods[index].image!,
                              width: 50,
                              height: 30,
                              errorWidget: (context, url, error) => Icon(
                                Icons.image_not_supported_rounded,
                                size: 25,
                              ),
                            ),
                            const SizedBox(width: 20),
                            Text(
                              "${value.paymentMethods[index].title}",
                              style: TextStyle(fontSize: responsiveFont(13)),
                            ),
                          ],
                        ),
                      )),
                    ),
                  );
                },
                // separatorBuilder: (context, index) => SizedBox(
                //   height: 10.h,
                // ),
              ),
            ],
          );
        },
      ),
    );
  }
}
