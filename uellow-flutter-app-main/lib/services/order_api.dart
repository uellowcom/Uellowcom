import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../models/cart_model.dart';
import '../models/checkout_data_model.dart';
import '../provider/urlProvider.dart';

class OrderAPI {
  checkoutOrder(order, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response =
        await newUrl.getAsync('$orderApi?order=$order', isOrder: true);
    return response;
  }

  listMyOrder(String? status, String? search, String? orderId, int? page,
      int? limit, BuildContext context,
      {required String? country}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {
      "cookie": Session.data.getString('cookie'),
      "status": status,
      "search": search,
      "page": page,
      "limit": limit,
      if (orderId != null) "order_id": orderId,
      "country": country,
    };
    printLog("${jsonEncode(data)}", name: "data my order");
    var response = await newUrl.newCustomBaseAPI.postAsync('$listOrders', data,
        isCustom: true, headersTranslate: 'list-product');
    return response;
  }

  detailOrder(
    String? orderId,
    BuildContext context, {
    required String? country,
  }) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {
      "cookie": Session.data.getString('cookie'),
      "order_id": orderId,
      "country": country,
    };
    printLog(data.toString());
    var response = await newUrl.newCustomBaseAPI.postAsync('$listOrders', data,
        isCustom: true, headersTranslate: 'list-product');
    return response;
  }

  checkoutData({
    List<CartProductItem>? line,
    String? countryId,
    String? stateId,
    String? postcode,
    String? city,
    String? subdistrict,
    required BuildContext context,
    required String? country,
  }) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {
      "cookie": Session.data.getString('cookie'),
      "line_items": line,
      "country_id": countryId,
      "state_id": stateId,
      'postcode': postcode,
      "city": city,
      "subdistrict": subdistrict,
      'country': country,
    };
    printLog("data : ${json.encode(data)}");
    var response = await newUrl.newCustomBaseAPI.postAsync(
        '$checkoutDatas', data,
        isCustom: true, printedLog: true, headersTranslate: "checkout-data");
    printLog("${jsonEncode(response)}", name: "response checkout data");
    return response;
  }

  placeOrder(
      {List<CartProductItem>? line,
      UserData? bill,
      ShippingLine? ship,
      PaymentMethod? pay,
      List<Map<String, dynamic>>? coupon,
      String? note,
      bool? partialPayment,
      required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    printLog("couponz: ${jsonEncode(coupon)}");

    Map data = {
      "cookie": Session.data.getString('cookie'),
      'line_items': line,
      'billing_address': bill,
      'shipping_lines': ship,
      'payment_method': pay,
      'coupon_lines': coupon,
      "order_notes": note,
      "wallet_partial_payment": partialPayment
    };
    printLog("data place : ${json.encode(data)}");
    var response =
        await newUrl.baseAPI.postAsync('$placeOrders', data, isCustom: true);
    printLog("response place : ${json.encode(response)}");
    return response;
  }

  loadProductCart(String? include, context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {
      "include": include,
      "lang": Session.data.getString("language_code"),
      "cookie": Session.data.containsKey("cookie")
          ? Session.data.getString("cookie")
          : null,
    };
    printLog(data.toString());
    var response = await newUrl.newCustomBaseAPI.postAsync(
      '$customProductUrl',
      data,
      isCustom: true,
    );
    return response;
  }
}
