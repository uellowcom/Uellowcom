import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class ReviewAPI {
  historyReview(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {
      "cookie": Session.data.getString('cookie'),
    };
    printLog(data.toString());
    var response = await newUrl.newCustomBaseAPI.postAsync(
        '$historyReviewUrl', data,
        isCustom: true, headersTranslate: 'review');
    return response;
  }

  inputReview(productId, review, rating, reviewTitle, caption,
      {List<File>? image,
      String name = "",
      String email = "",
      required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      "product_id": productId,
      "comments": review,
      "cookie": Session.data.getString('cookie') ?? "",
      "rating": rating,
      "review_title": reviewTitle,
      "caption": caption,
      if (image != null) "media[]": image,
      if (name != "") "author_name": name,
      if (email != "") "author_email": email
    };
    printLog(data.toString());
    var response = await newUrl.postAsync('$addReviewUrl', data,
        isCustom: true, isReview: true);
    printLog(json.encode(response), name: "Response Review");
    return response;
  }

  limitReview(productId, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {
      "post_id": productId,
      // "page": "0",
      // "limit": "1",
    };
    printLog(data.toString(), name: "data review");
    var response = await newUrl.newCustomBaseAPI.postAsync(
        '$historyReviewUrl', data,
        isCustom: true, printedLog: true, headersTranslate: 'review');
    return response;
  }

  productReview(productId, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {
      "post_id": productId,
    };
    printLog(data.toString());
    var response = await newUrl.newCustomBaseAPI.postAsync(
        '$historyReviewUrl', data,
        isCustom: true, headersTranslate: 'review');
    return response;
  }
}
