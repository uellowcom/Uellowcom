import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class LoginAPI {
  loginByDefault(
      String? username, String? password, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {'username': username, 'password': password};
    var response = await newUrl.postAsync(
      '$loginDefault',
      data,
      isCustom: true,
    );
    return response;
  }

  loginByOTP(phone, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response =
        await newUrl.getAsync('$signInOTP?phone=$phone', isCustom: true);
    return response;
  }

  loginByGoogle(token, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await newUrl.getAsync('$signInGoogle?access_token=$token',
        isCustom: true, printedLog: true);
    return response;
  }

  loginByFacebook(token, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await newUrl.getAsync('$signInFacebook?access_token=$token',
        isCustom: true);
    return response;
  }

  loginByApple(email, displayName, userName,
      {username1, required BuildContext context}) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      'email': email,
      'display_name': displayName,
      'user_name': userName,
      'username': username1
    };
    printLog("${jsonEncode(data)}", name: "data login apple");
    var response = await newUrl.postAsync('$signInApple', data,
        isCustom: true, printedLog: true);
    return response;
  }

  inputTokenAPI(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      'token': Session.data.getString('device_token'),
      'cookie': Session.data.getString('cookie')
    };
    printLog(data.toString(), name: 'Token Firebase');
    var response = await newUrl.postAsync(
      '$inputTokenUrl',
      data,
      isCustom: true,
    );
    return response;
  }

  forgotPasswordAPI(String? email, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {'email': email};
    var response = await newUrl.postAsync(
      '$forgotPasswordUrl',
      data,
      isCustom: true,
    );
    return response;
  }
}
