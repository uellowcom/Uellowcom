import 'dart:async';
import 'dart:convert';

import 'package:flutter/cupertino.dart';
import 'package:nyoba/models/cart_model.dart';
import 'package:nyoba/models/checkout_data_model.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/services/order_api.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

class CheckoutProvider with ChangeNotifier {
  bool loading = true;
  bool loadingOrder = false;
  UserData? user;
  List<LineItem> lineItems = [];
  List<ShippingLine> shippingLines = [];
  List<PaymentMethod> paymentMethods = [];
  List<PaymentMethod> tempPaymentMethods = [];
  PointsRedemption? pointsRedemption;
  late StreamSubscription subscription;
  var isDeviceConnected = false;
  bool isAlertSet = false;
  bool isWallet = false;

  // Future<bool> deleteCart({List<CartProductItem>? line}) async {
  //   await OrderAPI().addCart(action: "delete", line: line).then((data) {
  //     printLog("data : $data");
  //     if (data['status'] == 'success') {
  //       return true;
  //     }
  //   });
  //   return false;
  // }

  // Future<bool> syncCart({List<CartProductItem>? line}) async {
  //   await OrderAPI().addCart(action: "sync", line: line).then((data) {
  //     printLog("data : $data");
  //     if (data['status'] == 'success') {
  //       return true;
  //     }
  //   });
  //   return false;
  // }

  // getConectivity() {
  //   subscription = Connectivity().onConnectivityChanged.listen((event) async {
  //     isDeviceConnected = await InternetConnectionChecker().hasConnection;
  //     if (!isDeviceConnected) {
  //       printLog("inet off", name: "check inet");
  //       isAlertSet = true;
  //       notifyListeners();
  //     }
  //   });
  // }

  setAlert() {
    isAlertSet = false;
    notifyListeners();
  }

  // Future createCart({List<CartProductItem>? line}) async {
  //   OrderAPI().addCart(action: "create", line: line);
  // }

  int? indexPayment;
  int? indexShipping;
  int? indexCourier;
  String? titlePayment;
  String? titleShipping;
  String? shipping;
  String? shippingCost;
  double? total = 0;
  double? subTotal = 0;
  double? newSubTotal = 0;
  double? grandTotal = 0;
  double? newTotal = 0;
  ShippingLine? shiped;
  PaymentMethod? payment;
  String? titleCourier = "Choose Courier Services";
  String? courierCost = "0";
  String? courierEtd;
  Couriers? courier;
  List<Couriers>? listCourier = [];
  var shippingPrice;

  changeNewSubTotal(double newSub) {
    newSubTotal = newSub;
    notifyListeners();
  }

  setNewPayment(PaymentMethod tempPayment) {
    payment = tempPayment;
    notifyListeners();
  }

  setNewShipping(ShippingLine shippingLine) {
    shiped = shippingLine;
    notifyListeners();
  }

  insertCourier(value) {
    listCourier = (value);
    notifyListeners();
  }

  reset() {
    indexPayment = null;
    titlePayment = null;
    indexShipping = null;
    titleShipping = null;
    titleCourier = "Choose Courier Services";
    user = null;
    shiped = null;
    payment = null;
    listCourier?.clear();
    notifyListeners();
  }

  resetPayment() {
    payment = null;
    titlePayment = null;
    indexPayment = null;
    notifyListeners();
  }

  double ratePoint = 0;
  checkPoin({double? coupon = 0}) {
    if (coupon != 0) {
      double temptotal = total! - coupon!;
      printLog(temptotal.toString());
      pointsRedemption!.totalDisc = temptotal.toInt();
      pointsRedemption!.point = temptotal.toInt() * ratePoint.toInt();
    }
  }

  Future<dynamic> placeOrder(
      {List<CartProductItem>? line,
      UserData? bill,
      ShippingLine? ship,
      PaymentMethod? pay,
      List<Map<String, dynamic>>? coupon,
      String? note,
      bool? partialPayment,
      required BuildContext context}) async {
    var val;
    try {
      loadingOrder = true;
      notifyListeners();
      await OrderAPI()
          .placeOrder(
              line: line,
              bill: bill,
              ship: ship,
              pay: pay,
              coupon: coupon,
              note: note,
              partialPayment: partialPayment,
              context: context)
          .then((data) {
        printLog(json.encode(data));
        if (data != null) {
          val = data;
          return data;
        }
      });
      loadingOrder = false;
      notifyListeners();
      return val;
    } catch (e) {
      loadingOrder = false;
      print(e.toString());
      notifyListeners();
      return false;
    }
  }

