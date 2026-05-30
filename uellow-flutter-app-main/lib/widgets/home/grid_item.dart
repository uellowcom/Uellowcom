import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:nyoba/widgets/product/marquee.dart';

import '../../pages/product/product_detail_screen.dart';

class GridItem extends StatefulWidget {
  final int? i;
  final int? itemCount;
  final ProductModel? product;

  GridItem({this.i, this.itemCount, this.product});

  @override
  State<GridItem> createState() => _GridItemState();
}

class _GridItemState extends State<GridItem> {
  List<Widget> listBadges = [];

  @override
  void initState() {
    // TODO: implement initState
    super.initState();
    loadBadges();
  }

  loadBadges() {
    if (widget.product!.badges != [] && widget.product!.badges != null) {
      for (var i in widget.product!.badges!) {
        listBadges.add(Row(
          children: [
            Image.network(
              i.image!,
              width: 50.w,
            ),
            SizedBox(
              width: 3.w,
            )
          ],
        ));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
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
                        productId: widget.product!.id.toString(),
                      )));
        },
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                ),
                child: widget.product!.yith!.video == ""
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: CachedNetworkImage(
                          imageUrl: widget.product!.images![0].src!,
                          placeholder: (context, url) => customLoading(),
                          errorWidget: (context, url, error) => Icon(
                            Icons.image_not_supported_rounded,
                            size: 25,
                          ),
                        ),
                      )
                    : Stack(
                        alignment: Alignment.center,
                        children: [
                          Center(
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: CachedNetworkImage(
                                imageUrl: widget.product!.images![0].src!,
                                placeholder: (context, url) => customLoading(),
                                errorWidget: (context, url, error) => Icon(
                                  Icons.image_not_supported_rounded,
                                  size: 25,
                                ),
                              ),
                            ),
                          ),
                          Container(
                            width: 50,
                            height: 50,
                            decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(100),
                                color: Colors.black54),
                            alignment: Alignment.center,
                            child: Icon(
                              Icons.play_arrow,
                              size: 35,
                              color: Colors.white70,
                            ),
                          )
                        ],
                      )),
            SizedBox(
              height: 3.h,
            ),
            Row(
              children: [...listBadges],
            ),
            // widget.product!.yith!.text != ""
            //     ? Container(
            //         margin: EdgeInsets.symmetric(horizontal: 5.w),
            //         padding: EdgeInsets.symmetric(horizontal: 7.w, vertical: 0),
            //         decoration: BoxDecoration(
            //             color: primaryColor,
            //             borderRadius: BorderRadius.only(
            //                 topLeft: Radius.circular(7),
            //                 bottomLeft: Radius.circular(7),
            //                 bottomRight: Radius.circular(7))),
            //         child: Text(
            //           "${widget.product!.yith!.text}",
            //           style: TextStyle(
            //               fontSize: responsiveFont(8),
            //               fontWeight: FontWeight.w500),
            //         ))
            //     : Container(),
            Container(
              margin: EdgeInsets.symmetric(vertical: 3, horizontal: 5),
              child: Text(
                widget.product!.productName!,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: responsiveFont(10)),
              ),
            ),
            Container(
              alignment: Alignment.bottomCenter,
              margin: EdgeInsets.symmetric(vertical: 3, horizontal: 5),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  tempProduct.type != 'simple'
                      ? tempProduct.variationPrices!.isNotEmpty
                          ? Visibility(
                              visible: tempProduct.type != 'simple' &&
                                  tempProduct.discProduct != 0 &&
                                  tempProduct.variationPrices!.first !=
                                      tempProduct.variationPrices!.last,
                              child: Column(
                                children: [
                                  SizedBox(
                                    height: 5,
                                  ),
                                  MarqueeWidget(
                                    direction: Axis.horizontal,
                                    child: RichText(
                                      text: TextSpan(
                                        style: TextStyle(color: Colors.black),
                                        children: <TextSpan>[
                                          TextSpan(
                                              text:
                                                  '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                                              style: TextStyle(
                                                  decoration: TextDecoration
                                                      .lineThrough,
                                                  fontSize: responsiveFont(9),
                                                  color: HexColor("C4C4C4"))),
                                        ],
                                      ),
                                    ),
                                  )
                                ],
                              ))
                          : Container()
                      : Container(),
                  Row(
                    children: [
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
                                            fontSize: responsiveFont(11),
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
                                                                  FontWeight
                                                                      .w600,
                                                              fontSize:
                                                                  responsiveFont(
                                                                      11),
                                                              color: Colors
                                                                  .black)),
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
                                                                  FontWeight
                                                                      .w600,
                                                              fontSize:
                                                                  responsiveFont(
                                                                      11),
                                                              color: Colors
                                                                  .black)),
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
                                                                  FontWeight
                                                                      .w600,
                                                              fontSize:
                                                                  responsiveFont(
                                                                      11),
                                                              color: Colors
                                                                  .black)),
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
                                                                  FontWeight
                                                                      .w600,
                                                              fontSize:
                                                                  responsiveFont(
                                                                      11),
                                                              color: Colors
                                                                  .black)),
                                                    ],
                                                  ),
                                                )
                                        ],
                                      )),
                      SizedBox(
                        width: 5.w,
                      ),
                      tempProduct.type == 'simple'
                          ? Visibility(
                              visible: tempProduct.type == 'simple',
                              child: Expanded(
                                  child: RichText(
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                text: TextSpan(
                                  style: TextStyle(color: Colors.black),
                                  children: <TextSpan>[
                                    TextSpan(
                                        text: stringToCurrency(
                                            double.parse(widget
                                                .product!.productRegPrice),
                                            context),
                                        style: TextStyle(
                                            decoration:
                                                TextDecoration.lineThrough,
                                            fontSize: responsiveFont(9),
                                            color: HexColor("C4C4C4"))),
                                  ],
                                ),
                              )),
                            )
                          : tempProduct.variationPrices!.isNotEmpty
                              ? Visibility(
                                  visible: tempProduct.type != 'simple' &&
                                      tempProduct.discProduct != 0 &&
                                      tempProduct.variationPrices!.first ==
                                          tempProduct.variationPrices!.last,
                                  child: Expanded(
                                      child: RichText(
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    text: TextSpan(
                                      style: TextStyle(color: Colors.black),
                                      children: <TextSpan>[
                                        TextSpan(
                                            text:
                                                '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                                            style: TextStyle(
                                                decoration:
                                                    TextDecoration.lineThrough,
                                                fontSize: responsiveFont(9),
                                                color: HexColor("C4C4C4"))),
                                      ],
                                    ),
                                  )))
                              : Container(),
                    ],
                  ),
                  Container(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
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
                        Row(
                          children: [
                            Visibility(
                              visible: widget.product!.discProduct != 0 &&
                                  widget.product!.discProduct != 0.0,
                              child: Container(
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
                            ),
                            SizedBox(
                              width: 5.w,
                            )
                          ],
                        ),
                      ],
                    ),
                  ),
                  widget.product!.shippingPrice != null
                      ? Container(
                          child: Text(
                            "Shipping : ${stringToCurrency(widget.product!.shippingPrice!, context)}",
                            style: TextStyle(fontSize: responsiveFont(10)),
                          ),
                        )
                      : Container(),
                  // widget.product!.tags!.length == 0
                  //     ? Container()
                  //     : Container(
                  //         child: Text(
                  //           convertHtmlUnescape(widget.product!.tags!.first),
                  //           style: TextStyle(fontSize: responsiveFont(10)),
                  //         ),
                  //       ),
                ],
              ),
            ),
            Container(
              height: 5,
            ),
          ],
        ),
      ),
    );
  }
}
