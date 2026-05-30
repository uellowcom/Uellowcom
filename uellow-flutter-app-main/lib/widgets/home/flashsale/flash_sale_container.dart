import 'package:flutter/material.dart';
import 'package:flutter_countdown_timer/current_remaining_time.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/pages/product/product_more_screen.dart';
import 'package:nyoba/provider/flash_sale_provider.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:nyoba/widgets/home/card_item_small.dart';
import 'package:provider/provider.dart';

class FlashSaleContainer extends StatelessWidget {
  final AnimationController? colorAnimationController;
  final AnimationController? textAnimationController;

  final Animation? colorTween, titleColorTween, iconColorTween, moveTween;
  final List<ProductModel>? dataProducts;
  final String? customImage;

  final bool? loading;

  CurrentRemainingTime time;

  FlashSaleContainer(
      {this.colorAnimationController,
      this.textAnimationController,
      this.colorTween,
      this.titleColorTween,
      this.iconColorTween,
      this.moveTween,
      this.dataProducts,
      this.loading,
      this.customImage,
      required this.time});

  bool scrollListener(ScrollNotification scrollInfo) {
    if (scrollInfo.metrics.axis == Axis.horizontal) {
      colorAnimationController!.animateTo(scrollInfo.metrics.pixels / 150);
      textAnimationController!
          .animateTo((scrollInfo.metrics.pixels - 350) / 50);
      return true;
    } else {
      return false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final flashSale = Provider.of<FlashSaleProvider>(context, listen: false);
    final home = Provider.of<HomeProvider>(context, listen: false);

    List<ProductModel> _list = [];

    _list.addAll(dataProducts!);

    int? hours = time.hours ?? 0;
    if (time.days != null && time.days != 0) {
      hours = (time.days! * 24) + time.hours!;
    } else if (time.hours != null) {
      hours = time.hours;
    } else if (time.hours == null) {
      hours = 0;
    } else if (time.hours == null && time.min == null && time.sec == null) {
      flashSale.fetchFlashSale(context);
      return Text(
          '${AppLocalizations.of(context)!.translate('flashsale_end')}');
    }

    return NotificationListener<ScrollNotification>(
      onNotification: scrollListener,
      child: AspectRatio(
        aspectRatio: 3 / 2,
        child: Container(
          decoration: home.flashSaleBgImage == ''
              ? BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment(
                        0.8, 0.0), // 10% of the width, so there are ten blinds.
                    colors: [
                      home.flashSaleBGColorPrimary!,
                      home.flashSaleBGColorSecondary!
                    ],
                    tileMode: TileMode
                        .repeated, // repeats the gradient over the canvas
                  ),
                )
              : BoxDecoration(
                  image: DecorationImage(
                      image: NetworkImage("${home.flashSaleBgImage}"),
                      fit: BoxFit.cover)),
          width: double.infinity,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                height: 10.h,
              ),
              Container(
                margin: EdgeInsets.symmetric(horizontal: 25.w),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Image.network(
                          customImage!,
                          width: 120.w,
                        ),
                        // Text(
                        //   "${AppLocalizations.of(context)!.translate('flash_deals')}",
                        //   style: TextStyle(
                        //       fontWeight: FontWeight.bold,
                        //       fontSize: responsiveFont(16)),
                        // ),
                        Row(
                          children: [
                            Text(
                              "${AppLocalizations.of(context)!.translate('end_in')}",
                              style: TextStyle(color: home.flashSaleText),
                            ),
                            SizedBox(
                              width: 4.w,
                            ),
                            Row(
                              children: [
                                Text(
                                  hours! < 10 ? "0$hours" : "$hours",
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                      color: home.flashSaleText,
                                      fontSize: responsiveFont(10)),
                                ),
                                Text(
                                  ":",
                                  style: TextStyle(
                                      fontSize: responsiveFont(12),
                                      color: home.flashSaleText),
                                ),
                                Text(
                                  time.min == null
                                      ? "00"
                                      : time.min! < 10
                                          ? "0${time.min}"
                                          : "${time.min}",
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                      color: home.flashSaleText,
                                      fontSize: responsiveFont(10)),
                                ),
                                Text(
                                  ":",
                                  style: TextStyle(
                                      fontSize: responsiveFont(12),
                                      color: home.flashSaleText),
                                ),
                                Text(
                                  time.sec! < 10
                                      ? "0${time.sec}"
                                      : "${time.sec}",
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                      color: home.flashSaleText,
                                      fontSize: responsiveFont(10)),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ],
                    ),
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (context) => ProductMoreScreen(
                                      include: flashSale.flashSales[0].products,
                                      name:
                                          "${AppLocalizations.of(context)!.translate('flash_sale')!.toUpperCase()}",
                                    )));
                      },
                      child: Row(
                        children: [
                          Text(
                            "${AppLocalizations.of(context)!.translate('view_more')}",
                            style: TextStyle(color: home.flashSaleText),
                          ),
                          Icon(
                            Icons.arrow_forward_ios_rounded,
                            color: home.flashSaleText,
                            size: 15.w,
                          )
                        ],
                      ),
                    )
                  ],
                ),
              ),
              Expanded(
                child: Container(
                  padding: EdgeInsets.symmetric(vertical: 10, horizontal: 10),
                  child: loading!
                      ? customLoading(color: primaryColor)
                      : ListView.separated(
                          scrollDirection: Axis.horizontal,
                          itemBuilder: (context, i) {
                            return CardItem(
                              i: i,
                              isFlashSale: true,
                              itemCount: _list.length,
                              product: _list[i],
                            );
                          },
                          separatorBuilder: (BuildContext context, int index) {
                            return SizedBox(
                              width: 10,
                            );
                          },
                          itemCount: _list.length),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