  Future<bool> calculateTotal(
      {double? disc,
      double? wallet,
      bool? isWallet = false,
      bool? isPoint = false,
      int? point = 0}) async {
    printLog("diskon calculate total: $disc");
    grandTotal = total;
    newTotal = total;

    if (point != 0 && isPoint!) {
      printLog("masuk if point!=0");
      grandTotal = grandTotal! - point!.toDouble();
      newTotal = newTotal! - point.toDouble();
    }
    if (isWallet!) {
      printLog("masuk isWallet!");
      grandTotal = grandTotal! - disc!;
      if (disc <= newTotal!)
        newTotal = newTotal! - disc - wallet!;
      else if (disc > newTotal!) newTotal = 0;
    } else if (!isWallet) {
      printLog("masuk !isWallet");
      grandTotal = grandTotal! - disc!;
      printLog("grand total: $grandTotal");
      if (disc <= newTotal!)
        newTotal = newTotal! - disc;
      else if (disc > newTotal!) newTotal = 0;
    }
    printLog("new total: $newTotal");
    // if (disc != 0) {
    //   printLog("masuk diskon tidak null");
    //   newTotal = newTotal! + shippingPrice;
    // }

    notifyListeners();
    return true;
  }

  removeCOD({required List<PaymentMethod> listPaymentMethod}) {
    paymentMethods = listPaymentMethod;
    notifyListeners();
  }

  Future getCheckoutData(
      {List<CartProductItem>? line,
      String? countryId,
      String? stateId,
      String? postcode,
      String? city,
      String? subdistrict,
      required BuildContext context}) async {
    loading = true;
    try {
      // if (Session.data.containsKey('cookie')) {
      //   line = null;
      // }
      lineItems.clear();
      shippingLines.clear();
      paymentMethods.clear();
      String country = base64Encode(
          utf8.encode(context.read<ProductProvider>().currentPosition));
      await OrderAPI()
          .checkoutData(
        line: line,
        countryId: countryId,
        stateId: stateId,
        postcode: postcode,
        city: city,
        subdistrict: subdistrict,
        context: context,
        country: country,
      )
          .then((data) {
        var result;
        printLog("data 1: ${json.encode(data)}");
        if (data != null) {
          result = data;
          if (result['user_data'] != null) {
            user = UserData.fromJson(result['user_data']);
            printLog("data : ${json.encode(user)}");
          }
          printLog(json.encode(user), name: 'USER');
          if (result['line_items'] != null && result['line_items'].isNotEmpty) {
            for (Map item in result['line_items']) {
              lineItems.add(LineItem.fromJson(item));
            }
          }
          if (result['shipping_lines'] != null) {
            for (Map item in result['shipping_lines']) {
              shippingLines.add(ShippingLine.fromJson(item));
            }
          }
          if (result['payment_methods'] != null) {
            for (Map item in result['payment_methods']) {
              paymentMethods.add(PaymentMethod.fromJson(item));
            }
            tempPaymentMethods = paymentMethods;
          }
          if (result['points_redemption'] != null) {
            pointsRedemption =
                PointsRedemption.fromJson(result['points_redemption']);
            ratePoint = pointsRedemption!.point! / pointsRedemption!.totalDisc!;
          }
        }
        total = 0;
        subTotal = 0;
        for (int i = 0; i < lineItems.length; i++) {
          total = total! + lineItems[i].subtotal!;
          subTotal = subTotal! + lineItems[i].subtotal!;
        }
        for (int i = 0; i < shippingLines.length; i++) {
          total = total! + shippingLines[i].cost!;
          shippingPrice = shippingLines[i].cost!;
        }
        printLog("$shippingPrice shipping price");
        grandTotal = total;
        newTotal = total;
        loading = false;
        notifyListeners();
      });
    } catch (e) {
      loading = false;
      notifyListeners();
      print(e.toString());
    }
  }
}
