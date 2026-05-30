import 'dart:convert';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/pages/category/brand_product_screen.dart';
import 'package:nyoba/pages/product/product_detail_screen.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:nyoba/widgets/product/marquee.dart';

import '../../../app_localizations.dart';

class GridItemCategory extends StatefulWidget {
  final int? i;
  final int? itemCount;
  final ProductModel? product;
  final String? categoryName;
  final int? categoryId;
  final int? chosenCountSub;

  GridItemCategory(
      {this.i,
      this.itemCount,
      this.product,
      this.categoryName,
      this.categoryId,
      this.chosenCountSub});

  @override
  State<GridItemCategory> createState() => _GridItemCategoryState();
}

class _GridItemCategoryState extends State<GridItemCategory> {
  List<Widget> listBadges = [];

  @override
  void initState() {
    // TODO: implement initState
    super.initState();
    loadBadges();
  }

  loadBadges() {
    printLog(
        "${jsonEncode(widget.product!.badges)} - ${widget.product!.productName}",
        name: "badges");
    if (widget.product!.badges != [] && widget.product!.badges != null) {
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
    if (widget.i == 5) {
      return buildViewMore(context);
    } else {
      final ProductModel tempProduct =
          checkDiscountRules(context, widget.product!);

      return Container(
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(8)),
        child: GestureDetector(
          onTap: () {
            Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (context) => ProductDetail(
                          productId: tempProduct.id.toString(),
                        )));
          },
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  tempProduct.images!.isEmpty
                      ? Icon(
                          Icons.broken_image_outlined,
                          size: 50,
                        )
                      : ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: CachedNetworkImage(
                            imageUrl: tempProduct.images![0].src!,
                            placeholder: (context, url) => customLoading(),
                            errorWidget: (context, url, error) => Icon(
                              Icons.image_not_supported_rounded,
                              size: 25,
                            ),
                          ),
                        ),
                  listBadges.isNotEmpty
                      ? Row(
                          children: [...listBadges],
                        )
                      : SizedBox(
                          height: 14.h,
                        ),
                  Container(
                    margin: EdgeInsets.symmetric(vertical: 3, horizontal: 5),
                    child: Text(
                      tempProduct.productName!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: responsiveFont(10)),
                    ),
                  ),
                  Container(
                    height: 0,
                  ),
                ],
              ),
              Container(
                alignment: Alignment.bottomCenter,
                margin: EdgeInsets.symmetric(vertical: 1, horizontal: 5),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Visibility(
                      visible: widget.product!.discProduct != 0 &&
                          widget.product!.discProduct != 0.0,
                      child: Row(
                        children: [
                          Container(
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(2),
                              color: secondaryColor,
                            ),
                            padding: EdgeInsets.symmetric(horizontal: 5),
                            child: Text(
                              "${widget.product!.discProduct!.round()}%",
                              style: TextStyle(
                                  color: Colors.black,
                                  fontSize: responsiveFont(9)),
                            ),
                          ),
                          SizedBox(
                            width: 3.w,
                          ),
                          tempProduct.type == 'simple'
                              ? Visibility(
                                  visible: tempProduct.type == 'simple',
                                  child: MarqueeWidget(
                                    direction: Axis.horizontal,
                                    child: RichText(
                                      text: TextSpan(
                                        style: TextStyle(color: Colors.black),
                                        children: <TextSpan>[
                                          TextSpan(
                                              text: stringToCurrency(
                                                  double.parse(widget.product!
                                                      .productRegPrice),
                                                  context),
                                              style: TextStyle(
                                                  decoration: TextDecoration
                                                      .lineThrough,
                                                  fontSize: responsiveFont(9),
                                                  color: HexColor("C4C4C4"))),
                                        ],
                                      ),
                                    ),
                                  ))
                              : tempProduct.variationPrices!.isNotEmpty
                                  ? Visibility(
                                      visible: tempProduct.type != 'simple' &&
                                          tempProduct.discProduct != 0 &&
                                          tempProduct.variationPrices!.first ==
                                              tempProduct.variationPrices!.last,
                                      child: MarqueeWidget(
                                        direction: Axis.horizontal,
                                        child: RichText(
                                          text: TextSpan(
                                            style:
                                                TextStyle(color: Colors.black),
                                            children: <TextSpan>[
                                              TextSpan(
                                                  text:
                                                      '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                                                  style: TextStyle(
                                                      decoration: TextDecoration
                                                          .lineThrough,
                                                      fontSize:
                                                          responsiveFont(9),
                                                      color:
                                                          HexColor("C4C4C4"))),
                                            ],
                                          ),
                                        ),
                                      ))
                                  : Container(),
                        ],
                      ),
                    ),
                    Row(
                      children: [
                        Column(
                          children: [
                            tempProduct.type != 'simple'
                                ? tempProduct.variationPrices!.isNotEmpty
                                    ? Visibility(
                                        visible: tempProduct.type != 'simple' &&
                                            tempProduct.discProduct != 0 &&
                                            tempProduct
                                                    .variationPrices!.first !=
                                                tempProduct
                                                    .variationPrices!.last,
                                        child: MarqueeWidget(
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
                                                        decoration:
                                                            TextDecoration
                                                                .lineThrough,
                                                        fontSize:
                                                            responsiveFont(9),
                                                        color: HexColor(
                                                            "C4C4C4"))),
                                              ],
                                            ),
                                          ),
                                        ))
                                    : Container()
                                : Container(),
                            tempProduct.type == 'simple'
                                ? MarqueeWidget(
                                    direction: Axis.horizontal,
                                    child: RichText(
                                      text: TextSpan(
                                        style: TextStyle(color: Colors.black),
                                        children: <TextSpan>[
                                          TextSpan(
                                              text: stringToCurrency(
                                                  tempProduct.productPrice!,
                                                  context),
                                              style: TextStyle(
                                                  fontWeight: FontWeight.w600,
                                                  fontSize: responsiveFont(11),
                                                  color: Colors.black)),
                                        ],
                                      ),
                                    ),
                                  )
                                : tempProduct.variationPrices!.isEmpty
                                    ? Container()
                                    : tempProduct
                                            .variationPricesDisc!.isNotEmpty
                                        ? MarqueeWidget(
                                            direction: Axis.horizontal,
                                            child: MarqueeWidget(
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
                                                                FontWeight.w600,
                                                            fontSize:
                                                                responsiveFont(
                                                                    11),
                                                            color:
                                                                Colors.black)),
                                                  ],
                                                ),
                                              ),
                                            ),
                                          )
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
                                                              FontWeight.w600,
                                                          fontSize:
                                                              responsiveFont(
                                                                  11),
                                                          color: Colors.black)),
                                                ],
                                              ),
                                            ),
                                          ),
                          ],
                        ),
                        SizedBox(
                          width: 5.w,
                        ),
                        // tempProduct.type == 'simple'
                        //     ? Visibility(
                        //         visible: tempProduct.type == 'simple',
                        //         child: MarqueeWidget(
                        //           direction: Axis.horizontal,
                        //           child: RichText(
                        //             text: TextSpan(
                        //               style: TextStyle(color: Colors.black),
                        //               children: <TextSpan>[
                        //                 TextSpan(
                        //                     text: stringToCurrency(
                        //                         double.parse(widget
                        //                             .product!.productRegPrice),
                        //                         context),
                        //                     style: TextStyle(
                        //                         decoration:
                        //                             TextDecoration.lineThrough,
                        //                         fontSize: responsiveFont(9),
                        //                         color: HexColor("C4C4C4"))),
                        //               ],
                        //             ),
                        //           ),
                        //         ))
                        //     : tempProduct.variationPrices!.isNotEmpty
                        //         ? Visibility(
                        //             visible: tempProduct.type != 'simple' &&
                        //                 tempProduct.discProduct != 0 &&
                        //                 tempProduct.variationPrices!.first ==
                        //                     tempProduct.variationPrices!.last,
                        //             child: MarqueeWidget(
                        //               direction: Axis.horizontal,
                        //               child: RichText(
                        //                 text: TextSpan(
                        //                   style: TextStyle(color: Colors.black),
                        //                   children: <TextSpan>[
                        //                     TextSpan(
                        //                         text:
                        //                             '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                        //                         style: TextStyle(
                        //                             decoration: TextDecoration
                        //                                 .lineThrough,
                        //                             fontSize: responsiveFont(9),
                        //                             color: HexColor("C4C4C4"))),
                        //                   ],
                        //                 ),
                        //               ),
                        //             ))
                        //         : Container()
                      ],
                    ),
                    // Visibility(
                    //   visible: widget.product!.discProduct != 0 &&
                    //       widget.product!.discProduct != 0.0,
                    //   child: Container(
                    //     decoration: BoxDecoration(
                    //       borderRadius: BorderRadius.circular(2),
                    //       color: secondaryColor,
                    //     ),
                    //     padding: EdgeInsets.symmetric(horizontal: 5),
                    //     child: Text(
                    //       "${widget.product!.discProduct!.round()}%",
                    //       style: TextStyle(
                    //           color: Colors.black, fontSize: responsiveFont(9)),
                    //     ),
                    //   ),
                    // ),
                    // SizedBox(
                    //   width: 1.w,
                    // ),
                    Container(
                      child: Row(
                        children: [
                          Container(
                            child: Text(
                              "${widget.product!.totalSold!} ${AppLocalizations.of(context)!.translate('sold')}",
                              style: TextStyle(fontSize: responsiveFont(10)),
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
                                  style:
                                      TextStyle(fontSize: responsiveFont(10)),
                                ),
                              ),
                            ],
                          )
                        ],
                      ),
                    ),
                    // product!.tags!.length == 0
                    //     ? Container()
                    //     : Container(
                    //         child: Text(
                    //           product!.tags!.first,
                    //           style: TextStyle(fontSize: responsiveFont(10)),
                    //         ),
                    //       ),
                  ],
                ),
              ),
              Container(
                height: 5.h,
              ),
            ],
          ),
        ),
      );
    }
  }

  Widget buildViewMore(context) {
    return Container(
      decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(8)),
      child: GestureDetector(
        onTap: () {
          Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (context) => BrandProducts(
                        withFilter: true,
                        categoryId: widget.categoryId.toString(),
                        brandName: widget.categoryName,
                        isNeedSub: true,
                      )));
        },
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              margin: EdgeInsets.only(bottom: 15),
              child: Icon(
                Icons.add,
                color: secondaryColor,
                size: 28,
              ),
            ),
            Container(
              child: Text(
                AppLocalizations.of(context)!.translate('view_more')!,
                style: TextStyle(
                    color: secondaryColor,
                    fontSize: responsiveFont(10),
                    fontWeight: FontWeight.w500),
              ),
            ),
            Container(
              margin: EdgeInsets.only(top: 5),
              child: Text(
                AppLocalizations.of(context)!.translate('sub_view_more')!,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: responsiveFont(8),
                  fontWeight: FontWeight.w400,
                ),
              ),
            )
          ],
        ),
      ),
    );
  }
}
