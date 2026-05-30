import 'package:flutter/material.dart';
import 'package:nyoba/app_theme/storage_manager.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/provider/urlProvider.dart';
import 'package:nyoba/provider/wishlist_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppNotifier extends ChangeNotifier {
  Locale _appLocale = Locale('en');
  bool isDarkMode = false;

  int? selectedLocaleIndex = 0;

  Locale get appLocal => _appLocale;

  ThemeData? _themeData;
  ThemeData? getTheme() => _themeData;

  AppNotifier() {
    StorageManager.readData('themeMode').then((value) {
      print('value read from storage: ' + value.toString());
      var themeMode = value ?? 'light';
      if (themeMode == 'light') {
        _themeData = lightTheme;
        isDarkMode = false;
      } else if (themeMode == 'lightAr') {
        _themeData = lightThemeAr;
        isDarkMode = false;
      } else {
        print('setting dark theme');
        _themeData = darkTheme;
        isDarkMode = true;
      }
      notifyListeners();
    });
  }

  fetchLocale() async {
    var prefs = await SharedPreferences.getInstance();
    if (prefs.getString('language_code') == null) {
      _appLocale = Locale('en');
      return Null;
    }
    if (prefs.getInt('localeIndex') == null) {
      selectedLocaleIndex = 0;
      return Null;
    }
    _appLocale = Locale(prefs.getString('language_code')!);
    selectedLocaleIndex = prefs.getInt('localeIndex');
    return Null;
  }

  void changeLanguage(Locale type, BuildContext context) async {
    final newUrl = Provider.of<UrlProvider>(context, listen: false);
    var prefs = await SharedPreferences.getInstance();
    if (_appLocale == type) {
      return;
    }
    if (type == Locale("en")) {
      _appLocale = Locale("en");
      selectedLocaleIndex = 0;
      await prefs.setString("language_code", "en");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ar")) {
      _appLocale = Locale("ar");
      selectedLocaleIndex = 1;
      await prefs.setString("language_code", "ar");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("fr")) {
      _appLocale = Locale("fr");
      selectedLocaleIndex = 2;
      await prefs.setString("language_code", "fr");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("af")) {
      _appLocale = Locale("af");
      selectedLocaleIndex = 3;
      await prefs.setString("language_code", "af");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("so")) {
      _appLocale = Locale("so");
      selectedLocaleIndex = 4;
      await prefs.setString("language_code", "so");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("az")) {
      _appLocale = Locale("az");
      selectedLocaleIndex = 5;
      await prefs.setString("language_code", "az");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("id")) {
      _appLocale = Locale("id");
      selectedLocaleIndex = 6;
      await prefs.setString("language_code", "id");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ms")) {
      _appLocale = Locale("ms");
      selectedLocaleIndex = 7;
      await prefs.setString("language_code", "ms");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("bs")) {
      _appLocale = Locale("bs");
      selectedLocaleIndex = 8;
      await prefs.setString("language_code", "bs");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ca")) {
      _appLocale = Locale("ca");
      selectedLocaleIndex = 9;
      await prefs.setString("language_code", "ca");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ny")) {
      _appLocale = Locale("ny");
      selectedLocaleIndex = 10;
      await prefs.setString("language_code", "ny");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("co")) {
      _appLocale = Locale("co");
      selectedLocaleIndex = 11;
      await prefs.setString("language_code", "co");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("cy")) {
      _appLocale = Locale("cy");
      selectedLocaleIndex = 12;
      await prefs.setString("language_code", "cy");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("da")) {
      _appLocale = Locale("da");
      selectedLocaleIndex = 13;
      await prefs.setString("language_code", "da");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("de")) {
      _appLocale = Locale("de");
      selectedLocaleIndex = 14;
      await prefs.setString("language_code", "de");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("et")) {
      _appLocale = Locale("et");
      selectedLocaleIndex = 15;
      await prefs.setString("language_code", "et");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("es")) {
      _appLocale = Locale("es");
      selectedLocaleIndex = 16;
      await prefs.setString("language_code", "es");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("eo")) {
      _appLocale = Locale("eo");
      selectedLocaleIndex = 17;
      await prefs.setString("language_code", "eo");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("eu")) {
      _appLocale = Locale("eu");
      selectedLocaleIndex = 18;
      await prefs.setString("language_code", "eu");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("tl")) {
      _appLocale = Locale("tl");
      selectedLocaleIndex = 19;
      await prefs.setString("language_code", "tl");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("fy")) {
      _appLocale = Locale("fy");
      selectedLocaleIndex = 20;
      await prefs.setString("language_code", "fy");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ga")) {
      _appLocale = Locale("ga");
      selectedLocaleIndex = 21;
      await prefs.setString("language_code", "ga");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("gl")) {
      _appLocale = Locale("gl");
      selectedLocaleIndex = 22;
      await prefs.setString("language_code", "gl");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("gd")) {
      _appLocale = Locale("gd");
      selectedLocaleIndex = 23;
      await prefs.setString("language_code", "gd");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ha")) {
      _appLocale = Locale("ha");
      selectedLocaleIndex = 24;
      await prefs.setString("language_code", "ha");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("hr")) {
      _appLocale = Locale("hr");
      selectedLocaleIndex = 25;
      await prefs.setString("language_code", "hr");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ig")) {
      _appLocale = Locale("ig");
      selectedLocaleIndex = 26;
      await prefs.setString("language_code", "ig");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("it")) {
      _appLocale = Locale("it");
      selectedLocaleIndex = 27;
      await prefs.setString("language_code", "it");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("sw")) {
      _appLocale = Locale("sw");
      selectedLocaleIndex = 28;
      await prefs.setString("language_code", "sw");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ht")) {
      _appLocale = Locale("ht");
      selectedLocaleIndex = 29;
      await prefs.setString("language_code", "ht");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("la")) {
      _appLocale = Locale("la");
      selectedLocaleIndex = 30;
      await prefs.setString("language_code", "la");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("lv")) {
      _appLocale = Locale("lv");
      selectedLocaleIndex = 31;
      await prefs.setString("language_code", "lv");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("lt")) {
      _appLocale = Locale("lt");
      selectedLocaleIndex = 32;
      await prefs.setString("language_code", "lt");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("lb")) {
      _appLocale = Locale("lb");
      selectedLocaleIndex = 33;
      await prefs.setString("language_code", "lb");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("hu")) {
      _appLocale = Locale("hu");
      selectedLocaleIndex = 34;
      await prefs.setString("language_code", "hu");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("mg")) {
      _appLocale = Locale("mg");
      selectedLocaleIndex = 35;
      await prefs.setString("language_code", "mg");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("mt")) {
      _appLocale = Locale("mt");
      selectedLocaleIndex = 36;
      await prefs.setString("language_code", "mt");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("nl")) {
      _appLocale = Locale("nl");
      selectedLocaleIndex = 37;
      await prefs.setString("language_code", "nl");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("no")) {
      _appLocale = Locale("no");
      selectedLocaleIndex = 38;
      await prefs.setString("language_code", "no");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("uz")) {
      _appLocale = Locale("uz");
      selectedLocaleIndex = 39;
      await prefs.setString("language_code", "uz");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("pl")) {
      _appLocale = Locale("pl");
      selectedLocaleIndex = 40;
      await prefs.setString("language_code", "pl");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("pt")) {
      _appLocale = Locale("pt");
      selectedLocaleIndex = 41;
      await prefs.setString("language_code", "pt");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ro")) {
      _appLocale = Locale("ro");
      selectedLocaleIndex = 42;
      await prefs.setString("language_code", "ro");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("sm")) {
      _appLocale = Locale("sm");
      selectedLocaleIndex = 43;
      await prefs.setString("language_code", "sm");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("st")) {
      _appLocale = Locale("st");
      selectedLocaleIndex = 44;
      await prefs.setString("language_code", "st");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("sn")) {
      _appLocale = Locale("sn");
      selectedLocaleIndex = 45;
      await prefs.setString("language_code", "sn");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("sq")) {
      _appLocale = Locale("sq");
      selectedLocaleIndex = 46;
      await prefs.setString("language_code", "sq");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("sk")) {
      _appLocale = Locale("sk");
      selectedLocaleIndex = 47;
      await prefs.setString("language_code", "sk");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("sl")) {
      _appLocale = Locale("sl");
      selectedLocaleIndex = 48;
      await prefs.setString("language_code", "sl");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("fi")) {
      _appLocale = Locale("fi");
      selectedLocaleIndex = 49;
      await prefs.setString("language_code", "fi");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("sv")) {
      _appLocale = Locale("sv");
      selectedLocaleIndex = 50;
      await prefs.setString("language_code", "sv");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("mi")) {
      _appLocale = Locale("mi");
      selectedLocaleIndex = 51;
      await prefs.setString("language_code", "mi");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("vi")) {
      _appLocale = Locale("vi");
      selectedLocaleIndex = 52;
      await prefs.setString("language_code", "vi");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("tr")) {
      _appLocale = Locale("tr");
      selectedLocaleIndex = 53;
      await prefs.setString("language_code", "tr");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("yo")) {
      _appLocale = Locale("yo");
      selectedLocaleIndex = 54;
      await prefs.setString("language_code", "yo");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("zu")) {
      _appLocale = Locale("zu");
      selectedLocaleIndex = 55;
      await prefs.setString("language_code", "zu");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("xh")) {
      _appLocale = Locale("xh");
      selectedLocaleIndex = 56;
      await prefs.setString("language_code", "xh");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("is")) {
      _appLocale = Locale("is");
      selectedLocaleIndex = 57;
      await prefs.setString("language_code", "is");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("cs")) {
      _appLocale = Locale("cs");
      selectedLocaleIndex = 58;
      await prefs.setString("language_code", "cs");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("el")) {
      _appLocale = Locale("el");
      selectedLocaleIndex = 59;
      await prefs.setString("language_code", "el");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("be")) {
      _appLocale = Locale("be");
      selectedLocaleIndex = 60;
      await prefs.setString("language_code", "be");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("bg")) {
      _appLocale = Locale("bg");
      selectedLocaleIndex = 61;
      await prefs.setString("language_code", "bg");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ky")) {
      _appLocale = Locale("ky");
      selectedLocaleIndex = 62;
      await prefs.setString("language_code", "ky");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("mk")) {
      _appLocale = Locale("mk");
      selectedLocaleIndex = 63;
      await prefs.setString("language_code", "mk");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("mn")) {
      _appLocale = Locale("mn");
      selectedLocaleIndex = 64;
      await prefs.setString("language_code", "mn");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ru")) {
      _appLocale = Locale("ru");
      selectedLocaleIndex = 65;
      await prefs.setString("language_code", "ru");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("sr")) {
      _appLocale = Locale("sr");
      selectedLocaleIndex = 66;
      await prefs.setString("language_code", "sr");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("tg")) {
      _appLocale = Locale("tg");
      selectedLocaleIndex = 67;
      await prefs.setString("language_code", "tg");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("uk")) {
      _appLocale = Locale("uk");
      selectedLocaleIndex = 68;
      await prefs.setString("language_code", "uk");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("kk")) {
      _appLocale = Locale("kk");
      selectedLocaleIndex = 69;
      await prefs.setString("language_code", "kk");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("hy")) {
      _appLocale = Locale("hy");
      selectedLocaleIndex = 70;
      await prefs.setString("language_code", "hy");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("iw")) {
      _appLocale = Locale("iw");
      selectedLocaleIndex = 71;
      await prefs.setString("language_code", "iw");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ur")) {
      _appLocale = Locale("ur");
      selectedLocaleIndex = 72;
      await prefs.setString("language_code", "ur");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("sd")) {
      _appLocale = Locale("sd");
      selectedLocaleIndex = 73;
      await prefs.setString("language_code", "sd");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("fa")) {
      _appLocale = Locale("fa");
      selectedLocaleIndex = 74;
      await prefs.setString("language_code", "fa");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ku")) {
      _appLocale = Locale("ku");
      selectedLocaleIndex = 75;
      await prefs.setString("language_code", "ku");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ps")) {
      _appLocale = Locale("ps");
      selectedLocaleIndex = 76;
      await prefs.setString("language_code", "ps");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ne")) {
      _appLocale = Locale("ne");
      selectedLocaleIndex = 77;
      await prefs.setString("language_code", "ne");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("mr")) {
      _appLocale = Locale("mr");
      selectedLocaleIndex = 78;
      await prefs.setString("language_code", "mr");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("hi")) {
      _appLocale = Locale("hi");
      selectedLocaleIndex = 79;
      await prefs.setString("language_code", "hi");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("bn")) {
      _appLocale = Locale("bn");
      selectedLocaleIndex = 80;
      await prefs.setString("language_code", "bn");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("pa")) {
      _appLocale = Locale("pa");
      selectedLocaleIndex = 81;
      await prefs.setString("language_code", "pa");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("gu")) {
      _appLocale = Locale("gu");
      selectedLocaleIndex = 82;
      await prefs.setString("language_code", "gu");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ta")) {
      _appLocale = Locale("ta");
      selectedLocaleIndex = 83;
      await prefs.setString("language_code", "ta");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("te")) {
      _appLocale = Locale("te");
      selectedLocaleIndex = 84;
      await prefs.setString("language_code", "te");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("kn")) {
      _appLocale = Locale("kn");
      selectedLocaleIndex = 85;
      await prefs.setString("language_code", "kn");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ml")) {
      _appLocale = Locale("ml");
      selectedLocaleIndex = 86;
      await prefs.setString("language_code", "ml");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("si")) {
      _appLocale = Locale("si");
      selectedLocaleIndex = 87;
      await prefs.setString("language_code", "si");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("th")) {
      _appLocale = Locale("th");
      selectedLocaleIndex = 88;
      await prefs.setString("language_code", "th");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("lo")) {
      _appLocale = Locale("lo");
      selectedLocaleIndex = 89;
      await prefs.setString("language_code", "lo");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("my")) {
      _appLocale = Locale("my");
      selectedLocaleIndex = 90;
      await prefs.setString("language_code", "my");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ka")) {
      _appLocale = Locale("ka");
      selectedLocaleIndex = 91;
      await prefs.setString("language_code", "ka");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("am")) {
      _appLocale = Locale("am");
      selectedLocaleIndex = 92;
      await prefs.setString("language_code", "am");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("km")) {
      _appLocale = Locale("km");
      selectedLocaleIndex = 93;
      await prefs.setString("language_code", "km");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ja")) {
      _appLocale = Locale("ja");
      selectedLocaleIndex = 94;
      await prefs.setString("language_code", "ja");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("zh-CN")) {
      _appLocale = Locale("zh-CN");
      selectedLocaleIndex = 95;
      await prefs.setString("language_code", "zh-CN");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("zh-TW")) {
      _appLocale = Locale("zh-TW");
      selectedLocaleIndex = 96;
      await prefs.setString("language_code", "zh-TW");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    } else if (type == Locale("ko")) {
      _appLocale = Locale("ko");
      selectedLocaleIndex = 97;
      await prefs.setString("language_code", "ko");
      await prefs.setString("countryCode", "");
      newUrl.changeUrl();
      loadHome(context);
    }
    await prefs.setInt('localeIndex', selectedLocaleIndex!);
    notifyListeners();
  }

  loadHome(BuildContext context) async {
    loadLobby(context);
    loadProduct(context);
    loadAccountHistory(context);
    loadAccountWishlist(context);
    Provider.of<AppNotifier>(context, listen: false).setLightMode();
  }

  loadLobby(BuildContext context) async {
    await Provider.of<HomeProvider>(context, listen: false).fetchHome(context);
  }

  loadProduct(BuildContext context) async {
    await Provider.of<ProductProvider>(context, listen: false)
        .fetchNewProducts(context: context, '');
  }

  loadAccountHistory(BuildContext context) async {
    await Provider.of<ProductProvider>(context, listen: false)
        .loadHistoryProduct(context);
  }

  loadAccountWishlist(BuildContext context) async {
    await Provider.of<WishlistProvider>(context, listen: false)
        .loadAccountWishlist(context);
  }

  final lightTheme = ThemeData.light().copyWith(
    useMaterial3: true,
    colorScheme: ColorScheme.light(
      primary: primaryColor, // Button & active color
      background: Colors.white, // Scaffold background
      surface: Colors.white, // Cards, sheets
      onPrimary: Colors.white, // Text/icons on primary color
      onBackground: Colors.black, // Text on background
      onSurface: Colors.black, // Text on cards, etc.
    ),
    scaffoldBackgroundColor: Colors.white,
    primaryColor: primaryColor,
    textTheme: ThemeData.light().textTheme.apply(
          fontFamily: 'Poppins',
        ),
    primaryTextTheme: ThemeData.light().textTheme.apply(
          fontFamily: 'Poppins',
        ),
  );

  final lightThemeAr = ThemeData.light().copyWith(
    useMaterial3: true,
    colorScheme: ColorScheme.light(
      primary: primaryColor, // Button & active color
      background: Colors.white, // Scaffold background
      surface: Colors.white, // Cards, sheets
      onPrimary: Colors.white, // Text/icons on primary color
      onBackground: Colors.black, // Text on background
      onSurface: Colors.black, // Text on cards, etc.
    ),
    scaffoldBackgroundColor: Colors.white,
    primaryColor: primaryColor,
    textTheme: ThemeData.light().textTheme.apply(
          fontFamily: 'Cairo',
        ),
    primaryTextTheme: ThemeData.light().textTheme.apply(
          fontFamily: 'Cairo',
        ),
  );

  final darkTheme = ThemeData.dark().copyWith(
    useMaterial3: true,
    colorScheme: ColorScheme.dark(
      primary: primaryColor, // Button & active color
      background: Color(0xFF121212), // Dark background
      surface: Color(0xFF1E1E1E), // Darker cards/sheets
      onPrimary: Colors.white,
      onBackground: Colors.white,
      onSurface: Colors.white,
    ),
    scaffoldBackgroundColor: Color(0xFF121212),
    primaryColor: primaryColor,
    textTheme: ThemeData.dark().textTheme.apply(
          fontFamily: 'Poppins',
        ),
    primaryTextTheme: ThemeData.dark().textTheme.apply(
          fontFamily: 'Poppins',
        ),
  );

  final darkThemeAr = ThemeData.dark().copyWith(
    useMaterial3: true,
    colorScheme: ColorScheme.dark(
      primary: primaryColor, // Button & active color
      background: Color(0xFF121212), // Dark background
      surface: Color(0xFF1E1E1E), // Darker cards/sheets
      onPrimary: Colors.white,
      onBackground: Colors.white,
      onSurface: Colors.white,
    ),
    scaffoldBackgroundColor: Color(0xFF121212),
    primaryColor: primaryColor,
    textTheme: ThemeData.dark().textTheme.apply(
          fontFamily: 'Cairo',
        ),
    primaryTextTheme: ThemeData.dark().textTheme.apply(
          fontFamily: 'Cairo',
        ),
  );

  void setDarkMode() async {
    var prefs = await SharedPreferences.getInstance();
    if (prefs.containsKey('language_code') == true) {
      if (prefs.getString('language_code') == 'ar') {
        _themeData = darkThemeAr;
      } else {
        _themeData = darkTheme;
      }
    } else {
      _themeData = darkTheme;
    }
    StorageManager.saveData('themeMode', 'dark');
    notifyListeners();
  }

  void setLightMode() async {
    var prefs = await SharedPreferences.getInstance();
    if (prefs.containsKey('language_code') == true) {
      if (prefs.getString('language_code') == 'ar') {
        _themeData = lightThemeAr;
        StorageManager.saveData('themeMode', 'lightAr');
      } else {
        _themeData = lightTheme;
        StorageManager.saveData('themeMode', 'light');
      }
    } else {
      _themeData = lightTheme;
      StorageManager.saveData('themeMode', 'light');
    }
    notifyListeners();
  }
}
