import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class WishlistAPI {
  checkWishlist(int productId, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {'product_id': productId};
    var response = await newUrl.postAsync(
      '$checkWishlistProduct',
      data,
      isCustom: true,
    );
    return response;
  }

  setWishlist(String? productId,
      {bool check = false, required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      'product_id': productId,
      if (Session.data.getString('cookie') != null)
        'cookie': Session.data.getString('cookie'),
      'check': check
    };
    var response = await newUrl.postAsync(
      '$setWishlistProduct',
      data,
      isCustom: true,
    );
    return response;
  }

  fetchProductWishlist(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      'cookie': Session.data.getString('cookie'),
    };
    var response = await newUrl.postAsync(
      '$listWishlistProduct',
      data,
      isCustom: true,
    );
    return response;
  }

  fetchAccountWishlist(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {'cookie': Session.data.getString('cookie')};
    var response = await newUrl.newCustomBaseAPI.postAsync(
        'wishlist/get-products', data,
        isCustom: true, printedLog: true, headersTranslate: 'wishlist-account');
    return response;
  }
}
