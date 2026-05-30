import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/services/session.dart';
import 'package:provider/provider.dart';

import '../constant/constants.dart';
import '../constant/global_url.dart';
import '../provider/urlProvider.dart';
import '../utils/utility.dart';

class WalletAPI {
  webViewWallet(type, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      "payment_method": "xendit_bniva",
      "payment_method_title": "Bank Transfer - BNI",
      "set_paid": true,
      "line_items": [],
      "customer_id": Session.data.getInt('id'),
      "status": "completed",
      "coupon_lines": [],
      "wallet_tab": type,
      "token": Session.data.getString('cookie'),
      "wallet_lang": Session.data.getString('language_code'),
    };

    printLog("${jsonEncode(data)} data wallet link");
    final jsonOrder = json.encode(data);
    printLog(jsonOrder, name: 'Json Order');

    //Convert Json to bytes
    var bytes = utf8.encode(jsonOrder);
    //Convert bytes to base64
    var order = base64.encode(bytes);

    var response =
        await newUrl.getAsync('$orderApi?order=$order', isOrder: true);
    return response;
  }

  listTransaction(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();

    String id = Session.data.getInt('id').toString();
    var response = await newUrl.newCustomBaseAPI.getAsync(
      '$transactionWalletUrl/history/$id',
      isCustom: true,
      headersTranslate: "wallet",
    );
    return response;
  }

  balance(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    String id = Session.data.getInt('id').toString();
    var response = await newUrl.getAsync('$balanceWalletUrl/$id',
        version: 2, isCustom: true);
    return response;
  }
}
