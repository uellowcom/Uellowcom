import 'dart:convert';

import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:nyoba/models/notification_model.dart';
import 'package:nyoba/services/notification_api.dart';
import 'package:nyoba/utils/utility.dart';

class NotificationProvider with ChangeNotifier {
  bool isLoading = false;
  List<NotificationModel> notification = [];
  List unreadNotification = [];

  fetchReadNotif(int id, String type, BuildContext context) async {
    printLog("masuk fecth read notif");
    var result;
    await NotificationAPI().readNotification(id, type, context).then((data) {
      result = data;
      printLog(result.toString(), name: "Hasil read notif");
    });
  }

  Future<List?> fetchNotifications(
      {status, search, required BuildContext context}) async {
    isLoading = !isLoading;
    var result;
    await NotificationAPI().notification(context).then((data) {
      result = data;
      notification.clear();
      unreadNotification.clear();
      printLog("${jsonEncode(result)}", name: "result notification");

      for (Map item in result) {
        notification.add(NotificationModel.fromJson(item));
      }

      for (var notif in notification) {
        if (notif.isRead == 0) {
          unreadNotification.add(notif);
        }
      }

      isLoading = !isLoading;
      notifyListeners();
      printLog(result.toString());
    });
    return result;
  }
}
