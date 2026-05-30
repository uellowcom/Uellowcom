import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class BannerAPI {
  fetchBanner(BuildContext context) async {
    final url = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await url.getAsync('$banner', isCustom: true);
    return response;
  }

  fetchMiniBanner({String isBlog = '', required BuildContext context}) async {
    final url = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await url.getAsync('$homeMiniBanner?blog_banner=$isBlog',
        isCustom: true);
    return response;
  }
}
