import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/deeplink/deeplink_config.dart';
import 'package:nyoba/models/notification_model.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/pages/home/home_screen.dart';
import 'package:nyoba/pages/order/cart_screen.dart';
import 'package:nyoba/pages/order/order_detail_screen.dart';
import 'package:nyoba/provider/notification_provider.dart';
import 'package:nyoba/services/session.dart';
import 'package:provider/provider.dart';
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:shimmer/shimmer.dart';

import '../../app_localizations.dart';
import '../../utils/utility.dart';

class NotificationScreen extends StatefulWidget {
  bool? fromPushNotif = false;

  NotificationScreen({Key? key, this.fromPushNotif}) : super(key: key);

  @override
  _NotificationScreenState createState() => _NotificationScreenState();
}

class _NotificationScreenState extends State<NotificationScreen> {
  int selectedIndex = 0;
  int cartCount = 0;
  RefreshController _refreshController =
      RefreshController(initialRefresh: false);

  @override
  void initState() {
    super.initState();
    load();
  }

  load() async {
    if (Session.data.getBool('isLogin')!) {
      await Provider.of<NotificationProvider>(context, listen: false)
          .fetchNotifications(context: context);
      _refreshController.refreshCompleted();
    }
    loadCartCount();
  }

  Future loadCartCount() async {
    print('Load Count');
    List<ProductModel> productCart = [];
    int _count = 0;

    if (Session.data.containsKey('cart')) {
      List listCart = await json.decode(Session.data.getString('cart')!);

      productCart = listCart
          .map((product) => new ProductModel.fromJson(product))
          .toList();

      productCart.forEach((element) {
        _count += element.cartQuantity!;
      });
    }
    setState(() {
      cartCount = _count;
    });
  }

