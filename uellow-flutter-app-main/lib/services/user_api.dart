import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class UserAPI {
  fetchDetail(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    newUrl.changeUrl();
    Map data = {"cookie": Session.data.get('cookie')};
    var response = await newUrl.newCustomBaseAPI.postAsync('$userDetail', data,
        isCustom: true, headersTranslate: 'points');
    return response;
  }

  updateUserInfo(
      {String? firstName,
      String? lastName,
      String? email,
      required String password,
      String? oldPassword,
      required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      "cookie": Session.data.get('cookie'),
      "first_name": firstName,
      "last_name": lastName,
      "user_email": email,
      if (password.isNotEmpty) "user_pass": password,
      if (password.isNotEmpty) "old_pass": oldPassword
    };
    printLog("${jsonEncode(data)}", name: "Data Update User");
    var response = await newUrl.postAsync('$updateUser', data,
        isCustom: true, printedLog: true);
    return response;
  }
}
