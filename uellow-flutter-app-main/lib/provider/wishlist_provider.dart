import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/services/product_api.dart';
import 'package:nyoba/services/wishlist_api.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../app_localizations.dart';

class WishlistProvider with ChangeNotifier {
  bool loadingWishlist = true;

  String? message;

  List<ProductModel> listWishlistProduct = [];

  String? productWishlist;

  // final HomeProvider homeProvider = HomeProvider();

  Future<bool> fetchWishlistProducts(
      String productId, BuildContext context) async {
    if (productId.isNotEmpty) {
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

          printLog(responseJson.toString(), name: 'Wishlist');
          listWishlistProduct.clear();
          for (Map item in responseJson) {
            listWishlistProduct.add(ProductModel.fromJson(item));
          }
          loadingWishlist = false;
          notifyListeners();
        } else {
          print("Load Failed");
          loadingWishlist = false;
          notifyListeners();
        }
      });
    } else {
      loadingWishlist = false;
      notifyListeners();
    }
    return true;
  }

  Future<Map<String, dynamic>?> checkWishlistProduct(
      {productId, required BuildContext context}) async {
    var result;
    await WishlistAPI()
        .setWishlist(productId, check: true, context: context)
        .then((data) {
      result = data;
      notifyListeners();
      printLog(result.toString());
    });
    return result;
  }

  Future<Map<String, dynamic>?> setWishlistProduct(context, {productId}) async {
    var result;
    await WishlistAPI().setWishlist(productId, context: context).then((data) {
      result = data;

      if (result['message'] == 'success') {
        if (result['type'] == 'add') {
          snackBar(context,
              message: AppLocalizations.of(context)!
                  .translate('wishlist_add_message')!);
        } else {
          snackBar(context,
              message: AppLocalizations.of(context)!
                  .translate('wishlist_remove_message')!);
        }
      } else {
        snackBar(context,
            message: AppLocalizations.of(context)!
                .translate('error_submit_message')!,
            color: Colors.red);
      }

      notifyListeners();
      printLog(result.toString());
    });
    return result;
  }

  Future<Map<String, dynamic>?> loadWishlistProduct(
      {productId, required BuildContext context}) async {
    loadingWishlist = true;
    var result;
    await WishlistAPI().fetchProductWishlist(context).then((data) {
      result = data;
      productWishlist = result['products'];
      notifyListeners();
      printLog(result.toString(), name: "Wishlist Products");
    });
    return result;
  }

  List<ProductModel> listProductWishlistAccount = [];

  Future<void> loadAccountWishlist(BuildContext context) async {
    loadingWishlist = true;
    notifyListeners();
    await WishlistAPI().fetchAccountWishlist(context).then((data) {
      printLog(json.encode(data), name: "Wishlist Account");
      if (data != null) {
        listProductWishlistAccount.clear();
        data.forEach((v) {
          listProductWishlistAccount.add(ProductModel.fromJson(v));
        });
        loadingWishlist = false;
        notifyListeners();
      }
    });
  }
}
