import 'package:flutter/material.dart';
import 'package:nyoba/utils/utility.dart';

import '../services/base_woo_api.dart';
import '../services/session.dart';

class UrlProvider extends ChangeNotifier {
  String appId = '1627419775';
  String url = "https://app.uellow.com";
  String newCustomUrl = 'https://app.uellow.com';

// oauth_consumer_key
  String consumerKey = "ck_9e0de31e898d5571f1d1d6295a2151eb0241c5bc";
  String consumerSecret = "cs_d0cbbe0ccb6c29b2f31c94128a4a44104c824817";

// String version = '2.5.6';

// baseAPI for WooCommerce
  BaseWooAPI baseAPI = BaseWooAPI(
      "https://app.uellow.com",
      "ck_9e0de31e898d5571f1d1d6295a2151eb0241c5bc",
      "cs_d0cbbe0ccb6c29b2f31c94128a4a44104c824817");
  BaseWooAPI newCustomBaseAPI = BaseWooAPI(
      "https://app.uellow.com",
      "ck_9e0de31e898d5571f1d1d6295a2151eb0241c5bc",
      "cs_d0cbbe0ccb6c29b2f31c94128a4a44104c824817");

  changeUrl() {
    printLog("${Session.data.containsKey('language_code')}",
        name: "language code");
    // printLog(message)
    if (Session.data.containsKey('language_code') == false ||
        Session.data.getString('language_code') == 'en') {
      newCustomUrl = 'https://app.uellow.com';
    } else {
      newCustomUrl =
          "https://app.uellow.com";
    }

    newCustomBaseAPI = BaseWooAPI(newCustomUrl, consumerKey, consumerSecret);
    printLog("$newCustomUrl", name: "NEW URL");
    notifyListeners();
  }
}
