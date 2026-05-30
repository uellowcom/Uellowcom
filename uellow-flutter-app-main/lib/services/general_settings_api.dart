import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:provider/provider.dart';

import '../provider/urlProvider.dart';

class GeneralSettingsAPI {
  introPageData(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await newUrl.getAsync(
      '$introPage',
      isCustom: true,
    );
    return response;
  }

  generalSettingsData(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await newUrl.getAsync(
      '$generalSetting',
      isCustom: true,
    );
    return response;
  }

  getCurrency(BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await newUrl.getAsync('woocs/currencies',
        isCustom: true, printedLog: true);
    return response;
  }
}
