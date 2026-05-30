import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:nyoba/pages/auth/login_screen.dart';
import 'package:nyoba/pages/wallet/wallet_detail_screen.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/wallet_provider.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../../app_localizations.dart';

class WalletCard extends StatelessWidget {
  final bool? showBtnMore;

  WalletCard({this.showBtnMore});

  @override
  Widget build(BuildContext context) {
    final balance = Provider.of<WalletProvider>(context).walletBalance;
    final loading = Provider.of<WalletProvider>(context).loadingBalance;
    final isWalletActive = Provider.of<HomeProvider>(context).isWalletActive;
    print("wallet :" + isWalletActive.toString());
    if (loading!)
      return Container(
        margin: EdgeInsets.only(left: 10, right: 10, top: 10),
        padding: EdgeInsets.symmetric(horizontal: 10),
        height: 40.h,
        decoration: BoxDecoration(
            color: Colors.grey[200], borderRadius: BorderRadius.circular(8)),
        child: Shimmer.fromColors(
          child: Container(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    ShaderMask(
                      child: Image(
                        image: AssetImage("images/lobby/wallet.png"),
                        height: 30.h,
                      ),
                      shaderCallback: (Rect bounds) {
                        return LinearGradient(
                          colors: [primaryColor, primaryColor],
                          stops: [
                            0.0,
                            0.5,
                          ],
                        ).createShader(bounds);
                      },
                      blendMode: BlendMode.srcATop,
                    ),
                    SizedBox(
                      width: 15,
                    ),
                    Container(
                      width: 30,
                      height: 20,
                      decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(6),
                          color: Colors.white),
                    ),
                    SizedBox(
                      width: 15,
                    ),
                    Container(
                      width: 90,
                      height: 20,
                      decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(6),
                          color: Colors.white),
                    ),
                  ],
                ),
                Visibility(
                  visible: showBtnMore!,
                  child: Container(
                    width: 80,
                    height: 30,
                    decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(6),
                        color: Colors.white),
                  ),
                )
              ],
            ),
          ),
          baseColor: Colors.grey[500]!,
          highlightColor: Colors.grey[100]!,
        ),
      );

    if (!isWalletActive) return Container();

    return Visibility(
        visible: isWalletActive && !loading,
        child: Container(
          margin: EdgeInsets.only(left: 10, right: 10, top: 10),
          padding: EdgeInsets.symmetric(horizontal: 10),
          height: 40.h,
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(8)),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                child: Row(
                  children: [
                    SizedBox(
                      width: 10,
                    ),
                    ShaderMask(
                      child: Image(
                        image: AssetImage("images/lobby/wallet.png"),
                        height: 18.h,
                      ),
                      shaderCallback: (Rect bounds) {
                        return LinearGradient(
                          colors: [primaryColor, primaryColor],
                          stops: [
                            0.0,
                            0.5,
                          ],
                        ).createShader(bounds);
                      },
                      blendMode: BlendMode.srcATop,
                    ),
                    Container(
                      margin: EdgeInsets.symmetric(horizontal: 15),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            AppLocalizations.of(context)!
                                .translate('wallet')!
                                .toUpperCase(),
                            style: TextStyle(
                                fontWeight: FontWeight.w500,
                                fontSize: responsiveFont(10)),
                          ),
                          SizedBox(
                            width: 5,
                          ),
                          Text(
                            stringToCurrency(
                                double.parse(
                                    Session.data.getBool('isLogin')! == false
                                        ? "0"
                                        : balance ?? "0"),
                                context),
                            style: TextStyle(
                                color: Colors.black,
                                fontSize: responsiveFont(10),
                                fontWeight: FontWeight.w700),
                          )
                        ],
                      ),
                    )
                  ],
                ),
              ),
              Visibility(
                  visible: showBtnMore!,
                  child: SizedBox(
                    height: 26.h,
                    child: TextButton.icon(
                      onPressed: () {
                        if (Session.data.getBool('isLogin')!) {
                          Navigator.push(
                              context,
                              MaterialPageRoute(
                                  builder: (context) => WalletDetail()));
                        } else {
                          Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => Login(),
                              ));
                        }
                      },
                      icon: Image(
                        image: AssetImage("images/lobby/more_detail.png"),
                        height: 15.h,
                      ),
                      label: Text(
                        AppLocalizations.of(context)!
                            .translate('more_detail')!
                            .toUpperCase(),
                        style: TextStyle(
                            fontWeight: FontWeight.w500, color: Colors.black),
                      ),
                      style: TextButton.styleFrom(
                          // primary: Colors.black,
                          backgroundColor: primaryColor,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8)),
                          textStyle: const TextStyle(fontSize: 10)),
                    ),
                  ))
            ],
          ),
        ));
  }
}
