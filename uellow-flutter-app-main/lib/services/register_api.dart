import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class RegisterAPI {
  register(String? firstName, String? lastName, String? email, String? username,
      String? password, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      "user_email": email,
      "user_login": username,
      "username": username,
      "user_pass": password,
      "email": email,
      "first_name": firstName,
      "last_name": lastName
    };
    var response = await newUrl.postAsync(
      '$signUp',
      data,
      isCustom: true,
    );
    return response;
  }
}
