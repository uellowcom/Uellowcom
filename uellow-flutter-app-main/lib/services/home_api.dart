import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/services/session.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class HomeAPI {
  homeDataApi(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    await newUrl.changeUrl();
    var lang = Session.data.getString('language_code') ?? "en";
    final country = base64Encode(
        utf8.encode(context.read<ProductProvider>().currentPosition));
    var response = await newUrl.newCustomBaseAPI.getAsync(
        '$homeUrl?currency=${Session.data.getString('currency_code')}&lang=$lang&country=$country',
        isCustom: true,
        isHomeAPI: true,
        headersTranslate: 'home-api',
        printedLog: true);
    return response;
  }

  discRuleData(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response =
        await newUrl.getAsync('$discUrl', isCustom: true, printedLog: true);
    return response;
  }
}
