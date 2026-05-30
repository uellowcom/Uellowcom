import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/provider/urlProvider.dart';
import 'package:provider/provider.dart';

class FlashSaleAPI {
  fetchHomeFlashSale(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await newUrl.getAsync('$homeFlashSale', isCustom: true);
    return response;
  }

  fetchFlashSaleProducts(String productId, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await newUrl.getAsync('$product?include=$productId');
    return response;
  }
}
