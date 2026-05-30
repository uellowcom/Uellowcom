import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'dart:convert';
import 'package:nyoba/services/flash_sale_api.dart';
import 'package:nyoba/models/flash_sale_model.dart';

import 'package:nyoba/services/product_api.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

class FlashSaleProvider with ChangeNotifier {
  FlashSaleModel? flashSale;
  bool loading = true;
  List<FlashSaleModel> flashSales = [];
  List<ProductModel> flashSaleProducts = [];

  final HomeProvider homeProvider = HomeProvider();

  FlashSaleProvider(BuildContext context) {
    fetchFlashSale(context);
  }

  Future<bool> fetchFlashSale(BuildContext context) async {
    loading = true;
    await FlashSaleAPI().fetchHomeFlashSale(context).then((data) async {
      printLog("Fetching FS", name: "FlashSale");
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);
        printLog(responseJson.toString(), name: 'FlashSale Response');
        for (Map item in responseJson) {
          flashSales.add(FlashSaleModel.fromJson(item));
        }
        loading = false;
        notifyListeners();
        if (flashSales.isNotEmpty) {
          fetchFlashSaleProducts(flashSales.first.products!, context);
        }
      } else {
        loading = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchFlashSaleProducts(
      String productId, BuildContext context) async {
    loading = true;
    String country = base64Encode(
        utf8.encode(context.read<ProductProvider>().currentPosition));
    await ProductAPI()
        .fetchProduct(
      include: productId,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        flashSaleProducts.clear();
        for (Map item in responseJson) {
          flashSaleProducts.add(ProductModel.fromJson(item));
        }
        loading = false;

        notifyListeners();
      } else {
        print("Load Failed");
        loading = false;
        notifyListeners();
      }
    });
    return true;
  }
}
