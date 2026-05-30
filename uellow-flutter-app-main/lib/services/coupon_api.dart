import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/provider/urlProvider.dart';
import 'package:nyoba/services/session.dart';
import 'package:provider/provider.dart';

import '../models/coupon_model.dart';
import '../utils/utility.dart';

class CouponAPI {
  fetchListCoupon(page, BuildContext context, {String? productId = ""}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    var response = await newUrl.newCustomBaseAPI.getAsync(
        '$coupon?page=$page&per_page=50&product_id=$productId',
        isCustom: true,
        headersTranslate: 'coupon');
    return response;
  }

  searchCoupon(code, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    var response = await newUrl.newCustomBaseAPI.getAsync(
        '$coupon?code=$code&page=1&per_page=1',
        headersTranslate: 'coupon');
    return response;
  }

  newSearchCoupon(
      {List<SearchCouponModel>? products,
      String? code,
      required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      'cookie': Session.data.getString('cookie'),
      'coupon_code': code,
      'products': products
    };
    printLog("data request use coupon : ${json.encode(data)}");
    var response = await newUrl.postAsync('$applyCoupon', data, isCustom: true);
    printLog("use coupon : ${json.encode(response)}");
    return response;
  }
}
