import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/pages/product/product_detail_screen.dart';
import 'package:nyoba/provider/app_provider.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:nyoba/widgets/product/marquee.dart';
import 'package:percent_indicator/linear_percent_indicator.dart';
import 'package:provider/provider.dart';

class CardItem extends StatefulWidget {
  final ProductModel? product;

  final int? i, itemCount;

  final bool? isFlashSale;

  CardItem({this.product, this.i, this.itemCount, this.isFlashSale = false});

  @override
  State<CardItem> createState() => _CardItemState();
}

class _CardItemState extends State<CardItem> {
  List<Widget> listBadges = [];
  @override
  void initState() {
    // TODO: implement initState
    super.initState();
    loadBadges();
  }

  loadBadges() {
    if (widget.product!.badges != [] &&
        widget.product!.badges != null &&
        widget.isFlashSale == false) {
      for (var i in widget.product!.badges!) {
        listBadges.add(Row(
          children: [
            Image.network(
              i.image!,
              height: 14.h,
              width: 50.w,
            ),
            SizedBox(
              width: 3.w,
            ),
          ],
        ));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ProductModel tempProduct =
        checkDiscountRules(context, widget.product!);
    final locale = Provider.of<AppNotifier>(context, listen: false).appLocal;
    return InkWell(
        onTap: () {
          Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (context) => ProductDetail(
                        productId: widget.product!.id.toString(),
                      )));
        },
        child: widget.isFlashSale == true
            ? Container(
                decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(8),
                    color: Colors.white),
                margin: EdgeInsets.only(
                  left: locale == Locale('ar')
                      ? widget.i == widget.itemCount! - 1
                          ? 15
                          : 0
                      : widget.i == 0
                          ? 15
                          : 0,
                  right: locale == Locale('ar')
                      ? widget.i == 0
                          ? 15
                          : 0
                      : widget.i == widget.itemCount! - 1
                          ? 15
                          : 0,
                ),
                width: 130.w,
                height: double.infinity,
                child: Column(
                  children: [
                    AspectRatio(
                      aspectRatio: 1 / 1,
                      child: Container(
                        width: double.infinity,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: widget.product!.images!.isEmpty
                            ? Icon(
                                Icons.image_not_supported,
                                size: 50,
                              )
                            : ClipRRect(
                                borderRadius: BorderRadius.circular(8),
                                child: CachedNetworkImage(
                                  imageUrl: widget.product!.images![0].src!,
                                  placeholder: (context, url) =>
                                      customLoading(),
                                  errorWidget: (context, url, error) => Icon(
                                    Icons.image_not_supported_rounded,
                                    size: 25,
                                  ),
                                ),
                              ),
                      ),
                    ),
                    SizedBox(
                      height: 3.h,
                    ),
                    Row(
                      children: [...listBadges],
                    ),
                    SizedBox(
                      height: 5.h,
                    ),
                    tempProduct.type == 'simple'
                        ? MarqueeWidget(
                            direction: Axis.horizontal,
                            child: RichText(
                              text: TextSpan(
                                style: TextStyle(color: Colors.black),
                                children: <TextSpan>[
                                  TextSpan(
                                      text: stringToCurrency(
                                          tempProduct.productPrice!, context),
                                      style: TextStyle(
                                          fontWeight: FontWeight.w600,
                                          fontSize: responsiveFont(13),
                                          color: Colors.black)),
                                ],
                              ),
                            ))
                        : tempProduct.variationPrices!.isEmpty
                            ? Container()
                            : tempProduct.variationPricesDisc!.isNotEmpty
                                ? MarqueeWidget(
                                    direction: Axis.horizontal,
                                    child: Row(
                                      children: [
                                        tempProduct.variationPricesDisc!
                                                    .first ==
                                                tempProduct
                                                    .variationPricesDisc!.last
                                            ? RichText(
                                                text: TextSpan(
                                                  style: TextStyle(
                                                      color: Colors.black),
                                                  children: <TextSpan>[
                                                    TextSpan(
                                                        text:
                                                            '${stringToCurrency(tempProduct.variationPricesDisc!.first, context)}',
                                                        style: TextStyle(
                                                            fontWeight:
                                                                FontWeight.w600,
                                                            fontSize:
                                                                responsiveFont(
                                                                    13),
                                                            color:
                                                                Colors.black)),
                                                  ],
                                                ),
                                              )
                                            : RichText(
                                                text: TextSpan(
                                                  style: TextStyle(
                                                      color: Colors.black),
                                                  children: <TextSpan>[
                                                    TextSpan(
                                                        text:
                                                            '${stringToCurrency(tempProduct.variationPricesDisc!.first, context)}',
                                                        style: TextStyle(
                                                            fontWeight:
                                                                FontWeight.w600,
                                                            fontSize:
                                                                responsiveFont(
                                                                    13),
                                                            color:
                                                                Colors.black)),
                                                  ],
                                                ),
                                              )
                                      ],
                                    ))
                                : MarqueeWidget(
                                    direction: Axis.horizontal,
                                    child: Row(
                                      children: [
                                        tempProduct.variationPrices!.first ==
                                                tempProduct
                                                    .variationPrices!.last
                                            ? RichText(
                                                text: TextSpan(
                                                  style: TextStyle(
                                                      color: Colors.black),
                                                  children: <TextSpan>[
                                                    TextSpan(
                                                        text:
                                                            '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                                                        style: TextStyle(
                                                            fontWeight:
                                                                FontWeight.w600,
                                                            fontSize:
                                                                responsiveFont(
                                                                    11),
                                                            color:
                                                                Colors.black)),
                                                  ],
                                                ),
                                              )
                                            : RichText(
                                                text: TextSpan(
                                                  style: TextStyle(
                                                      color: Colors.black),
                                                  children: <TextSpan>[
                                                    TextSpan(
                                                        text:
                                                            '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                                                        style: TextStyle(
                                                            fontWeight:
                                                                FontWeight.w600,
                                                            fontSize:
                                                                responsiveFont(
                                                                    11),
                                                            color:
                                                                Colors.black)),
                                                  ],
                                                ),
                                              )
                                      ],
                                    )),
                  ],
                ),
              )
            : Container(
                decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(8),
                    color: Colors.white),
                margin: EdgeInsets.only(
                  left: locale == Locale('ar')
                      ? widget.i == widget.itemCount! - 1
                          ? 15
                          : 0
                      : widget.i == 0
                          ? 15
                          : 0,
                  right: locale == Locale('ar')
                      ? widget.i == 0
                          ? 15
                          : 0
                      : widget.i == widget.itemCount! - 1
                          ? 15
                          : 0,
                ),
                width: 130.w,
                height: double.infinity,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                        child: Column(
                      children: [
                        AspectRatio(
                          aspectRatio: 1 / 1,
                          child: Container(
                            width: double.infinity,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: widget.product!.images!.isEmpty
                                ? Icon(
                                    Icons.image_not_supported,
                                    size: 50,
                                  )
                                : widget.product!.yith!.video == ""
                                    ? ClipRRect(
                                        borderRadius: BorderRadius.circular(8),
                                        child: CachedNetworkImage(
                                          imageUrl:
                                              widget.product!.images![0].src!,
                                          placeholder: (context, url) =>
                                              customLoading(),
                                          errorWidget: (context, url, error) =>
                                              Icon(
                                            Icons.image_not_supported_rounded,
                                            size: 25,
                                          ),
                                        ),
                                      )
                                    : Stack(
                                        children: [
                                          Center(
                                            child: ClipRRect(
                                              borderRadius:
                                                  BorderRadius.circular(8),
                                              child: CachedNetworkImage(
                                                imageUrl: widget
                                                    .product!.images![0].src!,
                                                placeholder: (context, url) =>
                                                    customLoading(),
                                                errorWidget:
                                                    (context, url, error) =>
                                                        Icon(
                                                  Icons
                                                      .image_not_supported_rounded,
                                                  size: 25,
                                                ),
                                              ),
                                            ),
                                          ),
                                          Center(
                                            child: Container(
                                              width: 50,
                                              height: 50,
                                              decoration: BoxDecoration(
                                                  borderRadius:
                                                      BorderRadius.circular(
                                                          100),
                                                  color: Colors.black54),
                                              alignment: Alignment.center,
                                              child: Icon(
                                                Icons.play_arrow,
                                                size: 35,
                                                color: Colors.white70,
                                              ),
                                            ),
                                          )
                                        ],
                                      ),
                          ),
                        ),
                        SizedBox(
                          height: 3.h,
                        ),
                        listBadges.isNotEmpty
                            ? Row(
                                children: [...listBadges],
                              )
                            : SizedBox(
                                height: 14.h,
                              ),
                        // SizedBox(
                        //   height: 3.h,
                        // ),
                        // product!.yith!.text != ""
                        //     ? Container(
                        //         margin: EdgeInsets.symmetric(horizontal: 5.w),
                        //         padding: EdgeInsets.symmetric(
                        //             horizontal: 7.w, vertical: 0),
                        //         decoration: BoxDecoration(
                        //             color: primaryColor,
                        //             borderRadius: BorderRadius.only(
                        //                 topLeft: Radius.circular(7),
                        //                 bottomLeft: Radius.circular(7),
                        //                 bottomRight: Radius.circular(7))),
                        //         child: Text(
                        //           "${product!.yith!.text}",
                        //           style: TextStyle(
                        //               fontSize: responsiveFont(7),
                        //               fontWeight: FontWeight.w500),
                        //         ))
                        //     : Container(),
                        Container(
                          margin: EdgeInsets.symmetric(horizontal: 5),
                          child: Text(
                            tempProduct.productName!,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(fontSize: responsiveFont(10)),
                            // textScaleFactor: 1.0,
                          ),
                        ),
                      ],
                    )),
                    Container(
                      margin: EdgeInsets.symmetric(horizontal: 5),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            height: 20.h,
                            child: Row(
                              children: [
                                tempProduct.type == 'simple'
                                    ? MarqueeWidget(
                                        direction: Axis.horizontal,
                                        child: RichText(
                                          text: TextSpan(
                                            style:
                                                TextStyle(color: Colors.black),
                                            children: <TextSpan>[
                                              TextSpan(
                                                  text: stringToCurrency(
                                                      tempProduct.productPrice!,
                                                      context),
                                                  style: TextStyle(
                                                      fontWeight:
                                                          FontWeight.w600,
                                                      fontSize:
                                                          responsiveFont(10),
                                                      color: Colors.black)),
                                            ],
                                          ),
                                        ))
                                    : tempProduct.variationPrices!.isEmpty
                                        ? Container()
                                        : tempProduct
                                                .variationPricesDisc!.isNotEmpty
                                            ? MarqueeWidget(
                                                direction: Axis.horizontal,
                                                child: RichText(
                                                  text: TextSpan(
                                                    style: TextStyle(
                                                        color: Colors.black),
                                                    children: <TextSpan>[
                                                      TextSpan(
                                                          text:
                                                              '${stringToCurrency(tempProduct.variationPricesDisc!.first, context)}',
                                                          style: TextStyle(
                                                              fontWeight:
                                                                  FontWeight
                                                                      .w600,
                                                              fontSize:
                                                                  responsiveFont(
                                                                      10),
                                                              color: Colors
                                                                  .black)),
                                                    ],
                                                  ),
                                                ))
                                            : MarqueeWidget(
                                                direction: Axis.horizontal,
                                                child: RichText(
                                                  text: TextSpan(
                                                    style: TextStyle(
                                                        color: Colors.black),
                                                    children: <TextSpan>[
                                                      TextSpan(
                                                          text:
                                                              '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                                                          style: TextStyle(
                                                              fontWeight:
                                                                  FontWeight
                                                                      .w600,
                                                              fontSize:
                                                                  responsiveFont(
                                                                      10),
                                                              color: Colors
                                                                  .black)),
                                                    ],
                                                  ),
                                                )),
                                SizedBox(
                                  width: 5.w,
                                ),
                                tempProduct.type == 'simple'
                                    ? Visibility(
                                        visible: tempProduct.type == 'simple' &&
                                            widget.product!.productRegPrice
                                                    .toString() !=
                                                tempProduct.productPrice
                                                    .toString(),
                                        child: Expanded(
                                          child: RichText(
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            text: TextSpan(
                                              style: TextStyle(
                                                  color: Colors.black),
                                              children: <TextSpan>[
                                                TextSpan(
                                                    text: stringToCurrency(
                                                        double.parse(widget
                                                            .product!
                                                            .productRegPrice),
                                                        context),
                                                    style: TextStyle(
                                                        decoration:
                                                            TextDecoration
                                                                .lineThrough,
                                                        fontSize:
                                                            responsiveFont(7.5),
                                                        color: HexColor(
                                                            "C4C4C4"))),
                                              ],
                                            ),
                                          ),
                                        ))
                                    : tempProduct.variationPrices!.isNotEmpty
                                        ? Visibility(
                                            visible: tempProduct.type !=
                                                    'simple' &&
                                                tempProduct.discProduct != 0 &&
                                                tempProduct.variationPrices!
                                                        .first ==
                                                    tempProduct
                                                        .variationPrices!.last,
                                            child: Expanded(
                                              child: RichText(
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                                text: TextSpan(
                                                  style: TextStyle(
                                                      color: Colors.black),
                                                  children: <TextSpan>[
                                                    TextSpan(
                                                        text:
                                                            '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                                                        style: TextStyle(
                                                            decoration:
                                                                TextDecoration
                                                                    .lineThrough,
                                                            fontSize:
                                                                responsiveFont(
                                                                    7.5),
                                                            color: HexColor(
                                                                "C4C4C4"))),
                                                  ],
                                                ),
                                              ),
                                            ))
                                        : Container(),
                                tempProduct.type != 'simple'
                                    ? tempProduct.variationPrices!.isNotEmpty
                                        ? Visibility(
                                            visible: tempProduct.type !=
                                                    'simple' &&
                                                tempProduct.discProduct != 0 &&
                                                tempProduct.variationPrices!
                                                        .first !=
                                                    tempProduct
                                                        .variationPrices!.last,
                                            child: Expanded(
                                                child: RichText(
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                              text: TextSpan(
                                                style: TextStyle(
                                                    color: Colors.black),
                                                children: <TextSpan>[
                                                  TextSpan(
                                                      text:
                                                          '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                                                      style: TextStyle(
                                                          decoration:
                                                              TextDecoration
                                                                  .lineThrough,
                                                          fontSize:
                                                              responsiveFont(9),
                                                          color: HexColor(
                                                              "C4C4C4"))),
                                                ],
                                              ),
                                            )))
                                        : Container()
                                    : Container(),
                              ],
                            ),
                          ),
                          Container(
                            height: 17.h,
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Container(
                                  child: Row(
                                    mainAxisAlignment:
                                        MainAxisAlignment.spaceBetween,
                                    children: [
                                      Row(
                                        children: [
                                          Container(
                                            child: Text(
                                              "${widget.product!.totalSold!} ${AppLocalizations.of(context)!.translate('sold')}",
                                              style: TextStyle(
                                                  fontSize: responsiveFont(7)),
                                            ),
                                          ),
                                          SizedBox(
                                            width: 5.w,
                                          ),
                                          Row(
                                            children: [
                                              Icon(
                                                Icons.star,
                                                color: Colors.redAccent,
                                                size: 12,
                                              ),
                                              SizedBox(
                                                width: 2.w,
                                              ),
                                              Container(
                                                child: Text(
                                                  "${double.parse(widget.product!.avgRating!).toStringAsFixed(1)}",
                                                  style: TextStyle(
                                                      fontSize:
                                                          responsiveFont(7)),
                                                ),
                                              ),
                                            ],
                                          )
                                        ],
                                      ),
                                      // product!.yith!.text != ""
                                      //     ? Container(
                                      //         padding: EdgeInsets.symmetric(
                                      //             horizontal: 7.w, vertical: 0),
                                      //         decoration: BoxDecoration(
                                      //             color: primaryColor,
                                      //             borderRadius: BorderRadius.only(
                                      //                 topLeft: Radius.circular(7),
                                      //                 bottomLeft: Radius.circular(7),
                                      //                 bottomRight: Radius.circular(7))),
                                      //         child: Text(
                                      //           "${product!.yith!.text}",
                                      //           style: TextStyle(
                                      //               fontSize: responsiveFont(7),
                                      //               fontStyle: FontStyle.italic,
                                      //               fontWeight: FontWeight.w500),
                                      //         ))
                                      //     : Container(),
                                    ],
                                  ),
                                ),
                                Visibility(
                                  visible: widget.product!.discProduct != 0 &&
                                      widget.product!.discProduct != 0.0,
                                  child: Row(
                                    children: [
                                      Container(
                                        decoration: BoxDecoration(
                                          borderRadius:
                                              BorderRadius.circular(2),
                                          color: secondaryColor,
                                        ),
                                        padding:
                                            EdgeInsets.symmetric(horizontal: 5),
                                        child: Text(
                                          "${widget.product!.discProduct!.round()}%",
                                          style: TextStyle(
                                              color: Colors.black,
                                              fontSize: responsiveFont(9)),
                                        ),
                                      ),
                                      Container(
                                        width: 5,
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                          // widget.product!.shippingPrice != null
                          //     ? Container(
                          //         child: Text(
                          //           "Shipping : ${shippingCurrency(widget.product!.shippingPrice!, context)}",
                          //           style:
                          //               TextStyle(fontSize: responsiveFont(10)),
                          //         ),
                          //       )
                          //     : Container(),
                          // widget.product!.tags!.length == 0
                          //           ? Container()
                          //           : Container(
                          //               child: Text(
                          //                 widget.product!.tags!.first,
                          //                 style: TextStyle(
                          //                     fontSize: responsiveFont(10)),
                          //               ),
                          //             ),
                        ],
                      ),
                    ),
                    Visibility(
                      visible: widget.isFlashSale!,
                      child: Container(
                        margin:
                            EdgeInsets.symmetric(horizontal: 5, vertical: 5),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            new LinearPercentIndicator(
                                padding: EdgeInsets.zero,
                                lineHeight: 5.0,
                                percent: tempProduct.productStock != null &&
                                        tempProduct.productStock != 0
                                    ? 1
                                    : 0,
                                backgroundColor: Colors.grey,
                                progressColor: HexColor("00963C")),
                            Text(
                              tempProduct.productStock != null &&
                                      tempProduct.productStock != 0
                                  ? "Stock Available"
                                  : "Stock Empty",
                              style: TextStyle(fontSize: responsiveFont(6)),
                            )
                          ],
                        ),
                      ),
                    ),
                    SizedBox(
                      height: 10.h,
                    ),
                  ],
                ),
              ));
  }
}
