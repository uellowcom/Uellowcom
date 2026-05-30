import 'dart:convert';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/src/widgets/framework.dart';
import 'package:flutter/src/widgets/placeholder.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/models/currency_model.dart';
import 'package:nyoba/provider/general_settings_provider.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

class CurrencyScreen extends StatefulWidget {
  CurrencyScreen({super.key});

  @override
  State<CurrencyScreen> createState() => _CurrencyScreenState();
}

class _CurrencyScreenState extends State<CurrencyScreen> {
  String selectedCurrency = "";

  @override
  void initState() {
    super.initState();
    WidgetsFlutterBinding.ensureInitialized().addPostFrameCallback((timeStamp) {
      Provider.of<GeneralSettingsProvider>(context, listen: false)
          .loadAllCurrency(context);
      context
          .read<GeneralSettingsProvider>()
          .setCurrency(Session.data.getString('currency_code'));
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        elevation: 0,
        leading: GestureDetector(
          onTap: () {
            Navigator.pop(context);
          },
          child: Icon(
            Icons.arrow_back,
            color: Colors.black,
          ),
        ),
        title: Text(
          "${AppLocalizations.of(context)!.translate('currency')}",
          style: TextStyle(color: Colors.black),
        ),
        backgroundColor: primaryColor,
      ),
      body: Consumer<GeneralSettingsProvider>(
        builder: (context, value, child) => value.loadingCurrency
            ? customLoading()
            : Container(
                margin: EdgeInsets.all(15),
                child: ListView(
                  children: [
                    ListView.separated(
                      shrinkWrap: true,
                      physics: ScrollPhysics(),
                      itemBuilder: (context, i) {
                        return InkWell(
                          onTap: () {
                            // setState(() {
                            //   appLanguage.selectedLocaleIndex = i;
                            // });
                            // appLanguage.changeLanguage(
                            //     Locale(locale(appLanguage.selectedLocaleIndex)));
                            value.setCurrency(value.listCurrency[i].name);
                          },
                          child: Container(
                            padding: EdgeInsets.symmetric(vertical: 10),
                            width: double.infinity,
                            child: itemList(value.listCurrency[i], value, i),
                          ),
                        );
                      },
                      itemCount: value.listCurrency.length,
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
      ),
    );
  }

  Widget itemList(
      CurrencyModel currency, GeneralSettingsProvider value, int i) {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Container(
                    width: 36.h,
                    height: 36.w,
                    child: CachedNetworkImage(
                      imageUrl: currency.flag!,
                      placeholder: (context, url) => customLoading(),
                      errorWidget: (context, url, error) =>
                          Icon(Icons.image_not_supported),
                    )),
                SizedBox(
                  width: 15,
                ),
                Text(
                  currency.name!,
                  style: TextStyle(fontSize: responsiveFont(12)),
                )
              ],
            ),
            currency.name == value.activeCurrency
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
