import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/services/notify_api.dart';
import 'package:nyoba/utils/utility.dart';

class NotifyProvider with ChangeNotifier {
  bool loadingNotify = false;
  bool isNotifySucceed = true;
  fetchNotifyme(
      {required String name,
      required String email,
      required String productId,
      required BuildContext context}) async {
    loadingNotify = true;
    await NotifyAPI()
        .fetchNotify(
            name: name, email: email, productId: productId, context: context)
        .then((data) {
      var result = data;
      printLog(jsonEncode(result['message']), name: "message");
      if (result["message"] != null) {
        printLog("masuk gagal");
        isNotifySucceed = false;
        notifyListeners();
      } else {
        isNotifySucceed = true;
        notifyListeners();
      }
      loadingNotify = false;
      notifyListeners();
    });
  }
}
