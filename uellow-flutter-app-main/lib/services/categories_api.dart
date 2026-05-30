import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class CategoriesAPI {
  fetchCategories(
      {String showPopular = '', required BuildContext context}) async {
    final url = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await url.getAsync('$category?show_popular=$showPopular',
        isCustom: true);
    return response;
  }

  fetchProductCategories(
      {int? parent, page, required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {"parent": parent};
    var response = await newUrl.newCustomBaseAPI.postAsync(
        '$allCategoriesUrl', data,
        isCustom: true, headersTranslate: 'list-categories');
    // var url = productCategories;
    // if (parent != null) {
    //   url = '$productCategories?parent=$parent&page=$page';
    // }
    // var response = await newUrl.newCustomBaseAPI
    //     .getAsync('$url', headersTranslate: 'subcategory', printedLog: true);
    return response;
  }

  fetchPopularCategories(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    var response = await newUrl.newCustomBaseAPI.getAsync('$popularCategories',
        isCustom: true, headersTranslate: 'popular-categories');
    return response;
  }

  fetchAllCategories(BuildContext context, bool isFromSplashScreen,
      {int? count}) async {
    if (isFromSplashScreen == true &&
        Session.data.containsKey('language_code') == false) {
      printLog("masuk else fetch all categories");
      final newUrl = Provider.of<UrlProvider>(context, listen: false);
      newUrl.changeUrl();
      Map data = {'parent': count};
      printLog(data.toString());
      var response = await newUrl.newCustomBaseAPI.postAsync(
          '$allCategoriesUrl', data,
          isCustom: true, headersTranslate: 'list-categories');
      return response;
    } else {
      printLog("masuk else fetch all categories");
      final newUrl = Provider.of<UrlProvider>(context, listen: false);
      await newUrl.changeUrl();
      Map data = {'parent': count};
      printLog(data.toString());
      var response = await newUrl.newCustomBaseAPI.postAsync(
          '$allCategoriesUrl', data,
          isCustom: true, headersTranslate: 'list-categories');
      return response;
    }
  }
}
