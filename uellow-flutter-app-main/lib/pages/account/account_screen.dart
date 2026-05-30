import 'dart:io';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:launch_review/launch_review.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/pages/account/account_address_screen.dart';
import 'package:nyoba/pages/account/account_detail_screen.dart';
import 'package:nyoba/pages/account/currency_screen.dart';
import 'package:nyoba/pages/auth/login_screen.dart';
import 'package:nyoba/pages/auth/not_login_screen.dart';
import 'package:nyoba/pages/home/home_screen.dart';
import 'package:nyoba/pages/language/language_screen.dart';
import 'package:nyoba/pages/point/my_point_screen.dart';
import 'package:nyoba/pages/product/product_detail_screen.dart';
import 'package:nyoba/pages/product/product_more_screen.dart';
import 'package:nyoba/pages/review/review_screen.dart';
import 'package:nyoba/provider/app_provider.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/provider/user_provider.dart';
import 'package:nyoba/provider/wishlist_provider.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/widgets/container_card.dart';
import 'package:nyoba/widgets/home/wallet_card.dart';
import 'package:nyoba/widgets/webview/webview.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';
import 'package:url_launcher/url_launcher_string.dart';

import '../../utils/utility.dart';
import '../order/my_order_screen.dart';
import '../product/product_form.dart';
import '../wishlist/wishlist_screen.dart';

class AccountScreen extends StatefulWidget {
  AccountScreen({Key? key}) : super(key: key);

  @override
  _AccountScreenState createState() => _AccountScreenState();
}

class _AccountScreenState extends State<AccountScreen> {
  String? _versionName;
  bool isLogin = false;

  int idxView = 0;
  @override
  void initState() {
    super.initState();
    loadDetail();
    isLogin = Session.data.getBool('isLogin')!;
    WidgetsFlutterBinding.ensureInitialized().addPostFrameCallback((timeStamp) {
      if (isLogin) {
        Provider.of<WishlistProvider>(context, listen: false)
            .loadAccountWishlist(context);
      }
    });
  }

  loadDetail() async {
    if (Session.data.getBool('isLogin')!) {
      Provider.of<UserProvider>(context, listen: false)
          .fetchUserDetail(context)
          .then((value) => this.setState(() {}));
    }
  }

  Future _init() async {
    final _packageInfo = await PackageInfo.fromPlatform();

    return _packageInfo.version;
  }

