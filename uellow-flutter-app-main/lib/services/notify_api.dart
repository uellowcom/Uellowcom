import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class NotifyAPI {
  fetchNotify(
      {String? name,
      String? email,
      String? productId,
      required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      "subscriber_name": name,
      "email": email,
      "product_id": productId,
      "status": "cwg_subscribed"
    };
    var response = newUrl.postAsync(
      notifyMe,
      data,
      printedLog: true,
      isNotify: true,
    );
    return response;
  }
}
