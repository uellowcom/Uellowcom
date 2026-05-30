import 'dart:async';
import 'dart:convert';

import 'package:colorful_safe_area/colorful_safe_area.dart';
import 'package:flutter/material.dart';
import 'package:flutter/src/widgets/framework.dart';
import 'package:flutter/src/widgets/placeholder.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:modal_bottom_sheet/modal_bottom_sheet.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/provider/app_provider.dart';
import 'package:nyoba/provider/coupon_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';

class CustomCouponScreen extends StatefulWidget {
  const CustomCouponScreen({super.key});

  @override
  State<CustomCouponScreen> createState() => _CustomCouponScreenState();
}

class _CustomCouponScreenState extends State<CustomCouponScreen> {
  bool isSearching = false;
  List<double> height = [];
  List<WebViewController> webControllers = [];
  List<Completer<WebViewController>> completers = [];
  CouponProvider? cp;
  @override
  void initState() {
    super.initState();
    cp = Provider.of<CouponProvider>(context, listen: false);
    for (int i = 0; i < cp!.coupons.length; i++) {
      height.add(140);
      completers.add(Completer<WebViewController>());
    }
  }

  @override
  Widget build(BuildContext context) {
    final coupons = Provider.of<CouponProvider>(context, listen: false);

    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;
    return ColorfulSafeArea(
      color: Colors.white,
      child: Scaffold(
          appBar: AppBar(
            elevation: 0,
            backgroundColor: Colors.white,
            leading: IconButton(
              icon: Icon(
                Icons.arrow_back,
                color: Colors.black,
              ),
              onPressed: () {
                Navigator.pop(context);
              },
            ),
            title: Text(
              AppLocalizations.of(context)!.translate('coupon_code')!,
              style: TextStyle(color: Colors.black),
            ),
            actions: [
              GestureDetector(
                onTap: () {
                  showBarModalBottomSheet(
                      context: context,
                      builder: (context) => modalBottomSheet());
                },
                child: Container(
                    margin: locale == Locale('ar')
                        ? EdgeInsets.only(left: 10)
                        : EdgeInsets.only(right: 10),
                    width: 25.w,
                    height: 25.h,
                    child: Image.asset("images/cart/Faq.png")),
              )
            ],
          ),
          body: Consumer<CouponProvider>(
            builder: (context, value, child) {
              return Column(
                children: [
                  Container(
                    alignment: Alignment.centerLeft,
                    padding: EdgeInsets.all(15),
                    child: Text(
                      AppLocalizations.of(context)!
                          .translate('coupon_available')!,
                      style: TextStyle(
                          fontSize: responsiveFont(12),
                          fontWeight: FontWeight.w500),
                    ),
                  ),
                  SizedBox(
                    height: 10,
                  ),
                  Expanded(
                    child: ListView.separated(
                        shrinkWrap: true,
                        physics: ScrollPhysics(),
                        itemBuilder: (context, i) {
                          return Container(
                            width: MediaQuery.of(context).size.width,
                            height: height[i],
                            child: Stack(
                              children: [
                                WebView(
                                  zoomEnabled: false,
                                  initialUrl: Uri.dataFromString(
                                          '${(value.coupons[i].couponHtml!)}',
                                          mimeType: 'text/html',
                                          encoding: Encoding.getByName('utf-8'))
                                      .toString(),
                                  gestureRecognizers: Set()
                                    ..add(Factory<
                                            VerticalDragGestureRecognizer>(
                                        () => VerticalDragGestureRecognizer())),
                                  onWebViewCreated: (controller) {
                                    setState(() {
                                      webControllers.add(controller);
                                      completers[i].complete(webControllers[i]);
                                    });
                                  },
                                  onPageFinished: (url) async {
                                    var x = await webControllers[i]
                                        .runJavascriptReturningResult(
                                            "document.querySelector('#sc-cc').scrollHeight");
                                    double? y = double.tryParse(x.toString());
                                    setState(() {
                                      printLog('parse : $y --- $x');
                                      height[i] = y != null ? y + 10 : 150;
                                    });
                                  },
                                  javascriptMode: JavascriptMode.unrestricted,
                                ),
                                Visibility(
                                    visible: value.couponUsed != null &&
                                        value.coupons[i].code ==
                                            value.couponUsed!.code,
                                    child: Positioned(
                                      top: 10,
                                      right: 10,
                                      child: Icon(Icons.check_circle,
                                          color: Colors.green, size: 20),
                                    )),
                                GestureDetector(
                                  onTap: () {
                                    context
                                        .read<CouponProvider>()
                                        .useCoupon(
                                            context: context,
                                            search: value.coupons[i].code,
                                            i: i)
                                        .then((va) {
                                      setState(() {
                                        isSearching = true;
                                      });
                                      if (isSearching) {
                                        snackBar(context,
                                            message:
                                                "${AppLocalizations.of(context)!.translate('coupon_succesfully_applied')}");
                                      } else {
                                        snackBar(context,
                                            message:
                                                "${AppLocalizations.of(context)!.translate('coupon_code_invalid')}");
                                      }
                                    });
                                  },
                                  child: Container(
                                    width: MediaQuery.of(context).size.width,
                                    height: 150,
                                    color: Colors.transparent,
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                        separatorBuilder: (BuildContext context, int index) {
                          return SizedBox(
                            height: 15,
                          );
                        },
                        itemCount: value.coupons.length),
                  ),
                  SizedBox(
                    height: 10,
                  ),
                  GestureDetector(
                    onTap: () {
                      if (value.loadingUse == false) {
                        printLog("${coupons.coupons}");
                        Navigator.pop(context);
                      }
                    },
                    child: Container(
                      alignment: Alignment.bottomCenter,
                      width: MediaQuery.of(context).size.width,
                      padding: EdgeInsets.symmetric(vertical: 12),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment
                              .bottomCenter, // 10% of the width, so there are ten blinds.
                          colors: <HexColor>[
                            secondaryColor as HexColor,
                            primaryColor as HexColor,
                          ], // red to yellow
                          tileMode: TileMode
                              .repeated, // repeats the gradient over the canvas
                        ),
                      ),
                      child: value.loadingUse
                          ? customLoading(color: Colors.white)
                          : Text(
                              "${AppLocalizations.of(context)!.translate('done')}",
                              style: TextStyle(
                                  color: Colors.black,
                                  fontWeight: FontWeight.w500),
                            ),
                    ),
                  ),
                ],
              );
            },
          )),
    );
  }

  Widget modalBottomSheet() {
    return Container(
        height: MediaQuery.of(context).size.height / 3,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 15, vertical: 15),
                  width: double.infinity,
                  alignment: Alignment.center,
                  child: Text(
                    AppLocalizations.of(context)!.translate('coupon_faq')!,
                    style: TextStyle(
                        fontSize: responsiveFont(14),
                        fontWeight: FontWeight.w500),
                  ),
                ),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 15),
                  child: Text(
                    AppLocalizations.of(context)!.translate('how_to_use')!,
                    style: TextStyle(
                        fontSize: responsiveFont(12),
                        fontWeight: FontWeight.w500),
                  ),
                ),
                SizedBox(
                  height: 5,
                ),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 15),
                  child: Text(
                    AppLocalizations.of(context)!.translate('sub_how_to_use')!,
                    style: TextStyle(
                      fontSize: responsiveFont(10),
                    ),
                  ),
                ),
                SizedBox(
                  height: 15,
                ),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 15),
                  child: Text(
                    AppLocalizations.of(context)!.translate('how_to_get')!,
                    style: TextStyle(
                        fontSize: responsiveFont(12),
                        fontWeight: FontWeight.w500),
                  ),
                ),
                SizedBox(
                  height: 5,
                ),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 15),
                  child: Text(
                    AppLocalizations.of(context)!.translate('sub_how_to_get')!,
                    style: TextStyle(
                      fontSize: responsiveFont(10),
                    ),
                  ),
                ),
              ],
            ),
            GestureDetector(
              onTap: () {
                Navigator.pop(context);
              },
              child: Container(
                alignment: Alignment.center,
                width: MediaQuery.of(context).size.width,
                padding: EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment
                        .bottomCenter, // 10% of the width, so there are ten blinds.
                    colors: <HexColor>[
                      secondaryColor as HexColor,
                      primaryColor as HexColor,
                    ], // red to yellow
                    tileMode: TileMode
                        .repeated, // repeats the gradient over the canvas
                  ),
                ),
                child: Text(
                  "${AppLocalizations.of(context)!.translate('done')}",
                  style: TextStyle(
                      color: Colors.black, fontWeight: FontWeight.w500),
                ),
              ),
            ),
          ],
        ));
  }
}