  @override
  Widget build(BuildContext context) {
    final notification =
        Provider.of<NotificationProvider>(context, listen: false);
    Widget buildNotification = Container(
      child: ListenableProvider.value(
        value: notification,
        child: Consumer<NotificationProvider>(builder: (context, value, child) {
          if (value.isLoading) {
            return ListView.separated(
              shrinkWrap: true,
              itemBuilder: (context, i) {
                return GestureDetector(onTap: null, child: itemShimmer());
              },
              itemCount: 6,
              separatorBuilder: (BuildContext context, int index) {
                return Container(
                  // margin: EdgeInsets.symmetric(vertical: 18),
                  width: double.infinity,
                  height: 1,
                  color: HexColor("c4c4c4"),
                );
              },
            );
          }
          return ListView.separated(
            shrinkWrap: true,
            physics: ScrollPhysics(),
            itemBuilder: (context, i) {
              return GestureDetector(
                  onTap: () async {
                    if (value.notification[i].type == 'push_notif') {
                      var _payload =
                          value.notification[i].description!['link_to'];
                      var _title = value.notification[i].description!['title'];

                      Uri uri = Uri.parse(_payload);
                      printLog(uri.toString(), name: "URL");
                      DeeplinkConfig().pathUrl(uri, context, false);

                      await Provider.of<NotificationProvider>(context,
                              listen: false)
                          .fetchReadNotif(int.parse(value.notification[i].id!),
                              value.notification[i].type!, context);
                      load();
                    } else {
                      await Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (context) => OrderDetail(
                                    orderId: value
                                        .notification[i].description!['link_to']
                                        .toString(),
                                  )));
                      loadCartCount();
                      await Provider.of<NotificationProvider>(context,
                              listen: false)
                          .fetchReadNotif(int.parse(value.notification[i].id!),
                              value.notification[i].type!, context);
                      load();
                    }
                  },
                  child: itemList(value.notification[i]));
            },
            itemCount: value.notification.length,
            separatorBuilder: (BuildContext context, int index) {
              return Container(
                // margin: EdgeInsets.symmetric(vertical: 18),
                width: double.infinity,
                height: 1,
                color: HexColor("c4c4c4"),
              );
            },
          );
        }),
      ),
    );

    return WillPopScope(
      onWillPop: () async {
        if (widget.fromPushNotif == true) {
          Navigator.pushAndRemoveUntil(
              context,
              MaterialPageRoute(
                builder: (context) => HomeScreen(),
              ),
              (route) => false);
        } else {
          Navigator.pop(context);
        }

        return true;
      },
      child: Scaffold(
        appBar: AppBar(
          elevation: 0,
          backgroundColor: Colors.white,
          surfaceTintColor: Colors.transparent,
          leading: IconButton(
            onPressed: () {
              if (widget.fromPushNotif == true) {
                Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(
                      builder: (context) => HomeScreen(),
                    ),
                    (route) => false);
              } else {
                Navigator.pop(context);
              }
            },
            icon: Icon(Icons.arrow_back, color: Colors.black),
          ),
          title: Container(
            height: 38,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  AppLocalizations.of(context)!.translate('notification')!,
                  style: TextStyle(
                      color: Colors.black,
                      fontSize: responsiveFont(16),
                      fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),
          actions: [
            InkWell(
              onTap: () {
                Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (context) => CartScreen(
                              isFromHome: false,
                            )));
              },
              child: Container(
                width: 65,
                height: 65,
                padding: EdgeInsets.symmetric(horizontal: 8),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Icon(
                      Icons.shopping_cart,
                      color: Colors.black,
                    ),
                    Positioned(
                      right: 7,
                      top: 7,
                      child: Container(
                        padding:
                            EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                            shape: BoxShape.circle, color: primaryColor),
                        alignment: Alignment.center,
                        child: Text(
                          cartCount.toString(),
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.black,
                            fontSize: responsiveFont(9),
                          ),
                        ),
                      ),
                    )
                  ],
                ),
              ),
            ),
          ],
        ),
        body: Session.data.getBool('isLogin')!
            ? SmartRefresher(
                controller: _refreshController,
                onRefresh: load,
                child: Container(
                    margin: EdgeInsets.all(15), child: buildNotification),
              )
            : Center(
                child: buildNoAuth(context),
              ),
      ),
    );
  }

  Widget itemList(NotificationModel notification) {
    return Container(
      padding: EdgeInsets.symmetric(vertical: 18),
      color: notification.isRead != 0 ? null : Color(0xfffff8e8),
      child: Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(5),
                ),
                width: 80.h,
                height: 80.h,
                child: notification.description!["image"] == null
                    ? Icon(
                        Icons.broken_image_outlined,
                        size: 80,
                      )
                    : Image.network(
                        notification.description!["image"],
                        errorBuilder: (BuildContext context, Object exception,
                            StackTrace? stackTrace) {
                          return Icon(
                            Icons.broken_image_outlined,
                            size: 128,
                          );
                        },
                      ),
              ),
              SizedBox(
                width: 15,
              ),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "${notification.description!['title']}",
                          style: TextStyle(
                              fontSize: responsiveFont(10),
                              fontWeight: FontWeight.w500),
                        ),
                        SizedBox(
                          width: 5,
                        ),
                        RichText(
                          text: TextSpan(
                            style: TextStyle(color: Colors.black),
                            children: <TextSpan>[
                              TextSpan(
                                  text:
                                      '${AppLocalizations.of(context)!.translate('order_with_number')} ',
                                  style: TextStyle(
                                      fontWeight: FontWeight.w300,
                                      fontSize: responsiveFont(9))),
                              TextSpan(
                                  text: notification.id.toString(),
                                  style: TextStyle(
                                      fontWeight: FontWeight.w300,
                                      fontSize: responsiveFont(9),
                                      color: Colors.red[700])),
                              // TextSpan(
                              //     text: buildNotificationSubtitle(
                              //         notification.status, context),
                              //     style: TextStyle(
                              //         fontWeight: FontWeight.w300,
                              //         fontSize: responsiveFont(9))),
                            ],
                          ),
                        ),
                        SizedBox(
                          height: 5,
                        ),
                      ],
                    ),
                    SizedBox(
                      height: 20.h,
                    ),
                    Row(
                      children: [
                        Icon(Icons.query_builder),
                        SizedBox(
                          width: 5,
                        ),
                        Text(
                          notification.createdAt!,
                          style: TextStyle(
                              fontSize: responsiveFont(8),
                              fontWeight: FontWeight.w300),
                        )
                      ],
                    )
                  ],
                ),
              )
            ],
          )
        ],
      ),
    );
  }

  Widget itemShimmer() {
    return Column(
      children: [
        Shimmer.fromColors(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(5),
                    color: Colors.white,
                  ),
                  width: 80.h,
                  height: 80.h,
                ),
                SizedBox(
                  width: 15,
                ),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 150,
                            height: 10,
                            color: Colors.white,
                          ),
                          SizedBox(
                            height: 10,
                          ),
                          Container(
                            width: double.infinity,
                            height: 10,
                            color: Colors.white,
                          ),
                          SizedBox(
                            height: 5,
                          ),
                          Container(
                            width: double.infinity,
                            height: 10,
                            color: Colors.white,
                          ),
                          SizedBox(
                            height: 5,
                          ),
                        ],
                      ),
                      SizedBox(
                        height: 20.h,
                      ),
                      Row(
                        children: [
                          Icon(Icons.query_builder),
                          SizedBox(
                            width: 5,
                          ),
                          Container(
                            width: 100,
                            height: 10,
                            color: Colors.white,
                          ),
                        ],
                      )
                    ],
                  ),
                )
              ],
            ),
            baseColor: Colors.grey[300]!,
            highlightColor: Colors.grey[100]!)
      ],
    );
  }
}
