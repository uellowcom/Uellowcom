import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:nyoba/models/currency_model.dart';
import 'package:nyoba/models/general_settings_model.dart';
import 'dart:convert';
import 'package:nyoba/services/general_settings_api.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';

class GeneralSettingsProvider with ChangeNotifier {
  List<GeneralSettingsModel> intro = [];

  GeneralSettingsModel splashscreen = new GeneralSettingsModel();
  GeneralSettingsModel logo = new GeneralSettingsModel();
  GeneralSettingsModel wa = new GeneralSettingsModel();
  GeneralSettingsModel sms = new GeneralSettingsModel();
  GeneralSettingsModel phone = new GeneralSettingsModel();
  GeneralSettingsModel about = new GeneralSettingsModel();
  GeneralSettingsModel currency = new GeneralSettingsModel();
  GeneralSettingsModel formatCurrency = new GeneralSettingsModel();
  GeneralSettingsModel privacy = new GeneralSettingsModel();

  GeneralSettingsModel image404 = new GeneralSettingsModel();
  GeneralSettingsModel imageThanksOrder = new GeneralSettingsModel();
  GeneralSettingsModel imageNoTransaction = new GeneralSettingsModel();
  GeneralSettingsModel imageSearchEmpty = new GeneralSettingsModel();

  bool loading = false;
  bool? isBarcodeActive = false;
  String? message;

  GeneralSettingsProvider(BuildContext context) {
    fetchGeneralSettings(context);
  }

  Future<Map<String, dynamic>?> fetchIntroPage(BuildContext context) async {
    Map<String, dynamic>? appConfig;
    try {
      loading = true;
      await GeneralSettingsAPI().introPageData(context).then((data) {
        if (data.statusCode == 200) {
          final responseJson = json.decode(data.body);

          appConfig = responseJson;
          splashscreen =
              GeneralSettingsModel.fromJson(responseJson['splashscreen']);
          for (Map item in responseJson['intro']) {
            intro.add(GeneralSettingsModel.fromJson(item));
          }
          loading = false;
          notifyListeners();
        } else {
          loading = false;
          notifyListeners();
        }
      });
      return appConfig;
    } catch (e) {
      printLog(e.toString());
      return appConfig;
    }
  }

  Future<bool> fetchGeneralSettings(BuildContext context) async {
    loading = true;
    await GeneralSettingsAPI().generalSettingsData(context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);

        for (Map item in responseJson['empty_image']) {
          if (item['title'] == '404_images') {
            image404 = GeneralSettingsModel.fromJson(item);
          } else if (item['title'] == 'thanks_order') {
            imageThanksOrder = GeneralSettingsModel.fromJson(item);
          } else if (item['title'] == 'no_transaksi') {
            imageNoTransaction = GeneralSettingsModel.fromJson(item);
          } else if (item['title'] == 'search_empty') {
            imageSearchEmpty = GeneralSettingsModel.fromJson(item);
          }
        }

        logo = GeneralSettingsModel.fromJson(responseJson['logo']);
        wa = GeneralSettingsModel.fromJson(responseJson['wa']);
        sms = GeneralSettingsModel.fromJson(responseJson['sms']);
        phone = GeneralSettingsModel.fromJson(responseJson['phone']);
        about = GeneralSettingsModel.fromJson(responseJson['about']);
        currency = GeneralSettingsModel.fromJson(responseJson['currency']);
        formatCurrency =
            GeneralSettingsModel.fromJson(responseJson['format_currency']);
        privacy = GeneralSettingsModel.fromJson(responseJson['privacy_policy']);

        if (responseJson['barcode_active'] != null) {
          isBarcodeActive = responseJson['barcode_active'];
        }

        loading = false;
        notifyListeners();
      } else {
        loading = false;
        notifyListeners();
      }
    });
    return true;
  }

  bool loadingCurrency = false;
  List<CurrencyModel> listCurrency = [];
  CurrencyModel? selectedCurrency;
  int selectedCurrencyIndex = 0;
  String activeCurrency = "";

  setCurrency(val) {
    Session.data.setString('currency_code', val);
    activeCurrency = val;
    listCurrency.forEach((v) {
      if (v.name == val) {
        selectedCurrency = v;
        notifyListeners();
      }
    });
    // selectedCurrency = val;
    notifyListeners();
  }

  Future<void> loadAllCurrency(BuildContext context) async {
    loadingCurrency = true;
    notifyListeners();
    printLog("Fetching Currency");
    await GeneralSettingsAPI().getCurrency(context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);

        if (responseJson != null) {
          listCurrency.clear();
          responseJson.forEach((v) {
            listCurrency.add(CurrencyModel.fromJson(v));
            if (v['name'] == Session.data.getString('currency_code')) {
              selectedCurrency = CurrencyModel.fromJson(v);
            }
          });
          printLog("Currency loaded");
          loadingCurrency = false;
          notifyListeners();
        }
      }
    });
  }
}
