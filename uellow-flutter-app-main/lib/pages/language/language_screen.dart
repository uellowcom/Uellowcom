import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/provider/app_provider.dart';
import 'package:provider/provider.dart';

import '../../utils/utility.dart';

class LanguageScreen extends StatefulWidget {
  LanguageScreen({Key? key}) : super(key: key);

  @override
  _LanguageScreenState createState() => _LanguageScreenState();
}

class _LanguageScreenState extends State<LanguageScreen> {
  List languagesData = [
    {
      "code": "en",
      "name": "English",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/en.svg"
    },
    {
      "code": "ar",
      "name": "العربية",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ar.svg"
    },
    {
      "code": "fr",
      "name": "Français",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/fr.svg"
    },
    {
      "code": "af",
      "name": "Afrikaans",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/af.svg"
    },
    {
      "code": "so",
      "name": "Afsoomaali",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/so.svg"
    },
    {
      "code": "az",
      "name": "Azərbaycan",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/az.svg"
    },
    {
      "code": "id",
      "name": "Bahasa",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/id.svg"
    },
    {
      "code": "ms",
      "name": "Bahasa",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ms.svg"
    },
    // {
    //   "code": "jw",
    //   "name": "Basa",
    //   "image":
    //       "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/jw.svg"
    // },
    // {
    //   "code": "su",
    //   "name": "Basa",
    //   "image":
    //       "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/su.svg"
    // },
    {
      "code": "bs",
      "name": "Bosanski",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/bs.svg"
    },
    {
      "code": "ca",
      "name": "Català",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ca.svg"
    },
    {
      "code": "ny",
      "name": "Chichewa",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ny.svg"
    },
    {
      "code": "co",
      "name": "Corsu",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/co.svg"
    },
    {
      "code": "cy",
      "name": "Cymraeg",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/cy.svg"
    },
    {
      "code": "da",
      "name": "Dansk",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/da.svg"
    },
    {
      "code": "de",
      "name": "Deutsch",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/de.svg"
    },
    {
      "code": "et",
      "name": "Eesti",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/et.svg"
    },
    {
      "code": "es",
      "name": "Español",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/es.svg"
    },
    {
      "code": "eo",
      "name": "Esperanto",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/eo.svg"
    },
    {
      "code": "eu",
      "name": "Euskara",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/eu.svg"
    },
    {
      "code": "tl",
      "name": "Filipino",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/tl.svg"
    },
    {
      "code": "fy",
      "name": "Frysk",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/fy.svg"
    },
    {
      "code": "ga",
      "name": "Gaeilge",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ga.svg"
    },
    {
      "code": "gl",
      "name": "Galego",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/gl.svg"
    },
    {
      "code": "gd",
      "name": "Gàidhlig",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/gd.svg"
    },
    {
      "code": "ha",
      "name": "Harshen",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ha.svg"
    },
    {
      "code": "hr",
      "name": "Hrvatski",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/hr.svg"
    },
    {
      "code": "ig",
      "name": "Igbo",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ig.svg"
    },
    {
      "code": "it",
      "name": "Italiano",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/it.svg"
    },
    {
      "code": "sw",
      "name": "Kiswahili",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/sw.svg"
    },
    {
      "code": "ht",
      "name": "Kreyol",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ht.svg"
    },
    {
      "code": "la",
      "name": "Latin",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/la.svg"
    },
    {
      "code": "lv",
      "name": "Latviešu",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/lv.svg"
    },
    {
      "code": "lt",
      "name": "Lietuvių",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/lt.svg"
    },
    {
      "code": "lb",
      "name": "Lëtzebuergesch",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/lb.svg"
    },
    {
      "code": "hu",
      "name": "Magyar",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/hu.svg"
    },
    {
      "code": "mg",
      "name": "Malagasy",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/mg.svg"
    },
    {
      "code": "mt",
      "name": "Maltese",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/mt.svg"
    },
    {
      "code": "nl",
      "name": "Nederlands",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/nl.svg"
    },
    {
      "code": "no",
      "name": "Norsk",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/no.svg"
    },
    {
      "code": "uz",
      "name": "O‘zbekcha",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/uz.svg"
    },
    {
      "code": "pl",
      "name": "Polski",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/pl.svg"
    },
    {
      "code": "pt",
      "name": "Português",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/pt.svg"
    },
    {
      "code": "ro",
      "name": "Română",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ro.svg"
    },
    {
      "code": "sm",
      "name": "Samoan",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/sm.svg"
    },
    {
      "code": "st",
      "name": "Sesotho",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/st.svg"
    },
    {
      "code": "sn",
      "name": "Shona",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/sn.svg"
    },
    {
      "code": "sq",
      "name": "Shqip",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/sq.svg"
    },
    {
      "code": "sk",
      "name": "Slovenčina",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/sk.svg"
    },
    {
      "code": "sl",
      "name": "Slovenščina",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/sl.svg"
    },
    {
      "code": "fi",
      "name": "Suomi",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/fi.svg"
    },
    {
      "code": "sv",
      "name": "Svenska",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/sv.svg"
    },
    {
      "code": "mi",
      "name": "Te",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/mi.svg"
    },
    {
      "code": "vi",
      "name": "Tiếng",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/vi.svg"
    },
    {
      "code": "tr",
      "name": "Türkçe",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/tr.svg"
    },
    {
      "code": "yo",
      "name": "Yorùbá",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/yo.svg"
    },
    {
      "code": "zu",
      "name": "Zulu",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/zu.svg"
    },
    {
      "code": "xh",
      "name": "isiXhosa",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/xh.svg"
    },
    {
      "code": "is",
      "name": "Íslenska",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/is.svg"
    },
    {
      "code": "cs",
      "name": "Čeština",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/cs.svg"
    },
    {
      "code": "el",
      "name": "Ελληνικά",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/el.svg"
    },
    {
      "code": "be",
      "name": "Беларуская",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/be.svg"
    },
    {
      "code": "bg",
      "name": "Български",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/bg.svg"
    },
    {
      "code": "ky",
      "name": "Кыргызча",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ky.svg"
    },
    {
      "code": "mk",
      "name": "Македонски",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/mk.svg"
    },
    {
      "code": "mn",
      "name": "Монгол",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/mn.svg"
    },
    {
      "code": "ru",
      "name": "Русский",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ru.svg"
    },
    {
      "code": "sr",
      "name": "Српски",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/sr.svg"
    },
    {
      "code": "tg",
      "name": "Тоҷикӣ",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/tg.svg"
    },
    {
      "code": "uk",
      "name": "Українська",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/uk.svg"
    },
    {
      "code": "kk",
      "name": "Қазақ",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/kk.svg"
    },
    {
      "code": "hy",
      "name": "Հայերեն",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/hy.svg"
    },
    {
      "code": "ur",
      "name": "اردو",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ur.svg"
    },
    {
      "code": "sd",
      "name": "سنڌي",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/sd.svg"
    },
    {
      "code": "fa",
      "name": "فارسی",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/fa.svg"
    },
    {
      "code": "ku",
      "name": "كوردی",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ku.svg"
    },
    {
      "code": "ps",
      "name": "پښتو",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ps.svg"
    },
    {
      "code": "ne",
      "name": "नेपाली",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ne.svg"
    },
    {
      "code": "mr",
      "name": "मराठी",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/mr.svg"
    },
    {
      "code": "hi",
      "name": "हिन्दी",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/hi.svg"
    },
    {
      "code": "bn",
      "name": "বাংলা",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/bn.svg"
    },
    {
      "code": "pa",
      "name": "ਪੰਜਾਬੀ",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/pa.svg"
    },
    {
      "code": "gu",
      "name": "ગુજરાતી",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/gu.svg"
    },
    {
      "code": "ta",
      "name": "தமிழ்",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ta.svg"
    },
    {
      "code": "te",
      "name": "తెలుగు",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/te.svg"
    },
    {
      "code": "kn",
      "name": "ಕನ್ನಡ",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/kn.svg"
    },
    {
      "code": "ml",
      "name": "മലയാളം",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ml.svg"
    },
    {
      "code": "si",
      "name": "සිංහල",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/si.svg"
    },
    {
      "code": "th",
      "name": "ไทย",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/th.svg"
    },
    {
      "code": "lo",
      "name": "ພາສາລາວ",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/lo.svg"
    },
    {
      "code": "my",
      "name": "ဗမာစာ",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/my.svg"
    },
    {
      "code": "ka",
      "name": "ქართული",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ka.svg"
    },
    {
      "code": "am",
      "name": "አማርኛ",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/am.svg"
    },
    {
      "code": "km",
      "name": "ភាសាខ្មែរ",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/km.svg"
    },
    {
      "code": "ja",
      "name": "日本語",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ja.svg"
    },
    {
      "code": "zh-CN",
      "name": "简体中文",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/zh-CN.svg"
    },
    {
      "code": "zh-TW",
      "name": "繁體中文",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/zh-TW.svg"
    },
    {
      "code": "ko",
      "name": "한국어",
      "image":
          "https://app.uellow.com/wp-content/plugins/gtranslate/flags/svg/ko.svg"
    }
  ];

