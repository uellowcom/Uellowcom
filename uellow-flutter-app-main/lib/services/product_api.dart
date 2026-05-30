import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/models/attribute_filter_model.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class ProductAPI {
  fetchProduct(
      {String include = '',
      bool? featured,
      int page = 1,
      int perPage = 8,
      String parent = '',
      String search = '',
      String category = '',
      String productId = '',
      String slug = '',
      required String? country,
      required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    await newUrl.changeUrl();
    Map data = {
      if (include.isNotEmpty) "include": include,
      "page": page,
      "per_page": perPage,
      if (parent.isNotEmpty) "parent": parent,
      if (search.isNotEmpty) "search": search,
      if (category.isNotEmpty) "category": category,
      if (slug.isNotEmpty) "slug": slug,
      if (productId.isNotEmpty) "id": productId,
      if (featured != null) "featured": featured,
      "country": country,
    };

    printLog(data.toString(), name: "Data Param Product");

    var response = await newUrl.newCustomBaseAPI.postAsync(
        customProductUrl, data,
        isCustom: true, headersTranslate: 'list-product');
    // printLog("${jsonEncode(response)}", name: "response new product");
    return response;
  }

  fetchExtendProduct(String type, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response =
        await newUrl.getAsync('$extendProducts?type=$type', isCustom: true);
    return response;
  }

  fetchRecentViewProducts(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {"cookie": Session.data.getString('cookie')};
    var response =
        await newUrl.postAsync('$recentProducts', data, isCustom: true);
    printLog(Session.data.getString('cookie')!);
    return response;
  }

  hitViewProductsAPI(productId, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    await newUrl.changeUrl();
    Map data = {
      "cookie": Session.data.getString('cookie'),
      "product_id": productId,
      "ip_address": Session.data.getString('ip'),
    };
    var response = await newUrl.newCustomBaseAPI.postAsync(
        '$hitViewedProducts', data,
        isCustom: true, headersTranslate: 'list-product');
    printLog(Session.data.getString('cookie')!);
    return response;
  }

  fetchDetailProduct({
    String? productId,
    required BuildContext context,
    required String? country,
  }) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    await newUrl.changeUrl();
    Map data = {
      "id": productId,
      "country": country,
    };
    printLog("${jsonEncode(data)} ", name: "data product api");
    var response = await newUrl.newCustomBaseAPI.postAsync(
        customProductUrl, data,
        isCustom: true, headersTranslate: 'list-product', printedLog: true);
    printLog("${jsonEncode(response)} ", name: "response product api");
    return response;
  }

  fetchDetailProductSlug(String? slug, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    await newUrl.changeUrl();
    Map data = {"slug": slug};
    var response = await newUrl.newCustomBaseAPI.postAsync(
        customProductUrl, data,
        isCustom: true, headersTranslate: 'list-product');
    return response;
  }

  searchProduct(
      {String search = '',
      String category = '',
      int? page,
      required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    await newUrl.changeUrl();
    Map data = {
      "page": page,
      if (search.isNotEmpty) "search": search,
      if (category.isNotEmpty) "category": category,
    };
    var response = await newUrl.newCustomBaseAPI.postAsync(
        customProductUrl, data,
        isCustom: true, headersTranslate: 'list-product');
    return response;
  }

  checkVariationProduct(int? productId, List<ProductVariation>? list,
      BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {"product_id": productId, "variation": list};
    printLog("${jsonEncode(data)}", name: "data check variation");
    var response = await newUrl.postAsync(
      '$checkVariations',
      data,
      isCustom: true,
    );
    return response;
  }

  fetchBrandProduct({
    int? page = 1,
    int perPage = 8,
    String search = '',
    String? category = '',
    String? order = 'desc',
    String? orderBy = 'popularity',
    String? slug,
    List<AttributeFilter>? attributeFilter,
    required BuildContext context,
    required String? country,
  }) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    await newUrl.changeUrl();
    Map data = {
      "page": page,
      "per_page": perPage,
      "order": order,
      "order_by": orderBy,
      "slug_category": slug,
      if (search.isNotEmpty) "search": search,
      if (category!.isNotEmpty) "category": category,
      if (attributeFilter != null && attributeFilter.isNotEmpty)
        "attribute": attributeFilter,
      "country": country,
    };

    printLog("${jsonEncode(data)}", name: 'Param Brand');
    var response = await newUrl.newCustomBaseAPI.postAsync(
        customProductUrl,
        headersTranslate: 'list-product',
        data,
        isCustom: true);
    return response;
  }

  reviewProduct({String productId = '', required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response =
        await newUrl.getAsync('$reviewProductUrl?product=$productId');
    return response;
  }

  reviewProductLimit(
      {String productId = '', required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await newUrl
        .getAsync('$reviewProductUrl?product=$productId&per_page=1&page=1');
    return response;
  }

  fetchMoreProduct({
    int? page = 1,
    int perPage = 6,
    String search = '',
    String? include = '',
    String category = '',
    String order = 'desc',
    String? orderBy = 'popularity',
    bool? featured,
    required BuildContext context,
    required String? country,
  }) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    await newUrl.changeUrl();
    Map data = {
      if (include!.isNotEmpty) "include": include,
      "page": page,
      "per_page": perPage,
      if (search.isNotEmpty) "search": search,
      if (category.isNotEmpty) "category": category,
      "order": order,
      "order_by": orderBy,
      if (featured != null) "featured": featured,
      "country": country,
    };

    printLog(data.toString(), name: "Data Param Product");

    var response = await newUrl.newCustomBaseAPI.postAsync(
        customProductUrl,
        headersTranslate: 'list-product',
        data,
        isCustom: true);

    return response;
  }

  scanProductAPI(String? code, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {"code": code};
    printLog(data.toString());
    var response = await newUrl.postAsync(
      '$getBarcodeUrl',
      data,
      isCustom: true,
    );
    return response;
  }

  productVariations(
      {String? productId = '', required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await newUrl.getAsync('$product/$productId/variations');
    return response;
  }

  filterData(String? category, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {"category": category};
    var response = await newUrl.newCustomBaseAPI.postAsync(
        '$dataFilterAttr', data,
        isCustom: true, headersTranslate: 'filters');
    return response;
  }

  fetchHistory(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {"cookie": Session.data.getString('cookie')};
    var response = await newUrl.newCustomBaseAPI.postAsync(
        'products/recently-views', data,
        isCustom: true, headersTranslate: 'wishlist-account');
    return response;
  }

  fetchProductForm(
      {required String name,
      required String email,
      required String subject,
      required String message,
      int? id,
      required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var data;
    if (id != null) {
      data = {
        "name": name,
        "email": email,
        "subject": subject,
        "message": message,
        "product_id": id,
      };
    } else {
      data = {
        "name": name,
        "email": email,
        "subject": subject,
        "message": message,
      };
    }
    printLog("${jsonEncode(data)}");
    var response = await newUrl.postAsync("products/ask", data, isCustom: true);
    return response;
  }

  fetchProductShippingMethod({
    required String? country,
    String? productId,
    int? qty = 1,
    required BuildContext context,
  }) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {
      "cookie": Session.data.getString("cookie") ?? "",
      "country": country,
      "product_id": productId,
      "quantity": qty
    };
    printLog(json.encode(data), name: "Data Fetch Shipping Method");
    var response = await newUrl.newCustomBaseAPI.postAsync(
        'a2w/product-shipping-methods', data,
        isCustom: true, printedLog: true, headersTranslate: 'shipping-methods');
    return response;
  }

  cartApplyShippingMethods(String country, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      'cookie': Session.data.getString('cookie') ?? "",
      'country_code': country
    };
    printLog(json.encode(data), name: "Data Cart Apply");
    var response = await newUrl.postAsync(
        'a2w/cart-apply-shipping-methods', data,
        isCustom: true, printedLog: true);
    return response;
  }
}
