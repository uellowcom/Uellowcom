import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/provider/urlProvider.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

class NotificationAPI {
  notification(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {
      "cookie": Session.data.getString('cookie'),
    };
    printLog(data.toString());
    var response = await newUrl.newCustomBaseAPI.postAsync(
        '$notificationUrl', data,
        isCustom: true, headersTranslate: 'notification');
    return response;
  }

  readNotification(int id, String type, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      "cookie": Session.data.getString('cookie'),
      "id": id,
      "type": type,
    };
    printLog(data.toString(), name: "data notif");
    var response =
        await newUrl.postAsync(readNotificationUrl, data, isCustom: true);
    return response;
  }
}