  String locale(int? index) {
    String locale = 'en';

    if (index == 0) {
      locale = "en";
    } else if (index == 1) {
      locale = "ar";
    } else if (index == 2) {
      locale = "fr";
    } else if (index == 3) {
      locale = "af";
    } else if (index == 4) {
      locale = "so";
    } else if (index == 5) {
      locale = "az";
    } else if (index == 6) {
      locale = "id";
    } else if (index == 7) {
      locale = "ms";
    } else if (index == 8) {
      locale = "bs";
    } else if (index == 9) {
      locale = "ca";
    } else if (index == 10) {
      locale = "ny";
    } else if (index == 11) {
      locale = "co";
    } else if (index == 12) {
      locale = "cy";
    } else if (index == 13) {
      locale = "da";
    } else if (index == 14) {
      locale = "de";
    } else if (index == 15) {
      locale = "et";
    } else if (index == 16) {
      locale = "es";
    } else if (index == 17) {
      locale = "eo";
    } else if (index == 18) {
      locale = "eu";
    } else if (index == 19) {
      locale = "tl";
    } else if (index == 20) {
      locale = "fy";
    } else if (index == 21) {
      locale = "ga";
    } else if (index == 22) {
      locale = "gl";
    } else if (index == 23) {
      locale = "gd";
    } else if (index == 24) {
      locale = "ha";
    } else if (index == 25) {
      locale = "hr";
    } else if (index == 26) {
      locale = "ig";
    } else if (index == 27) {
      locale = "it";
    } else if (index == 28) {
      locale = "sw";
    } else if (index == 29) {
      locale = "ht";
    } else if (index == 30) {
      locale = "la";
    } else if (index == 31) {
      locale = "lv";
    } else if (index == 32) {
      locale = "lt";
    } else if (index == 33) {
      locale = "lb";
    } else if (index == 34) {
      locale = "hu";
    } else if (index == 35) {
      locale = "mg";
    } else if (index == 36) {
      locale = "mt";
    } else if (index == 37) {
      locale = "nl";
    } else if (index == 38) {
      locale = "no";
    } else if (index == 39) {
      locale = "uz";
    } else if (index == 40) {
      locale = "pl";
    } else if (index == 41) {
      locale = "pt";
    } else if (index == 42) {
      locale = "ro";
    } else if (index == 43) {
      locale = "sm";
    } else if (index == 44) {
      locale = "st";
    } else if (index == 45) {
      locale = "sn";
    } else if (index == 46) {
      locale = "sq";
    } else if (index == 47) {
      locale = "sk";
    } else if (index == 48) {
      locale = "sl";
    } else if (index == 49) {
      locale = "fi";
    } else if (index == 50) {
      locale = "sv";
    } else if (index == 51) {
      locale = "mi";
    } else if (index == 52) {
      locale = "vi";
    } else if (index == 53) {
      locale = "tr";
    } else if (index == 54) {
      locale = "yo";
    } else if (index == 55) {
      locale = "zu";
    } else if (index == 56) {
      locale = "xh";
    } else if (index == 57) {
      locale = "is";
    } else if (index == 58) {
      locale = "cs";
    } else if (index == 59) {
      locale = "el";
    } else if (index == 60) {
      locale = "be";
    } else if (index == 61) {
      locale = "bg";
    } else if (index == 62) {
      locale = "ky";
    } else if (index == 63) {
      locale = "mk";
    } else if (index == 64) {
      locale = "mn";
    } else if (index == 65) {
      locale = "ru";
    } else if (index == 66) {
      locale = "sr";
    } else if (index == 67) {
      locale = "tg";
    } else if (index == 68) {
      locale = "uk";
    } else if (index == 69) {
      locale = "kk";
    } else if (index == 70) {
      locale = "hy";
    } else if (index == 71) {
      locale = "iw";
    } else if (index == 72) {
      locale = "ur";
    } else if (index == 73) {
      locale = "sd";
    } else if (index == 74) {
      locale = "fa";
    } else if (index == 75) {
      locale = "ku";
    } else if (index == 76) {
      locale = "ps";
    } else if (index == 77) {
      locale = "ne";
    } else if (index == 78) {
      locale = "mr";
    } else if (index == 79) {
      locale = "hi";
    } else if (index == 80) {
      locale = "bn";
    } else if (index == 81) {
      locale = "pa";
    } else if (index == 82) {
      locale = "gu";
    } else if (index == 83) {
      locale = "ta";
    } else if (index == 84) {
      locale = "te";
    } else if (index == 85) {
      locale = "kn";
    } else if (index == 86) {
      locale = "ml";
    } else if (index == 87) {
      locale = "si";
    } else if (index == 88) {
      locale = "th";
    } else if (index == 89) {
      locale = "lo";
    } else if (index == 90) {
      locale = "my";
    } else if (index == 91) {
      locale = "ka";
    } else if (index == 92) {
      locale = "am";
    } else if (index == 93) {
      locale = "km";
    } else if (index == 94) {
      locale = "ja";
    } else if (index == 95) {
      locale = "zh-CN";
    } else if (index == 96) {
      locale = "zh-TW";
    } else if (index == 97) {
      locale = "ko";
    }

    return locale;
  }

  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    var appLanguage = Provider.of<AppNotifier>(context);

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        elevation: 0,
        backgroundColor: primaryColor,
        title: Text(
          AppLocalizations.of(context)!.translate('title_language')!,
          style: TextStyle(
              color: Colors.black,
              fontSize: responsiveFont(16),
              fontWeight: FontWeight.w500),
        ),
        leading: IconButton(
          onPressed: () {
            Navigator.pop(context);
          },
          icon: Icon(
            Icons.arrow_back,
            color: Colors.black,
          ),
        ),
      ),
      body: Container(
          margin: EdgeInsets.all(15),
          child: ListView(
            children: [
              ListView.separated(
                shrinkWrap: true,
                physics: ScrollPhysics(),
                itemBuilder: (context, i) {
                  return InkWell(
                    onTap: () {
                      setState(() {
                        appLanguage.selectedLocaleIndex = i;
                      });
                      appLanguage.changeLanguage(
                          Locale(locale(appLanguage.selectedLocaleIndex)),
                          context);
                      printLog("${appLanguage.selectedLocaleIndex}");
                      printLog("link: ${languagesData[i]['image']}");
                    },
                    child: Container(
                      padding: EdgeInsets.symmetric(vertical: 10),
                      width: double.infinity,
                      child: itemList(i),
                    ),
                  );
                },
                itemCount: languagesData.length,
                separatorBuilder: (BuildContext context, int index) {
                  return Container(
                    width: double.infinity,
                    height: 1,
                    color: HexColor("c4c4c4"),
                  );
                },
              ),
            ],
          )),
    );
  }

  Widget itemList(int i) {
    var appLanguage = Provider.of<AppNotifier>(context);

    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Visibility(
                  visible: languagesData[i]['code'] == "gd" ||
                      languagesData[i]['code'] == "es" ||
                      languagesData[i]['code'] == "tg",
                  child: Container(
                      width: 36.h,
                      height: 36.w,
                      child: Image.asset(
                        "images/account/${languagesData[i]['code']}.png",
                        // width: 35.h,
                        // height: 35.w,
                      )),
                ),
                Visibility(
                  visible: languagesData[i]['code'] != "gd" &&
                      languagesData[i]['code'] != "es" &&
                      languagesData[i]['code'] != "tg",
                  child: Container(
                      width: 36.h,
                      height: 36.w,
                      child: SvgPicture.network(
                        languagesData[i]['image'],
                        width: 35.h,
                        height: 35.w,
                      )),
                ),
                SizedBox(
                  width: 15,
                ),
                Text(
                  "${languagesData[i]['name']}",
                  style: TextStyle(fontSize: responsiveFont(12)),
                )
              ],
            ),
            appLanguage.selectedLocaleIndex == i
                ? Text(
                    AppLocalizations.of(context)!.translate('active')!,
                    style: TextStyle(
                        fontSize: responsiveFont(12),
                        fontWeight: FontWeight.w600,
                        color: secondaryColor),
                  )
                : Container()
          ],
        )
      ],
    );
  }
}