  logout() async {
    final home = Provider.of<HomeProvider>(context, listen: false);
    var auth = FirebaseAuth.instance;
    // final AccessToken? accessToken = await FacebookAuth.instance.accessToken;

    Session().removeUser();
    if (auth.currentUser != null) {
  await GoogleSignIn.instance.signOut();
}

    // if (accessToken != null) {
    //   await FacebookAuth.instance.logOut();
    // }
    if (Session.data.getString('login_type') == 'apple') {
      await auth.signOut();
    }
    home.isReload = true;
    await Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (BuildContext context) => HomeScreen()),
        (Route<dynamic> route) => false);
  }

  _launchPhoneURL(String phoneNumber) async {
    String url = 'tel:' + phoneNumber;
    if (await canLaunchUrlString(url)) {
      await launchUrlString(url);
    } else {
      throw 'Could not launch $url';
    }
  }

  @override
  Widget build(BuildContext context) {
    final generalSettings = Provider.of<HomeProvider>(context, listen: false);

    final point = Provider.of<UserProvider>(context, listen: false);

    final wishlistProvider =
        Provider.of<WishlistProvider>(context, listen: false);

    return Scaffold(
      backgroundColor: HexColor("f5f5f5"),
      appBar: AppBar(
        elevation: 0,
        backgroundColor: primaryColor,
        title: !isLogin
            ? GestureDetector(
                onTap: () {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => Login(
                          isFromNavBar: false,
                        ),
                      ));
                },
                child: Container(
                  child: Text(
                    "${AppLocalizations.of(context)!.translate('signin_register')}",
                    style: TextStyle(
                        color: Colors.black,
                        fontWeight: FontWeight.w500,
                        fontSize: 16),
                  ),
                ),
              )
            : Text(
                AppLocalizations.of(context)!.translate('title_myAccount')!,
                style: TextStyle(
                    fontSize: responsiveFont(16),
                    fontWeight: FontWeight.w500,
                    color: Colors.black),
              ),
      ),
      body: SingleChildScrollView(
        child: ListView(
          shrinkWrap: true,
          physics: ScrollPhysics(),
          children: [
            hello(point),
            order(),
            point.loading
                ? Container()
                : Visibility(
                    visible: point.point != null,
                    child: buildPointCard(),
                  ),
            WalletCard(
              showBtnMore: true,
            ),
            Session.data.getBool('isLogin')! ? account(point) : SizedBox(),
            socialMedia(),
            generalSetting(generalSettings),
            // Container(
            //   width: double.infinity,
            //   padding: EdgeInsets.all(15),
            //   child: Column(
            //     crossAxisAlignment: CrossAxisAlignment.start,
            //     children: [
            //       point.loading
            //           ? Text(
            //               "${AppLocalizations.of(context)!.translate('hello')}",
            //               style: TextStyle(
            //                   color: secondaryColor,
            //                   fontSize: responsiveFont(14),
            //                   fontWeight: FontWeight.w500),
            //             )
            //           : Text(
            //               "${AppLocalizations.of(context)!.translate('hello')}, ${Session.data.getString('firstname')!.length > 10 ? Session.data.getString('firstname')!.substring(0, 10) + '... ' : Session.data.getString('firstname')} !",
            //               style: TextStyle(
            //                   color: secondaryColor,
            //                   fontSize: responsiveFont(14),
            //                   fontWeight: FontWeight.w500),
            //             ),
            //       Text(
            //         AppLocalizations.of(context)!.translate('welcome_back')!,
            //         style: TextStyle(fontSize: responsiveFont(9)),
            //       ),
            //     ],
            //   ),
            // ),
            // Container(
            //   width: double.infinity,
            //   height: 5,
            //   color: Colors.black12,
            // ),
            // point.loading
            //     ? Container()
            //     : Visibility(
            //         visible: point.point != null,
            //         child: buildPointCard(),
            //       ),
            // Container(
            //   alignment: Alignment.centerLeft,
            //   margin: EdgeInsets.only(top: 15, left: 15, bottom: 5),
            //   child: Text(
            //     AppLocalizations.of(context)!.translate('account')!,
            //     style: TextStyle(
            //         fontSize: responsiveFont(10),
            //         fontWeight: FontWeight.w600,
            //         color: secondaryColor),
            //   ),
            // ),
            // accountButton("akun",
            //     AppLocalizations.of(context)!.translate('title_myAccount')!,
            //     func: () {
            //   Navigator.push(
            //           context,
            //           MaterialPageRoute(
            //               builder: (context) => AccountDetailScreen()))
            //       .then((value) => this.setState(() {}));
            // }),
            // point.loading
            //     ? Container()
            //     : Visibility(
            //         visible: point.point != null,
            //         child: accountButton("coin",
            //             AppLocalizations.of(context)!.translate('my_point')!,
            //             func: () {
            //           Navigator.push(
            //                   context,
            //                   MaterialPageRoute(
            //                       builder: (context) => MyPoint()))
            //               .then((value) => this.setState(() {}));
            //         }),
            //       ),
            // SizedBox(
            //   height: 5,
            // ),
            // Container(
            //   alignment: Alignment.centerLeft,
            //   margin: EdgeInsets.only(top: 15, left: 15, bottom: 5),
            //   child: Text(
            //     AppLocalizations.of(context)!.translate('transaction')!,
            //     style: TextStyle(
            //         fontSize: responsiveFont(10),
            //         fontWeight: FontWeight.w600,
            //         color: secondaryColor),
            //   ),
            // ),
            // accountButton(
            //     "myorder", AppLocalizations.of(context)!.translate('my_order')!,
            //     func: () {
            //   Navigator.push(
            //       context, MaterialPageRoute(builder: (context) => MyOrder()));
            // }),
            // accountButton("wishlist",
            //     AppLocalizations.of(context)!.translate('wishlist')!, func: () {
            //   Navigator.push(
            //       context, MaterialPageRoute(builder: (context) => WishList()));
            // }),
            // accountButton(
            //     "review", AppLocalizations.of(context)!.translate('review')!,
            //     func: () {
            //   Navigator.push(context,
            //       MaterialPageRoute(builder: (context) => ReviewScreen()));
            // }),
            // SizedBox(
            //   height: 5,
            // ),
            // Container(
            //   alignment: Alignment.centerLeft,
            //   margin: EdgeInsets.only(top: 5, left: 15, bottom: 5),
            //   child: Text(
            //     AppLocalizations.of(context)!.translate('general_setting')!,
            //     style: TextStyle(
            //         fontSize: responsiveFont(10),
            //         fontWeight: FontWeight.w600,
            //         color: secondaryColor),
            //   ),
            // ),
            // Column(
            //   children: [
            //     Container(
            //       margin: EdgeInsets.symmetric(horizontal: 10),
            //       child: Row(
            //         mainAxisAlignment: MainAxisAlignment.spaceBetween,
            //         children: [
            //           Row(
            //             children: [
            //               Container(
            //                   width: 25.w,
            //                   height: 25.h,
            //                   child:
            //                       Image.asset("images/account/darktheme.png")),
            //               SizedBox(
            //                 width: 10,
            //               ),
            //               Text(
            //                 AppLocalizations.of(context)!
            //                     .translate('dark_theme')!,
            //                 style: TextStyle(fontSize: responsiveFont(11)),
            //               )
            //             ],
            //           ),
            //           Consumer<AppNotifier>(
            //               builder: (context, theme, _) => Switch(
            //                     value: theme.isDarkMode,
            //                     onChanged: (value) {
            //                       setState(() {
            //                         theme.isDarkMode = !theme.isDarkMode;
            //                       });
            //                       if (theme.isDarkMode) {
            //                         theme.setDarkMode();
            //                       } else {
            //                         theme.setLightMode();
            //                       }
            //                     },
            //                     activeTrackColor: Colors.lightGreenAccent,
            //                     activeColor: Colors.green,
            //                   )),
            //         ],
            //       ),
            //     ),
            //     Container(
            //       margin: EdgeInsets.symmetric(horizontal: 15),
            //       width: double.infinity,
            //       height: 2,
            //       color: Colors.black12,
            //     )
            //   ],
            // ),
            // accountButton("languange",
            //     AppLocalizations.of(context)!.translate('title_language')!,
            //     func: () {
            //   Navigator.push(context,
            //       MaterialPageRoute(builder: (context) => LanguageScreen()));
            // }),
            // accountButton(
            //     "rateapp", AppLocalizations.of(context)!.translate('rate_app')!,
            //     func: () {
            //   if (Platform.isIOS) {
            //     LaunchReview.launch(writeReview: false, iOSAppId: appId);
            //   } else {
            //     LaunchReview.launch(
            //         androidAppId: generalSettings.packageInfo!.packageName);
            //   }
            // }),
            // accountButton(
            //     "aboutus", AppLocalizations.of(context)!.translate('about_us')!,
            //     func: () {
            //   Navigator.push(
            //       context,
            //       MaterialPageRoute(
            //           builder: (context) => WebViewScreen(
            //                 url: generalSettings.about.description,
            //                 title: AppLocalizations.of(context)!
            //                     .translate('about_us'),
            //               )));
            // }),
            // accountButton(
            //     "privacy", AppLocalizations.of(context)!.translate('privacy')!,
            //     func: () {
            //   Navigator.push(
            //       context,
            //       MaterialPageRoute(
            //           builder: (context) => WebViewScreen(
            //                 url: generalSettings.privacy.description,
            //                 title: AppLocalizations.of(context)!
            //                     .translate('privacy'),
            //               )));
            // }),
            // accountButton("terms_conditions",
            //     AppLocalizations.of(context)!.translate('terms_conditions')!,
            //     func: () {
            //   Navigator.push(
            //       context,
            //       MaterialPageRoute(
            //           builder: (context) => WebViewScreen(
            //                 url: generalSettings.terms.description,
            //                 title: AppLocalizations.of(context)!
            //                     .translate('terms_conditions'),
            //               )));
            // }),
            // accountButton(
            //     "contact", AppLocalizations.of(context)!.translate('contact')!,
            //     func: () {
            //   _launchPhoneURL(generalSettings.phone.description!);
            // }),
            // accountButton(
            //     "logout", AppLocalizations.of(context)!.translate('logout')!,
            //     func: logoutPopDialog),

            ContainerCard(
              child: Column(
                children: [
                  Row(
                    children: [
                      GestureDetector(
                        onTap: () {
                          setState(() {
                            idxView = 0;
                          });
                          Provider.of<WishlistProvider>(context, listen: false)
                              .loadAccountWishlist(context);
                        },
                        child: Column(
                          children: [
                            Container(
                                padding: EdgeInsets.symmetric(horizontal: 10),
                                child: Text(
                                  "${AppLocalizations.of(context)!.translate('wishlist')}",
                                  style: TextStyle(
                                    fontSize: responsiveFont(12),
                                    fontWeight: FontWeight.w600,
                                  ),
                                )),
                            Visibility(
                              visible: idxView == 0,
                              child: Container(
                                height: 5,
                                width: 80,
                                color: primaryColor,
                              ),
                            ),
                            SizedBox(
                              height: 10,
                            )
                          ],
                        ),
                      ),
                      GestureDetector(
                        onTap: () {
                          setState(() {
                            idxView = 1;
                          });
                          Provider.of<ProductProvider>(context, listen: false)
                              .loadHistoryProduct(context);
                        },
                        child: Column(
                          children: [
                            Container(
                              padding: EdgeInsets.symmetric(horizontal: 10),
                              child: Text(
                                "${AppLocalizations.of(context)!.translate('history')}",
                                style: TextStyle(
                                  fontSize: responsiveFont(12),
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            Visibility(
                              visible: idxView == 1,
                              child: Container(
                                height: 5,
                                width: 80,
                                color: primaryColor,
                              ),
                            ),
                            SizedBox(
                              height: 10,
                            )
                          ],
                        ),
                      )
                    ],
                  ),
                  Visibility(visible: idxView == 0, child: wishlist()),
                  Visibility(visible: idxView == 1, child: history())
                ],
              ),
            ),

            Container(
              margin: EdgeInsets.symmetric(horizontal: 15, vertical: 5),
              alignment: Alignment.centerLeft,
              child: FutureBuilder(
                future: _init(),
                builder: (context, snapshot) {
                  if (snapshot.hasData) {
                    _versionName = snapshot.data as String?;
                    return Text(
                      '${AppLocalizations.of(context)!.translate('version')} ' +
                          _versionName!,
                      style: TextStyle(
                          fontWeight: FontWeight.w300,
                          fontSize: responsiveFont(10)),
                    );
                  } else {
                    return Container();
                  }
                },
              ),
              // Text(
              //   "${AppLocalizations.of(context).translate('version')} $version",
              //   style: TextStyle(
              //       fontWeight: FontWeight.w300, fontSize: responsiveFont(10)),
              // ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> listWidget = [];

  Widget wishlist() {
    return Consumer<WishlistProvider>(
      builder: (context, value, child) => Container(
        child: isLogin
            ? MasonryGridView.count(
                shrinkWrap: true,
                physics: ScrollPhysics(),
                crossAxisCount: 2,
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                itemCount: value.listProductWishlistAccount.length + 1,
                itemBuilder: (context, index) {
                  if (index == 0) {
                    return GestureDetector(
                      onTap: () {
                        Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => WishList(),
                            )).then((value) {
                          Provider.of<WishlistProvider>(context, listen: false)
                              .loadAccountWishlist(context);
                        });
                      },
                      child: Container(
                        padding:
                            EdgeInsets.symmetric(vertical: 10, horizontal: 10),
                        decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(5),
                            color: HexColor("f5f5f5")),
                        child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              Text(
                                "${AppLocalizations.of(context)!.translate('view_all')}",
                                style: TextStyle(fontWeight: FontWeight.w600),
                              ),
                              Icon(Icons.arrow_forward)
                            ]),
                      ),
                    );
                  }
                  return value.loadingWishlist
                      ? shimmerCard()
                      : value.listProductWishlistAccount.length > 0
                          ? cardWishlist(
                              value.listProductWishlistAccount[index - 1])
                          : Container();
                },
              )
            : Container(
                width: MediaQuery.of(context).size.width,
                height: 100.h,
                // color: primaryColor,
                child: Center(
                    child: GestureDetector(
                  onTap: () {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => Login(),
                        ));
                  },
                  child: Container(
                      decoration: BoxDecoration(
                          color: primaryColor,
                          borderRadius: BorderRadius.circular(10)),
                      width: 90.w,
                      height: 30.h,
                      child: Center(child: Text("Login"))),
                )),
              ),
      ),
    );
  }

  Widget shimmerCard() {
    return Shimmer.fromColors(
        child: Container(
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(5), color: Colors.white),
          width: 80.w,
          height: 80.h,
        ),
        baseColor: Colors.grey[300]!,
        highlightColor: Colors.grey[100]!);
  }

  Widget cardWishlist(ProductModel product) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ProductDetail(
                productId: product.id.toString(),
              ),
            )).then((value) {
          Provider.of<WishlistProvider>(context, listen: false)
              .loadAccountWishlist(context);
        });
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(5),
                child: CachedNetworkImage(
                  imageUrl: product.image!,
                  fit: BoxFit.fill,
                  placeholder: (context, url) => customLoading(),
                  errorWidget: (context, url, error) =>
                      Icon(Icons.image_not_supported),
                ),
              ),
            ),
          ),
          Text(
            product.productName!,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
          ),
          Text(
            stringToCurrency(
                double.parse(product.productPrice.toString()), context),
            style: TextStyle(fontSize: 10, color: Colors.grey[400]),
          )
        ],
      ),
    );
  }

  Widget history() {
    return Consumer<ProductProvider>(
      builder: (context, value, child) => Container(
        child: isLogin
            ? MasonryGridView.count(
                shrinkWrap: true,
                physics: ScrollPhysics(),
                crossAxisCount: 2,
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                itemCount: value.listHistoryProduct.length + 1,
                itemBuilder: (context, index) {
                  if (index == 0) {
                    return GestureDetector(
                      onTap: () {
                        Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => ProductMoreScreen(
                                name: AppLocalizations.of(context)!
                                    .translate('recent_view')!,
                                include: value.productRecent,
                              ),
                            ));
                      },
                      child: Container(
                        padding:
                            EdgeInsets.symmetric(vertical: 10, horizontal: 10),
                        decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(5),
                            color: HexColor("f5f5f5")),
                        child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              Text(
                                "${AppLocalizations.of(context)!.translate('view_all')}",
                                style: TextStyle(fontWeight: FontWeight.w600),
                              ),
                              Icon(Icons.arrow_forward)
                            ]),
                      ),
                    );
                  }
                  return value.loadingHistory
                      ? shimmerCard()
                      : value.listHistoryProduct.length > 0
                          ? cardHistory(value.listHistoryProduct[index - 1])
                          : Container();
                },
              )
            : Container(
                width: MediaQuery.of(context).size.width,
                height: 100.h,
                // color: primaryColor,
                child: Center(
                    child: GestureDetector(
                  onTap: () {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => Login(),
                        ));
                  },
                  child: Container(
                      decoration: BoxDecoration(
                          color: primaryColor,
                          borderRadius: BorderRadius.circular(10)),
                      width: 90.w,
                      height: 30.h,
                      child: Center(child: Text("Login"))),
                )),
              ),
      ),
    );
  }

  Widget cardHistory(ProductModel product) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ProductDetail(
                productId: product.id.toString(),
              ),
            )).then((value) {
          Provider.of<ProductProvider>(context, listen: false)
              .loadHistoryProduct(context);
        });
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(5),
                child: CachedNetworkImage(
                  imageUrl: product.image!,
                  fit: BoxFit.fill,
                  placeholder: (context, url) => customLoading(),
                  errorWidget: (context, url, error) =>
                      Icon(Icons.image_not_supported),
                ),
              ),
            ),
          ),
          Text(
            product.productName!,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
          ),
          Text(
            stringToCurrency(
                double.parse(product.productPrice.toString()), context),
            style: TextStyle(fontSize: 10, color: Colors.grey[400]),
          )
        ],
      ),
    );
  }

  Widget hello(UserProvider user) {
    return ContainerCard(
        child: Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        isLogin
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  user.loading
                      ? Text(
                          "${AppLocalizations.of(context)!.translate('hello')}",
                          style: TextStyle(
                              color: Colors.black,
                              fontSize: responsiveFont(14),
                              fontWeight: FontWeight.w500),
                        )
                      : Text(
                          "${AppLocalizations.of(context)!.translate('hello')}, ${Session.data.getString('firstname')!.length > 10 ? Session.data.getString('firstname')!.substring(0, 10) + '... ' : Session.data.getString('firstname')} !",
                          style: TextStyle(
                              color: Colors.black,
                              fontSize: responsiveFont(14),
                              fontWeight: FontWeight.w500),
                        ),
                  Text(
                    AppLocalizations.of(context)!.translate('welcome_back')!,
                    style: TextStyle(fontSize: responsiveFont(9)),
                  ),
                ],
              )
            : Row(
                children: [
                  Container(
                      decoration: BoxDecoration(
                          shape: BoxShape.circle, color: Colors.grey[200]),
                      child: Icon(
                        Icons.person,
                        size: 25.h,
                      )),
                  SizedBox(
                    width: 10.w,
                  ),
                  GestureDetector(
                    onTap: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => Login(),
                          ));
                    },
                    child: Container(
                      padding:
                          EdgeInsets.symmetric(horizontal: 9.w, vertical: 3.h),
                      decoration: BoxDecoration(
                          color: Colors.grey[100],
                          borderRadius: BorderRadius.circular(20.h)),
                      child: Text(
                          "${AppLocalizations.of(context)!.translate('login_register')}"),
                    ),
                  ),
                ],
              ),
        isLogin
            ? button("logout",
                AppLocalizations.of(context)!.translate('logout')!, false,
                func: logoutPopDialog)
            : Container(),
      ],
    ));
  }

  Widget account(UserProvider point) {
    return ContainerCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            AppLocalizations.of(context)!.translate('account')!,
            style: TextStyle(
                fontSize: responsiveFont(12),
                fontWeight: FontWeight.w600,
                color: Colors.black),
          ),
          SizedBox(
            height: 10,
          ),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 5),
            child: GridView.count(
              shrinkWrap: true,
              physics: ScrollPhysics(),
              mainAxisSpacing: 15,
              crossAxisCount: 5,
              crossAxisSpacing: 4.5,
              children: [
                button(
                    "akun",
                    AppLocalizations.of(context)!.translate('title_myAccount')!,
                    false, func: () {
                  if (isLogin) {
                    Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (context) => AccountDetailScreen()))
                        .then((value) => this.setState(() {}));
                  } else if (!isLogin) {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => NotLoginScreen()));
                  }
                }, fiveItems: true),
                button(
                    "address",
                    "${AppLocalizations.of(context)!.translate('my_address')}",
                    false, func: () {
                  if (isLogin) {
                    Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (context) => AccountAddressScreen()))
                        .then((value) => this.setState(() {}));
                  } else if (!isLogin) {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => NotLoginScreen()));
                  }
                }, fiveItems: true),
                button(
                    "review",
                    AppLocalizations.of(context)!.translate('review')!,
                    false, func: () {
                  if (isLogin) {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => ReviewScreen()));
                  } else if (!isLogin) {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => NotLoginScreen()));
                  }
                }, fiveItems: true),
                button(
                    "location",
                    "${AppLocalizations.of(context)!.translate('track_order')}",
                    false, func: () {
                  if (isLogin) {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => WebViewScreen(
                                  fromNotif: false,
                                  title:
                                      "${AppLocalizations.of(context)!.translate('track_order')}",
                                  url:
                                      "https://www.uellow.com/track-your-order",
                                )));
                  } else if (!isLogin) {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => NotLoginScreen()));
                  }
                }, socmed: true, fiveItems: true),
                Visibility(
                  visible: point.point != null,
                  child: button(
                      "coin",
                      AppLocalizations.of(context)!.translate('my_point')!,
                      false, func: () {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => MyPoint(),
                        )).then((value) => this.setState(() {}));
                  }, fiveItems: true),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  _launchURL(String url) async {
    if (await canLaunchUrlString(url)) {
      await launchUrlString(url, mode: LaunchMode.externalApplication);
    } else {
      throw 'Could not launch $url';
    }
  }

  Widget socialMedia() {
    final socmed = Provider.of<HomeProvider>(context, listen: false).sosmedLink;

    return ContainerCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            AppLocalizations.of(context)!.translate('social_media')!,
            style: TextStyle(
                fontSize: responsiveFont(12),
                fontWeight: FontWeight.w600,
                color: Colors.black),
          ),
          SizedBox(
            height: 10,
          ),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 5),
            child: GridView.count(
              shrinkWrap: true,
              physics: ScrollPhysics(),
              mainAxisSpacing: 15,
              crossAxisCount: 5,
              crossAxisSpacing: 4.5,
              children: [
                button("whatsapp_outline", "Whatsapp", false, func: () {
                  _launchURL(socmed.description['whatsapp']);
                }, socmed: true, fiveItems: true),
                button("facebook_outline", "Facebook", false, func: () {
                  _launchURL(socmed.description['facebook']);
                }, socmed: true, fiveItems: true),
                button("instagram_outline", "Instagram", false, func: () {
                  _launchURL(socmed.description['instagram']);
                }, socmed: true, fiveItems: true),
                button("youtube_outline", "Youtube", false, func: () {
                  _launchURL(socmed.description['youtube']);
                }, socmed: true, fiveItems: true),
                button("tiktok_outline", "Tiktok", false, func: () {
                  _launchURL(socmed.description['tiktok']);
                }, socmed: true, fiveItems: true),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget order() {
    return ContainerCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              "${AppLocalizations.of(context)!.translate('orders')}",
              style: TextStyle(
                  fontSize: responsiveFont(12),
                  fontWeight: FontWeight.w600,
                  color: Colors.black),
            ),
            InkWell(
              onTap: () {
                if (Session.data.getBool('isLogin')!) {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MyOrder(
                            fromAccountScreen: false, currentStatus: ''),
                      ));
                } else {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => Login(),
                      ));
                }
              },
              child: Text(
                "${AppLocalizations.of(context)!.translate('view_all')}",
                style: TextStyle(
                    fontSize: responsiveFont(10), fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
        SizedBox(
          height: 10,
        ),
        Container(
          padding: EdgeInsets.symmetric(horizontal: 5),
          child: GridView.count(
            shrinkWrap: true,
            physics: ScrollPhysics(),
            mainAxisSpacing: 15,
            crossAxisCount: 5,
            crossAxisSpacing: 4.5,
            children: [
              // button("all_dark", "All", true, func: () {
              //   Navigator.push(
              //       context,
              //       MaterialPageRoute(
              //         builder: (context) => MyOrder(
              //           fromAccountScreen: true,
              //           currentStatus: '',
              //         ),
              //       ));
              // }),
              button(
                  "pending_dark",
                  AppLocalizations.of(context)!.translate('pending')!,
                  true, func: () {
                if (Session.data.getBool('isLogin')!) {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MyOrder(
                          fromAccountScreen: true,
                          currentStatus: 'pending',
                        ),
                      ));
                } else {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => Login(),
                      ));
                }
              }),
              button(
                  "hold_dark",
                  AppLocalizations.of(context)!.translate('on_hold')!,
                  true, func: () {
                if (Session.data.getBool('isLogin')!) {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MyOrder(
                          fromAccountScreen: true,
                          currentStatus: 'on-hold',
                        ),
                      ));
                } else {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => Login(),
                      ));
                }
              }),
              button(
                  "processing_dark",
                  AppLocalizations.of(context)!.translate('processing')!,
                  true, func: () {
                if (Session.data.getBool('isLogin')!) {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MyOrder(
                          fromAccountScreen: true,
                          currentStatus: 'processing',
                        ),
                      ));
                } else {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => Login(),
                      ));
                }
              }),
              button(
                  "completed_dark",
                  AppLocalizations.of(context)!.translate('completed')!,
                  true, func: () {
                if (Session.data.getBool('isLogin')!) {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MyOrder(
                          fromAccountScreen: true,
                          currentStatus: 'completed',
                        ),
                      ));
                } else {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => Login(),
                      ));
                }
              }),
              button(
                  "cancel_dark",
                  AppLocalizations.of(context)!.translate('cancel')!,
                  true, func: () {
                if (Session.data.getBool('isLogin')!) {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => MyOrder(
                          fromAccountScreen: true,
                          currentStatus: 'cancelled',
                        ),
                      ));
                } else {
                  Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => Login(),
                      ));
                }
              }),
            ],
          ),
        ),
      ]),
    );
  }

  Widget generalSetting(HomeProvider generalSettings) {
    return Consumer<HomeProvider>(
      builder: (context, value, child) {
        return ContainerCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                AppLocalizations.of(context)!.translate('general_setting')!,
                style: TextStyle(
                    fontSize: responsiveFont(12),
                    fontWeight: FontWeight.w600,
                    color: Colors.black),
              ),
              SizedBox(
                height: 10,
              ),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 5),
                child: GridView.count(
                  shrinkWrap: true,
                  physics: ScrollPhysics(),
                  mainAxisSpacing: 15,
                  crossAxisCount: 5,
                  crossAxisSpacing: 4.5,
                  children: [
                    button(
                        "languange",
                        AppLocalizations.of(context)!
                            .translate('title_language')!,
                        false, func: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (context) => LanguageScreen()));
                    }),
                    button(
                      "pending_dark",
                      "${AppLocalizations.of(context)!.translate('currency')}",
                      true,
                      func: () {
                        Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (context) => CurrencyScreen()));
                      },
                    ),
                    button(
                        "rateapp",
                        AppLocalizations.of(context)!.translate('rate_app')!,
                        false, func: () {
                      if (Platform.isIOS) {
                        LaunchReview.launch(
                            writeReview: false, iOSAppId: appId);
                      } else {
                        LaunchReview.launch(
                            androidAppId:
                                generalSettings.packageInfo!.packageName);
                      }
                    }),
                    button(
                        "aboutus",
                        AppLocalizations.of(context)!.translate('about_us')!,
                        false, func: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (context) => WebViewScreen(
                                    url: generalSettings.about.description,
                                    title: AppLocalizations.of(context)!
                                        .translate('about_us'),
                                  )));
                    }),
                    button(
                        "privacy",
                        AppLocalizations.of(context)!.translate('privacy')!,
                        false, func: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (context) => WebViewScreen(
                                    url: generalSettings.privacy.description,
                                    title: AppLocalizations.of(context)!
                                        .translate('privacy'),
                                  )));
                    }),
                    button(
                        "terms_conditions",
                        AppLocalizations.of(context)!
                            .translate('terms_conditions')!,
                        false, func: () {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (context) => WebViewScreen(
                                    url: generalSettings.terms.description,
                                    title: AppLocalizations.of(context)!
                                        .translate('terms_conditions'),
                                  )));
                    }),
                    for (int i = 0; i < value.additionalMenus.length; i++)
                      buttonAdditional(
                          value.additionalMenus[i].iconUrl!,
                          value.additionalMenus[i].title!,
                          value.additionalMenus[i].link!),
                    button(
                        "contact",
                        AppLocalizations.of(context)!.translate('contact')!,
                        false, func: () {
                      // _launchPhoneURL(generalSettings.phone.description!);
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => ProductForm(
                              isFromAccount: true,
                            ),
                          ));
                    }),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget buttonAdditional(String image, String title, String url) {
    return InkWell(
      onTap: () {
        var link;
        if (Session.data.containsKey('language_code') == true) {
          if (Session.data.getString('language_code') != 'en') {
            link = url.replaceAll(
                'www', '${Session.data.getString('language_code')}');
          } else {
            link = url;
          }
        } else {
          link = url;
        }
        Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => WebViewScreen(url: link, title: title),
            ));
      },
      child: Container(
        width: 66,
        child: Column(
          children: [
            Container(
                width: 30.w,
                height: 30.h,
                child: CachedNetworkImage(
                  imageUrl: image,
                  placeholder: (context, url) => customLoading(),
                  errorWidget: (context, url, error) =>
                      Icon(Icons.image_not_supported),
                )),
            SizedBox(
              width: 10,
            ),
            Text(
              title,
              style: TextStyle(fontSize: responsiveFont(8)),
              textAlign: TextAlign.center,
            )
          ],
        ),
      ),
    );
  }

  Widget button(String image, String title, bool order,
      {var func, bool socmed = false, bool fiveItems = false}) {
    return InkWell(
      onTap: func,
      child: Container(
        width: fiveItems ? 50 : 66,
        child: Column(children: [
          Container(
              width: 30.w,
              height: 30.h,
              child: order
                  ? Image.asset("images/order/$image.png")
                  : Image.asset(
                      "images/account/$image.png",
                      color: socmed ? Colors.grey[700] : null,
                    )),
          SizedBox(
            width: 10,
          ),
          image == "logout"
              ? Text(
                  title,
                  style: TextStyle(fontSize: responsiveFont(7)),
                  textAlign: TextAlign.center,
                )
              : Expanded(
                  child: Text(
                    title,
                    style: TextStyle(fontSize: responsiveFont(7)),
                    textAlign: TextAlign.center,
                    overflow: TextOverflow.ellipsis,
                  ),
                )
        ]),
      ),
    );
  }

  Widget accountButton(String image, String title, {var func}) {
    return Column(
      children: [
        InkWell(
          onTap: func,
          child: Container(
            padding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                        width: 25.w,
                        height: 25.h,
                        child: Image.asset("images/account/$image.png")),
                    SizedBox(
                      width: 10,
                    ),
                    Text(
                      title,
                      style: TextStyle(fontSize: responsiveFont(11)),
                    )
                  ],
                ),
                Icon(Icons.keyboard_arrow_right)
              ],
            ),
          ),
        ),
        Container(
          margin: EdgeInsets.symmetric(horizontal: 15),
          width: double.infinity,
          height: 2,
          color: Colors.black12,
        )
      ],
    );
  }

  Widget buildPointCard() {
    final point = Provider.of<UserProvider>(context, listen: false);
    String fullName =
        "${Session.data.getString('firstname')} ${Session.data.getString('lastname')}";

    if (point.point == null) {
      return Container();
    }
    return Container(
        margin: EdgeInsets.only(top: 15, left: 10, right: 10),
        child: Stack(
          children: [
            SizedBox(
                height: MediaQuery.of(context).size.height / 7,
                width: double.infinity,
                child: Image.asset(
                  "images/account/card_point.png",
                  fit: BoxFit.fill,
                )),
            // Positioned(
            //   child: Container(
            //     padding: EdgeInsets.symmetric(vertical: 5, horizontal: 15),
            //     decoration: BoxDecoration(
            //         color: Colors.white30,
            //         borderRadius: BorderRadius.circular(5)),
            //     child: Text(
            //       Session.data
            //           .getString('role')!
            //           .replaceAll('_', ' ')
            //           .toUpperCase(),
            //       style: TextStyle(
            //           fontSize: responsiveFont(12),
            //           color: Colors.black,
            //           fontWeight: FontWeight.w600),
            //     ),
            //   ),
            //   top: 15,
            //   right: 15,
            // ),
            Positioned(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(AppLocalizations.of(context)!.translate('full_name')!,
                      style: TextStyle(
                          fontSize: responsiveFont(10),
                          color: Colors.black,
                          fontWeight: FontWeight.w400)),
                  Session.data.getBool('isLogin')!
                      ? Text(
                          fullName.length > 10
                              ? fullName.substring(0, 10) + '... '
                              : fullName,
                          style: TextStyle(
                              fontSize: responsiveFont(18),
                              color: Colors.black,
                              fontWeight: FontWeight.w600),
                        )
                      : Text(
                          "Login First",
                          style: TextStyle(
                              fontSize: responsiveFont(18),
                              fontWeight: FontWeight.bold),
                        )
                ],
              ),
              bottom: 10,
              left: 15,
            ),
            Positioned(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(AppLocalizations.of(context)!.translate('total_point')!,
                      style: TextStyle(
                          fontSize: responsiveFont(10),
                          color: Colors.black,
                          fontWeight: FontWeight.w400)),
                  point.loading
                      ? Text(
                          '-',
                          style: TextStyle(
                              fontSize: responsiveFont(18),
                              color: Colors.black,
                              fontWeight: FontWeight.w600),
                        )
                      : Text(
                          Session.data.getBool('isLogin')! == false
                              ? '0'
                              : '${point.point!.pointsBalance} ${point.point!.pointsLabel}',
                          style: TextStyle(
                              fontSize: responsiveFont(18),
                              color: Colors.black,
                              fontWeight: FontWeight.w600),
                        )
                ],
              ),
              bottom: 10,
              right: 15,
            )
          ],
        ));
  }

  logoutPopDialog() {
    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;
    return showDialog(
      context: context,
      builder: (context) => AlertDialog(
          backgroundColor: Colors.white,
          contentPadding: EdgeInsets.zero,
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.all(Radius.circular(15.0))),
          insetPadding: EdgeInsets.all(0),
          content: Builder(
            builder: (context) {
              return Container(
                height: 150.h,
                width: 330.w,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      children: [
                        SizedBox(
                          height: 15,
                        ),
                        Text(
                          AppLocalizations.of(context)!
                              .translate('title_exit_alert')!,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                              fontSize: responsiveFont(14),
                              fontWeight: FontWeight.w500),
                        ),
                        SizedBox(
                          height: 15,
                        ),
                        Text(
                          AppLocalizations.of(context)!
                              .translate('logout_body_alert')!,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                              fontSize: responsiveFont(12),
                              fontWeight: FontWeight.w400),
                        ),
                      ],
                    ),
                    Container(
                        child: Column(
                      children: [
                        Container(
                          color: Colors.black12,
                          height: 2,
                        ),
                        Row(
                          children: [
                            Expanded(
                              flex: 2,
                              child: GestureDetector(
                                onTap: () => Navigator.of(context).pop(false),
                                child: Container(
                                  alignment: Alignment.center,
                                  padding: EdgeInsets.symmetric(vertical: 12),
                                  decoration: BoxDecoration(
                                      borderRadius: locale == Locale('ar')
                                          ? BorderRadius.only(
                                              bottomRight: Radius.circular(15))
                                          : BorderRadius.only(
                                              bottomLeft: Radius.circular(15)),
                                      color: primaryColor),
                                  child: Text(
                                    AppLocalizations.of(context)!
                                        .translate('no')!,
                                    style: TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.w500),
                                  ),
                                ),
                              ),
                            ),
                            Expanded(
                              flex: 2,
                              child: GestureDetector(
                                onTap: () => logout(),
                                child: Container(
                                  alignment: Alignment.center,
                                  padding: EdgeInsets.symmetric(vertical: 12),
                                  decoration: BoxDecoration(
                                      borderRadius: locale == Locale('ar')
                                          ? BorderRadius.only(
                                              bottomLeft: Radius.circular(15))
                                          : BorderRadius.only(
                                              bottomRight: Radius.circular(15)),
                                      color: Colors.white),
                                  child: Text(
                                    AppLocalizations.of(context)!
                                        .translate('yes')!,
                                    style: TextStyle(
                                        fontWeight: FontWeight.w500,
                                        color: primaryColor),
                                  ),
                                ),
                              ),
                            )
                          ],
                        ),
                      ],
                    ))
                  ],
                ),
              );
            },
          )),
    );
  }
}
