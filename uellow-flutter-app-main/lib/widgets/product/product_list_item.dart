import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/pages/product/product_detail_screen.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:hexcolor/hexcolor.dart';

class ProductListItem extends StatelessWidget {
  final ProductModel? product;
  final int? i, itemCount;

  ProductListItem({this.product, this.i, this.itemCount});

  @override
  Widget build(BuildContext context) {
    final ProductModel tempProduct = checkDiscountRules(context, product!);

    return GestureDetector(
      onTap: () {
        Navigator.push(
            context,
            MaterialPageRoute(
                builder: (context) => ProductDetail(
                      productId: product!.id.toString(),
                    )));
      },
      child: Card(
          elevation: 2,
          child: Container(
            padding: EdgeInsets.all(10),
            child: Column(
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(5),
                      ),
                      width: 65.h,
                      height: 65.h,
                      child: product!.images!.isEmpty
                          ? Icon(
                              Icons.image_not_supported,
                              size: 50,
                            )
                          : CachedNetworkImage(
                              imageUrl: product!.images![0].src!,
                              placeholder: (context, url) => customLoading(),
                              errorWidget: (context, url, error) =>
                                  Icon(Icons.error),
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
                                product!.productName!,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                    fontSize: responsiveFont(10),
                                    fontWeight: FontWeight.w500),
                              ),
                            ],
                          ),
                          SizedBox(
                            height: 10.h,
                          ),
                          Container(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Visibility(
                                  visible: product!.discProduct != 0 &&
                                      product!.discProduct != 0.0,
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
                                          "${product!.discProduct!.round()}%",
                                          style: TextStyle(
                                              color: Colors.black,
                                              fontSize: responsiveFont(9)),
                                        ),
                                      ),
                                      Container(
                                        width: 5,
                                      ),
                                      tempProduct.type == 'simple'
                                          ? Visibility(
                                              visible:
                                                  tempProduct.type == 'simple',
                                              child: RichText(
                                                text: TextSpan(
                                                  style: TextStyle(
                                                      color: Colors.black),
                                                  children: <TextSpan>[
                                                    TextSpan(
                                                        text: stringToCurrency(
                                                            double.parse(product!
                                                                .productRegPrice),
                                                            context),
                                                        style: TextStyle(
                                                            decoration:
                                                                TextDecoration
                                                                    .lineThrough,
                                                            fontSize:
                                                                responsiveFont(
                                                                    9),
                                                            color: HexColor(
                                                                "C4C4C4"))),
                                                  ],
                                                ),
                                              ),
                                            )
                                          : tempProduct
                                                  .variationPrices!.isNotEmpty
                                              ? Visibility(
                                                  visible: tempProduct.type !=
                                                          'simple' &&
                                                      tempProduct.discProduct !=
                                                          0 &&
                                                      tempProduct
                                                              .variationPrices!
                                                              .first ==
                                                          tempProduct
                                                              .variationPrices!
                                                              .last,
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
                                                                    responsiveFont(
                                                                        9),
                                                                color: HexColor(
                                                                    "C4C4C4"))),
                                                      ],
                                                    ),
                                                  ))
                                              : Container()
                                    ],
                                  ),
                                ),
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
                                            child: Column(
                                              children: [
                                                SizedBox(
                                                  height: 5,
                                                ),
                                                RichText(
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
                                                                      9),
                                                              color: HexColor(
                                                                  "C4C4C4"))),
                                                    ],
                                                  ),
                                                ),
                                              ],
                                            ))
                                        : Container()
                                    : Container(),
                                tempProduct.type == 'simple'
                                    ? RichText(
                                        text: TextSpan(
                                          style: TextStyle(color: Colors.black),
                                          children: <TextSpan>[
                                            TextSpan(
                                                text: stringToCurrency(
                                                    tempProduct.productPrice!,
                                                    context),
                                                style: TextStyle(
                                                    fontWeight: FontWeight.w600,
                                                    fontSize:
                                                        responsiveFont(11),
                                                    color: Colors.red[700])),
                                          ],
                                        ),
                                      )
                                    : tempProduct.variationPrices!.isEmpty
                                        ? Container()
                                        : tempProduct
                                                .variationPricesDisc!.isNotEmpty
                                            ? Row(
                                                children: [
                                                  tempProduct.variationPricesDisc!
                                                              .first ==
                                                          tempProduct
                                                              .variationPricesDisc!
                                                              .last
                                                      ? RichText(
                                                          text: TextSpan(
                                                            style: TextStyle(
                                                                color: Colors
                                                                    .black),
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
                                                                              .red[
                                                                          700])),
                                                            ],
                                                          ),
                                                        )
                                                      : RichText(
                                                          text: TextSpan(
                                                            style: TextStyle(
                                                                color: Colors
                                                                    .black),
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
                                                                              .red[
                                                                          700])),
                                                            ],
                                                          ),
                                                        )
                                                ],
                                              )
                                            : Row(
                                                children: [
                                                  tempProduct.variationPrices!
                                                              .first ==
                                                          tempProduct
                                                              .variationPrices!
                                                              .last
                                                      ? RichText(
                                                          text: TextSpan(
                                                            style: TextStyle(
                                                                color: Colors
                                                                    .black),
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
                                                                              .red[
                                                                          700])),
                                                            ],
                                                          ),
                                                        )
                                                      : Row(
                                                          children: [
                                                            RichText(
                                                              text: TextSpan(
                                                                style: TextStyle(
                                                                    color: Colors
                                                                        .black),
                                                                children: <TextSpan>[
                                                                  TextSpan(
                                                                      text:
                                                                          '${stringToCurrency(tempProduct.variationPrices!.first, context)}',
                                                                      style: TextStyle(
                                                                          fontWeight: FontWeight
                                                                              .w600,
                                                                          fontSize: responsiveFont(
                                                                              11),
                                                                          color:
                                                                              Colors.red[700])),
                                                                ],
                                                              ),
                                                            ),
                                                          ],
                                                        )
                                                ],
                                              ),
                                Container(
                                  child: Row(
                                    children: [
                                      Container(
                                        child: Text(
                                          "${product!.totalSold!} ${AppLocalizations.of(context)!.translate('sold')}",
                                          style: TextStyle(
                                              fontSize: responsiveFont(10)),
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
                                              "${double.parse(product!.avgRating!).toStringAsFixed(1)}",
                                              style: TextStyle(
                                                  fontSize: responsiveFont(10)),
                                            ),
                                          ),
                                        ],
                                      )
                                    ],
                                  ),
                                ),
                                product!.shippingPrice != null
                                    ? Container(
                                        child: Text(
                                          "Shipping : ${shippingCurrency(product!.shippingPrice!, context)}",
                                          style: TextStyle(
                                              fontSize: responsiveFont(10)),
                                        ),
                                      )
                                    : Container(),
                                product!.tags!.length == 0
                                    ? Container()
                                    : Container(
                                        child: Text(
                                          product!.tags!.first,
                                          style: TextStyle(
                                              fontSize: responsiveFont(10)),
                                        ),
                                      ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    )
                  ],
                )
              ],
            ),
          )),
    );
  }
}
