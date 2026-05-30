import 'dart:convert';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/models/shipping_method_model.dart';
import 'package:nyoba/pages/order/cart_screen.dart';
import 'package:nyoba/pages/order/order_success_screen.dart';
import 'package:nyoba/pages/product/page_view_review.dart';
import 'package:nyoba/pages/product/shipping_method_screen.dart';
import 'package:nyoba/provider/order_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/utils/global_variable.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

class ProductDetailModal extends StatefulWidget {
  final ProductModel? productModel;
  final String? type;
  final Future<dynamic> Function()? loadCount;
  const ProductDetailModal(
      {Key? key, this.productModel, this.type, this.loadCount})
      : super(key: key);

  @override
  State<ProductDetailModal> createState() => _ProductDetailModalState();
}

class _ProductDetailModalState extends State<ProductDetailModal> {
  List<ProductVariation> variation = [];

  bool load = false;
  bool isAvailable = false;
  bool isOutStock = false;

  num? variationPrice = 0;
  num? variationSalePrice = 0;
  String? variationName = '';
  Map<String, dynamic>? variationResult;
  int? variationStock = 0;

  int selectedVariantIndex = 0;

  int cartQuantityAddToCart = 0;
  ValueNotifier<int>? selectedIndex = ValueNotifier(0);
  String lang = "en";
  @override
  void initState() {
    super.initState();
    widget.productModel!.cartQuantity = 1;
    printLog(jsonEncode(widget.productModel), name: "DATA PRODUCT");
    if (Session.data.containsKey('language_code') == true) {
      lang = Session.data.getString('language_code')!;
    } else {
      lang = 'en';
    }
    initVariation();
  }

  /*add to cart*/
  void addCart(ProductModel product) async {
    print('Add Cart');
    if (variationPrice != 0) {
      print("Variation Price : $variationPrice");

      product.productPrice = variationPrice;
    }
    if (variationSalePrice != 0) {
      product.productPriceDisc = variationSalePrice;
    }
    if (product.variantId != null) {
      product.selectedVariation = variation;
      product.variationName = variationName;
    }

    if (product.type == 'simple') {
      print("Price Simple : ${product.productPrice}");
      product.cartPrice = product.productPrice;
    } else {
      product.cartPrice = product.productPriceDisc != null
          ? product.productPriceDisc
          : product.productPrice;
    }
    product.a2wShippingMethod = "";
    product.a2wShippingCheckoutData = [];
    if (Provider.of<ProductProvider>(context, listen: false)
        .shippingMethods
        .isNotEmpty) {
      product.a2wShippingMethod =
          Provider.of<ProductProvider>(context, listen: false)
              .shippingMethods[context.read<ProductProvider>().selectedShipping]
              .serviceName;

      var tempa2wshipping = {
        "method": Provider.of<ProductProvider>(context, listen: false)
            .shippingMethods[context.read<ProductProvider>().selectedShipping]
            .serviceName,
        "cost": Provider.of<ProductProvider>(context, listen: false)
            .shippingMethods[context.read<ProductProvider>().selectedShipping]
            .price
      };

      widget.productModel?.a2wShippingCheckoutData = [];
      if (Provider.of<ProductProvider>(context, listen: false)
          .shippingMethods
          .isNotEmpty) {
        widget.productModel?.a2wShippingCheckoutData = [tempa2wshipping];
      }

      widget.productModel?.a2wShippingMethod = "";
      if (Provider.of<ProductProvider>(context, listen: false)
          .shippingMethods
          .isNotEmpty) {
        widget.productModel?.a2wShippingMethod = Provider.of<ProductProvider>(
                context,
                listen: false)
            .shippingMethods[context.read<ProductProvider>().selectedShipping]
            .serviceName;
      }
    }

    printLog(json.encode(product), name: "DATA PRODUCT ADD TO CART");

    ProductModel productCart = product;
    cartQuantityAddToCart = product.cartQuantity!;

    /*check sharedprefs for cart*/
    if (!Session.data.containsKey('cart')) {
      List<ProductModel> listCart = [];
      productCart.priceTotal =
          (productCart.cartQuantity! * productCart.cartPrice!);

      listCart.add(productCart);

      await Session.data.setString('cart', json.encode(listCart));
    } else {
      List products = await json.decode(Session.data.getString('cart')!);

      List<ProductModel> listCart = products
          .map((product) => new ProductModel.fromJson(product))
          .toList();

      int index = products.indexWhere((prod) =>
          prod["id"] == productCart.id &&
          prod["variant_id"] == productCart.variantId &&
          prod["variation_name"] == productCart.variationName);

      if (index != -1) {
        productCart.cartQuantity =
            listCart[index].cartQuantity! + productCart.cartQuantity!;

        productCart.priceTotal =
            (productCart.cartQuantity! * productCart.cartPrice!);

        listCart[index] = productCart;

        await Session.data.setString('cart', json.encode(listCart));
      } else {
        productCart.priceTotal =
            (productCart.cartQuantity! * productCart.cartPrice!);
        listCart.add(productCart);
        await Session.data.setString('cart', json.encode(listCart));
      }
    }
    context.read<ProductProvider>().cartApplyShippingMethods(context);
    widget.loadCount!();
    this.setState(() {});
    Navigator.pop(context);
    // snackBar(context, message: "test");
    addToCartAlertDialog(context, product);
    // productCart.cartQuantity = 0;
    setState(() {
      cartQuantityAddToCart = 0;
    });
  }

  addToCartAlertDialog(BuildContext context, ProductModel product) {
    List<String> name = [], selectedName = [];
    printLog("${product.type}", name: "TIPE PRODUCT");
    if (product.type == "variable") {
      for (var customVariation in product.customVariation!) {
        name.add(customVariation.name!);
        selectedName.add(customVariation.selectedName!);
      }
    }
    // set up the buttons
    Widget cancelButton = GestureDetector(
      child: Container(
          height: 35.h,
          width: 230.w,
          decoration: BoxDecoration(
              color: primaryColor, borderRadius: BorderRadius.circular(5)),
          child: Center(
              child: Text(
                  "${AppLocalizations.of(context)!.translate('go_to_cart')}"))),
      onTap: () {
        Navigator.of(GlobalVariable.navState.currentContext!).pop();
        Navigator.of(GlobalVariable.navState.currentContext!)
            .push(MaterialPageRoute(
                builder: (context) => CartScreen(
                      isFromHome: false,
                    )));
      },
    );
    Widget continueButton = GestureDetector(
      child: Container(
          height: 35.h,
          width: 230.w,
          decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(5),
              border: Border.all(color: Colors.black)),
          child: Center(
              child: Text(
                  "${AppLocalizations.of(context)!.translate('continue')}"))),
      onTap: () {
        Navigator.of(GlobalVariable.navState.currentContext!).pop();
      },
    );

    Widget doneIcon = Container(
      padding: EdgeInsets.all(5.w),
      decoration: BoxDecoration(
          shape: BoxShape.circle, border: Border.all(color: primaryColor)),
      child: Container(
        padding: EdgeInsets.all(8.w),
        decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: primaryColor, width: 3.w)),
        child: Icon(
          Icons.done,
          size: 30.h,
          color: primaryColor,
        ),
      ),
    );
    // set up the AlertDialog
    AlertDialog alert = AlertDialog(
      title: doneIcon,
      actionsAlignment: MainAxisAlignment.center,
      content: Container(
        constraints: BoxConstraints(maxHeight: 30.h),
        child: Center(
            child: Text(
          "${AppLocalizations.of(context)!.translate('product_was_added')}",
          style: TextStyle(
              fontWeight: FontWeight.bold, fontSize: responsiveFont(10)),
        )),
        // child: Column(
        //   crossAxisAlignment: CrossAxisAlignment.start,
        //   mainAxisSize: MainAxisSize.min,
        //   children: [
        //     Text("${product.productName}"),
        //     SizedBox(
        //       height: 10.h,
        //     ),
        //     Row(
        //       children: [
        //         Column(
        //           crossAxisAlignment: CrossAxisAlignment.start,
        //           children: [
        //             for (var i in name) Text("$i"),
        //             Text(AppLocalizations.of(context)!.translate('qty')!)
        //           ],
        //         ),
        //         SizedBox(
        //           width: 10.w,
        //         ),
        //         Column(
        //           crossAxisAlignment: CrossAxisAlignment.start,
        //           children: [
        //             for (var i in selectedName) Text(": $i"),
        //             Text(": $cartQuantityAddToCart")
        //           ],
        //         ),
        //       ],
        //     ),
        //   ],
        // ),
      ),
      actions: [
        Column(
          children: [
            continueButton,
            SizedBox(
              height: 8.h,
            ),
            cancelButton,
            SizedBox(
              height: 10.h,
            )
          ],
        )
      ],
    );

    // show the dialog
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return alert;
      },
    );
  }

  /*init variation & check if variation true*/
  initVariation() {
    if (widget.productModel!.attributes!.isNotEmpty &&
        widget.productModel!.type == 'variable') {
      widget.productModel!.customVariation!.forEach((element) {
        print("Variation True");
        setState(() {
          variation.add(new ProductVariation(
              id: element.id,
              value: element.selectedValue,
              columnName: element.slug));
        });
      });
      checkProductVariant(widget.productModel!);
    }
    if (widget.productModel!.type == 'simple' &&
        widget.productModel!.productStock != 0) {
      setState(() {
        isAvailable = true;
        widget.productModel!.cartPrice = widget.productModel!.productPrice;
      });
    }
  }

  /*get variant id, if product have variant*/
  checkProductVariant(ProductModel productModel) async {
    setState(() {
      load = true;
    });
    var tempVar = [];
    productModel.customVariation!.forEach((element) {
      setState(() {
        tempVar.add(element.selectedName);
      });
    });
    print(tempVar);
    variationName = tempVar.join(", ");
    productModel.variationName = variationName;
    final product = Provider.of<ProductProvider>(context, listen: false);
    final Future<Map<String, dynamic>?> productResponse =
        product.checkVariation(
            context: context, productId: productModel.id, list: variation);

    productResponse.then((value) {
      if (value!['variation_id'] != 0) {
        setState(() {
          productModel.variantId = value['variation_id'];
          load = false;
          variationResult = value;

          productModel.availableVariations!.forEach((element) {
            if (element.variationId == productModel.variantId) {
              variationPrice = element.displayPrice!;
              variationSalePrice =
                  checkVariationDiscPrice(context, element.displayPrice!);
            }
          });
          if (value['data']['wholesales'] != null &&
              value['data']['wholesales'].isNotEmpty) {
            if (value['data']['wholesales'][0]['price'].isNotEmpty &&
                Session.data.getString('role') == 'wholesale_customer') {
              variationPrice =
                  double.parse(value['data']['wholesales'][0]['price']);
            }
          }
          if (value['data']['stock_status'] == 'instock' &&
                  value['data']['stock_quantity'] == null ||
              value['data']['stock_quantity'] == 0) {
            variationStock = 999;
            isAvailable = true;
            isOutStock = false;
          } else if (value['data']['stock_status'] == 'outofstock') {
            print('outofstock');
            isAvailable = true;
            isOutStock = true;
            variationStock = 0;
          } else if (value['data']['price'] == 0) {
            print('price not set');
            isAvailable = false;
            isOutStock = false;
            variationStock = 0;
          } else {
            print('else');
            variationStock = value['data']['stock_quantity'];
            isAvailable = true;
            isOutStock = false;
          }
        });
      } else {
        if (mounted)
          setState(() {
            variationPrice = 0;
            isAvailable = false;
            load = false;
          });
      }
    });
  }

  Future onFinishBuyNow() async {
    await Navigator.pushReplacement(
        context, MaterialPageRoute(builder: (context) => OrderSuccess()));
  }

  buyNow() async {
    print("Buy Now");
    setState(() {
      widget.productModel?.a2wShippingMethod = "";
      if (Provider.of<ProductProvider>(context, listen: false)
          .shippingMethods
          .isNotEmpty) {
        widget.productModel?.a2wShippingMethod = Provider.of<ProductProvider>(
                context,
                listen: false)
            .shippingMethods[context.read<ProductProvider>().selectedShipping]
            .serviceName;

        var tempa2wshipping = {
          "method": Provider.of<ProductProvider>(context, listen: false)
              .shippingMethods[context.read<ProductProvider>().selectedShipping]
              .serviceName,
          "cost": Provider.of<ProductProvider>(context, listen: false)
              .shippingMethods[context.read<ProductProvider>().selectedShipping]
              .price
        };

        widget.productModel?.a2wShippingCheckoutData = [];
        if (Provider.of<ProductProvider>(context, listen: false)
            .shippingMethods
            .isNotEmpty) {
          widget.productModel?.a2wShippingCheckoutData = [tempa2wshipping];
        }
      }
    });
    await Provider.of<OrderProvider>(context, listen: false)
        .buyNow(context, widget.productModel, onFinishBuyNow);
  }

  @override
  Widget build(BuildContext context) {
    return StatefulBuilder(
        builder: (BuildContext context, StateSetter setState) {
      return Container(
        constraints: BoxConstraints(
            maxHeight: MediaQuery.of(context).size.height -
                MediaQuery.of(context).viewPadding.top),
        child: SingleChildScrollView(
            child: Wrap(children: [
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Stack(
                children: [
                  Container(
                    height: 250.h,
                    width: MediaQuery.of(context).size.width,
                    child: CachedNetworkImage(
                      // imageUrl:
                      //     widget.productModel!.customVariation!.length != 0
                      //         ? widget.productModel!.customVariation![0]
                      //             .optionVariation![selectedVariantIndex].image!
                      //         : widget.productModel!.images![0].src!,
                      imageUrl: (widget.productModel!.customVariation != null &&
                              widget
                                  .productModel!.customVariation!.isNotEmpty &&
                              widget.productModel!.customVariation![0]
                                      .optionVariation !=
                                  null &&
                              widget.productModel!.customVariation![0]
                                  .optionVariation!.isNotEmpty &&
                              selectedVariantIndex <
                                  widget.productModel!.customVariation![0]
                                      .optionVariation!.length)
                          ? widget.productModel!.customVariation![0]
                              .optionVariation![selectedVariantIndex].image!
                          : (widget.productModel!.images != null &&
                                  widget.productModel!.images!.isNotEmpty)
                              ? widget.productModel!.images![0].src!
                              : '',
                      imageBuilder: (context, imageProvider) => Container(
                        height: 20.h,
                        width: 80.w,
                        decoration: BoxDecoration(
                          // color: Colors.grey[300],
                          borderRadius: BorderRadius.circular(10),
                          image: DecorationImage(
                            image: imageProvider,
                            fit: BoxFit.cover,
                          ),
                        ),
                      ),
                      placeholder: (context, url) => customLoading(),
                      errorWidget: (context, url, error) => Icon(Icons.error),
                    ),
                  ),
                  Positioned(
                    top: 8.h,
                    right: 9.w,
                    child: GestureDetector(
                      onTap: () => Navigator.pop(context),
                      child: Container(
                          width: 20.w,
                          height: 20.w,
                          decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(100),
                              color: Colors.grey[300]),
                          child: Center(
                            child: Icon(
                              Icons.clear,
                              color: Colors.black,
                              size: 15.w,
                            ),
                          )),
                    ),
                  ),
                  Positioned(
                      bottom: 2.h,
                      right: 9.w,
                      child: GestureDetector(
                        onTap: () {
                          Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => PageViewReview(
                                  isGeneral: true,
                                  image: widget.productModel!.customVariation!
                                              .length !=
                                          0
                                      ? widget
                                          .productModel!
                                          .customVariation![0]
                                          .optionVariation![
                                              selectedVariantIndex]
                                          .image!
                                      : widget.productModel!.images![0].src!,
                                ),
                              ));
                        },
                        child: Container(
                            width: 20.w,
                            height: 20.w,
                            decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(100),
                                color: Colors.grey[300]),
                            child: Center(
                              child: Icon(
                                Icons.fullscreen,
                                color: Colors.black,
                                size: 15.w,
                              ),
                            )),
                      ))
                ],
              ),
              SizedBox(
                height: 10.h,
              ),
              Container(
                margin: EdgeInsets.symmetric(horizontal: 10.w),
                child: Row(
                  children: [
                    widget.productModel!.type == 'simple'
                        ? Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text(
                                stringToCurrency(
                                    widget.productModel!.productPrice!,
                                    context),
                                style: TextStyle(
                                    color: Colors.red,
                                    fontSize: responsiveFont(17),
                                    fontWeight: FontWeight.bold),
                              ),
                            ],
                          )
                        : Visibility(
                            visible: widget.productModel!.type == 'variable',
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Row(
                                  children: [
                                    Visibility(
                                      visible: variationSalePrice != 0,
                                      child: Text(
                                        stringToCurrency(
                                            variationPrice!, context),
                                        style: TextStyle(
                                            color: Colors.grey,
                                            fontSize: responsiveFont(17),
                                            decoration:
                                                TextDecoration.lineThrough,
                                            fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                    SizedBox(
                                      width: 5,
                                    ),
                                    Text(
                                      stringToCurrency(
                                          variationSalePrice != 0
                                              ? variationSalePrice!
                                              : variationPrice!,
                                          context),
                                      style: TextStyle(
                                          color: Colors.red,
                                          fontSize: responsiveFont(17),
                                          fontWeight: FontWeight.bold),
                                    ),
                                  ],
                                ),
                              ],
                            )),
                    SizedBox(
                      width: 10.w,
                    ),
                    Visibility(
                      visible: widget.productModel!.discProduct != 0,
                      child: Text(
                        "${widget.productModel?.discProduct!.round()}% off",
                        style: TextStyle(color: Colors.grey[500]),
                      ),
                    )
                  ],
                ),
              ),
              SizedBox(
                height: 5.h,
              ),
              Container(
                  padding: EdgeInsets.symmetric(horizontal: 15),
                  child: ListView.builder(
                      padding: EdgeInsets.zero,
                      shrinkWrap: true,
                      physics: ScrollPhysics(),
                      itemCount: widget.productModel!.customVariation!.length,
                      itemBuilder: (context, i) {
                        CustomVariationModel customVariation =
                            widget.productModel!.customVariation![i];
                        return Container(
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  child: Row(children: [
                                    Text(
                                      "${customVariation.name} : ",
                                      style: TextStyle(
                                          fontSize: responsiveFont(12),
                                          color: Colors.grey[500],
                                          fontWeight: FontWeight.w500),
                                    ),
                                    Text(
                                      "${customVariation.selectedName}",
                                      style: TextStyle(
                                          fontSize: responsiveFont(12),
                                          fontWeight: FontWeight.w500),
                                    )
                                  ]),
                                ),
                                SizedBox(
                                  height: 5,
                                ),
                                i == 0
                                    ? Container(
                                        child: GridView.builder(
                                            shrinkWrap: true,
                                            padding: EdgeInsets.zero,
                                            physics: ScrollPhysics(),
                                            gridDelegate:
                                                SliverGridDelegateWithFixedCrossAxisCount(
                                                    crossAxisCount: 4,
                                                    crossAxisSpacing: 15,
                                                    mainAxisSpacing: 15,
                                                    childAspectRatio: 1 / 1),
                                            itemCount: customVariation
                                                .optionVariation!.length,
                                            itemBuilder: (context, j) {
                                              OptionVariation optionVariation =
                                                  customVariation
                                                      .optionVariation![j];
                                              if (optionVariation.image ==
                                                  null) {
                                                return Icon(Icons.error);
                                              }
                                              return CachedNetworkImage(
                                                imageUrl:
                                                    optionVariation.image!,
                                                imageBuilder:
                                                    (context, imageProvider) =>
                                                        InkWell(
                                                  onTap: () {
                                                    setState(() {
                                                      selectedVariantIndex = j;
                                                      customVariation
                                                              .selectedName =
                                                          optionVariation.name;
                                                      customVariation
                                                              .selectedValue =
                                                          optionVariation.value;
                                                    });
                                                    variation
                                                        .forEach((element) {
                                                      if (element.id != 0) {
                                                        if (element
                                                                .columnName ==
                                                            customVariation
                                                                .slug) {
                                                          setState(() {
                                                            element.value =
                                                                optionVariation
                                                                    .value;
                                                          });
                                                        }
                                                      } else {
                                                        if (element
                                                                .columnName ==
                                                            customVariation
                                                                .name) {
                                                          setState(() {
                                                            element.value =
                                                                optionVariation
                                                                    .name;
                                                          });
                                                        }
                                                      }
                                                    });
                                                    checkProductVariant(
                                                        widget.productModel!);
                                                  },
                                                  child: Container(
                                                    height: 20.h,
                                                    width: 60.w,
                                                    decoration: BoxDecoration(
                                                      color: Colors.grey[300],
                                                      border: Border.all(
                                                          width: 2,
                                                          color: widget
                                                                      .productModel!
                                                                      .customVariation![
                                                                          i]
                                                                      .selectedName ==
                                                                  widget
                                                                      .productModel!
                                                                      .customVariation![
                                                                          i]
                                                                      .optionVariation![
                                                                          j]
                                                                      .name
                                                              ? primaryColor
                                                              : Colors
                                                                  .grey[300]!),
                                                      borderRadius:
                                                          BorderRadius.circular(
                                                              10),
                                                      image: DecorationImage(
                                                        image: imageProvider,
                                                        fit: BoxFit.cover,
                                                      ),
                                                    ),
                                                  ),
                                                ),
                                                placeholder: (context, url) =>
                                                    customLoading(),
                                                errorWidget:
                                                    (context, url, error) =>
                                                        Icon(Icons.error),
                                              );
                                            }),
                                      )
                                    : Wrap(
                                        crossAxisAlignment:
                                            WrapCrossAlignment.start,
                                        runSpacing: 10.0,
                                        spacing: 10.0,
                                        children: [
                                          for (int j = 0;
                                              j <
                                                  widget
                                                      .productModel!
                                                      .customVariation![i]
                                                      .optionVariation!
                                                      .length;
                                              j++)
                                            _buildVarianNonImage(
                                                customVariation, j)
                                        ],
                                      ),
                                SizedBox(
                                  height: 5,
                                ),
                              ]),
                        );
                      })),
            ],
          ),
          load
              ? Shimmer.fromColors(
                  child: Container(
                    decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8)),
                    margin: EdgeInsets.all(15),
                    height: 35.h,
                  ),
                  baseColor: Colors.grey[300]!,
                  highlightColor: Colors.grey[100]!)
              : !isAvailable
                  ? Container(
                      margin: EdgeInsets.symmetric(vertical: 20.h),
                      alignment: Alignment.center,
                      child: Text(
                        AppLocalizations.of(context)!
                            .translate('select_var_not_avail')!,
                        style: TextStyle(
                            color: Colors.red, fontWeight: FontWeight.bold),
                        textAlign: TextAlign.center,
                      ),
                    )
                  : Container(
                      margin: EdgeInsets.only(
                          left: 15, right: 15, top: 10, bottom: 20),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                child: Text(
                                  AppLocalizations.of(context)!
                                      .translate('qty')!,
                                  style: TextStyle(
                                      fontSize: responsiveFont(12),
                                      color: Colors.grey[500],
                                      fontWeight: FontWeight.w500),
                                ),
                              ),
                              SizedBox(
                                height: 5,
                              ),
                              Row(
                                children: [
                                  Container(
                                    alignment: Alignment.center,
                                    child: InkWell(
                                        onTap: () {
                                          setState(() {
                                            if (widget.productModel!
                                                    .cartQuantity! >
                                                1) {
                                              widget.productModel!
                                                  .cartQuantity = widget
                                                      .productModel!
                                                      .cartQuantity! -
                                                  1;
                                            }
                                          });
                                        },
                                        child:
                                            widget.productModel!.cartQuantity! >
                                                    1
                                                ? Container(
                                                    decoration: BoxDecoration(
                                                      color: Colors.grey[400],
                                                      shape: BoxShape.circle,
                                                    ),
                                                    child: Icon(
                                                      Icons.remove,
                                                      color: Colors.black,
                                                    ),
                                                  )
                                                : Container(
                                                    alignment: Alignment.center,
                                                    decoration: BoxDecoration(
                                                      color: Colors.grey[300],
                                                      shape: BoxShape.circle,
                                                    ),
                                                    child: Icon(
                                                      Icons.remove,
                                                      color: Colors.grey,
                                                    ),
                                                  )),
                                  ),
                                  SizedBox(
                                    width: 15,
                                  ),
                                  Text(
                                      (widget.productModel!.cartQuantity)
                                          .toString(),
                                      style: TextStyle(
                                        fontSize: 16,
                                      )),
                                  SizedBox(
                                    width: 15,
                                  ),
                                  Container(
                                    alignment: Alignment.center,
                                    child: InkWell(
                                        onTap: widget.productModel!
                                                    .productStock! <=
                                                widget
                                                    .productModel!.cartQuantity!
                                            ? null
                                            : () {
                                                setState(() {
                                                  widget.productModel!
                                                      .cartQuantity = widget
                                                          .productModel!
                                                          .cartQuantity! +
                                                      1;
                                                });
                                              },
                                        child:
                                            widget.productModel!.productStock! >
                                                    widget.productModel!
                                                        .cartQuantity!
                                                ? Container(
                                                    decoration: BoxDecoration(
                                                      color: Colors.grey[400],
                                                      shape: BoxShape.circle,
                                                    ),
                                                    child: Icon(
                                                      Icons.add,
                                                      color: Colors.black,
                                                    ),
                                                  )
                                                : Container(
                                                    alignment: Alignment.center,
                                                    decoration: BoxDecoration(
                                                      color: Colors.grey[300],
                                                      shape: BoxShape.circle,
                                                    ),
                                                    child: Icon(
                                                      Icons.add,
                                                      color: Colors.grey,
                                                    ),
                                                  )),
                                  )
                                ],
                              ),
                            ],
                          ),
                          Container(
                              child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              // widget.productModel!.type == 'simple'
                              //     ? Column(
                              //         crossAxisAlignment: CrossAxisAlignment.end,
                              //         children: [
                              //           Text(
                              //             stringToCurrency(
                              //                 widget.productModel!.productPrice!,
                              //                 context),
                              //             style: TextStyle(
                              //                 color: secondaryColor,
                              //                 fontSize: responsiveFont(12),
                              //                 fontWeight: FontWeight.w500),
                              //           ),
                              //           Text(
                              //             widget.productModel!.productStock == 999
                              //                 ? '${AppLocalizations.of(context)!.translate('stock')} : ${AppLocalizations.of(context)!.translate('available')}'
                              //                 : '${AppLocalizations.of(context)!.translate('stock')} : ${widget.productModel!.productStock}',
                              //             style: TextStyle(
                              //               fontSize: responsiveFont(12),
                              //             ),
                              //           )
                              //         ],
                              //       )
                              //     : Visibility(
                              //         visible:
                              //             widget.productModel!.type == 'variable',
                              //         child: Column(
                              //           crossAxisAlignment:
                              //               CrossAxisAlignment.end,
                              //           children: [
                              //             Row(
                              //               children: [
                              //                 Visibility(
                              //                   visible: variationSalePrice != 0,
                              //                   child: Text(
                              //                     stringToCurrency(
                              //                         variationPrice!, context),
                              //                     style: TextStyle(
                              //                         color: Colors.grey,
                              //                         fontSize:
                              //                             responsiveFont(12),
                              //                         decoration: TextDecoration
                              //                             .lineThrough,
                              //                         fontWeight:
                              //                             FontWeight.w500),
                              //                   ),
                              //                 ),
                              //                 SizedBox(
                              //                   width: 5,
                              //                 ),
                              //                 Text(
                              //                   stringToCurrency(
                              //                       variationSalePrice != 0
                              //                           ? variationSalePrice!
                              //                           : variationPrice!,
                              //                       context),
                              //                   style: TextStyle(
                              //                       color: secondaryColor,
                              //                       fontSize: responsiveFont(12),
                              //                       fontWeight: FontWeight.w500),
                              //                 ),
                              //               ],
                              //             ),
                              //             Text(
                              //               variationStock == 999
                              //                   ? '${AppLocalizations.of(context)!.translate('stock')} : ${AppLocalizations.of(context)!.translate('in_stock')}'
                              //                   : '${AppLocalizations.of(context)!.translate('stock')} : $variationStock',
                              //               style: TextStyle(
                              //                 fontSize: responsiveFont(12),
                              //               ),
                              //             )
                              //           ],
                              //         ))
                            ],
                          ))
                        ],
                      ),
                    ),
          Consumer<ProductProvider>(
            builder: (context, value, child) => value.responseShippingInfo ==
                        "" &&
                    value.shippingMethods.isEmpty
                ? Container()
                : Container(
                    padding: EdgeInsets.only(left: 15, right: 15, bottom: 15),
                    // height: MediaQuery.of(context).size.height / 4.5,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              "${AppLocalizations.of(context)!.translate('choose_delivery')}",
                              style: TextStyle(
                                  fontSize: responsiveFont(12),
                                  color: Colors.grey[500],
                                  fontWeight: FontWeight.w500),
                            ),
                            GestureDetector(
                              onTap: () {
                                Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) =>
                                          ShippingMethodScreen(
                                        productModel: widget.productModel,
                                      ),
                                    ));
                              },
                              child: Row(
                                children: [
                                  Icon(Icons.location_on_outlined),
                                  Text(
                                      " ${AppLocalizations.of(context)!.translate('deliver_to')} ${value.selectedCountry?.name}")
                                ],
                              ),
                            )
                          ],
                        ),
                        SizedBox(
                          height: 10,
                        ),
                        value.loadingShipping
                            ? Shimmer.fromColors(
                                child: Container(
                                  width: double.infinity,
                                  height: 40,
                                  decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(10),
                                      color: Colors.white),
                                ),
                                baseColor: Colors.grey[300]!,
                                highlightColor: Colors.grey[100]!)
                            : value.responseShippingInfo != ""
                                ? Text(
                                    value.responseShippingInfo,
                                    style:
                                        TextStyle(fontWeight: FontWeight.w600),
                                  )
                                : _buildShipping(value
                                    .shippingMethods[value.selectedShipping]),
                      ],
                    ),
                  ),
          ),
          _buildAllBtn()
        ])),
      );
    });
  }

  _buildShipping(ShippingMethodModel shipping) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ShippingMethodScreen(
                productModel: widget.productModel,
              ),
            ));
      },
      child: Container(
        padding: EdgeInsets.all(8),
        margin: EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
            border: Border.all(color: Colors.grey[400]!),
            borderRadius: BorderRadius.circular(10),
            color: Colors.grey[200]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          shipping.price! > 0
              ? Text(
                  "${AppLocalizations.of(context)!.translate('delivery')}: ${stringToCurrency(shipping.price!, context)}",
                  style: TextStyle(fontWeight: FontWeight.w600),
                )
              : Text(
                  "${AppLocalizations.of(context)!.translate('free_delivery')}",
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
          HtmlWidget(
            shipping.label ?? "-",
            textStyle:
                TextStyle(fontSize: responsiveFont(8), color: Colors.black),
          ),
          Container(
            padding: EdgeInsets.all(5),
            decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(5),
                color: Colors.grey[300]),
            child: Text(
              shipping.tracking!
                  ? "${AppLocalizations.of(context)!.translate('tracking_available')}"
                  : "${AppLocalizations.of(context)!.translate('tracking_not_available')}",
              style: TextStyle(fontSize: 10),
            ),
          )
        ]),
      ),
    );
  }

  _buildAllBtn() {
    return Align(
      alignment: Alignment.bottomCenter,
      child: Container(
          padding: EdgeInsets.symmetric(horizontal: 15),
          decoration: BoxDecoration(
            color: Colors.white,
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: Colors.black54,
                blurRadius: 5.0,
              )
            ],
          ),
          height: 50.h,
          width: double.infinity,
          child: widget.type == 'all'
              ? Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [_buildBtnATC(), _buildBtnBuy()],
                )
              : widget.type == 'add'
                  ? Container(
                      margin: EdgeInsets.symmetric(vertical: 10),
                      child: _buildBtnATC(),
                    )
                  : Container(
                      margin: EdgeInsets.symmetric(vertical: 10),
                      child: _buildBtnBuy(),
                    )),
    );
  }

  _buildBtnATC() {
    return Container(
      decoration: BoxDecoration(
          borderRadius: widget.type == 'add'
              ? BorderRadius.circular(15)
              : BorderRadius.only(
                  bottomLeft:
                      lang == 'ar' ? Radius.circular(0) : Radius.circular(15),
                  topLeft:
                      lang == 'ar' ? Radius.circular(0) : Radius.circular(15),
                  topRight:
                      lang == 'ar' ? Radius.circular(15) : Radius.circular(0),
                  bottomRight:
                      lang == 'ar' ? Radius.circular(15) : Radius.circular(0)),
          gradient: LinearGradient(
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
              colors: widget.productModel!.stockStatus != 'outofstock' &&
                      widget.productModel!.productStock! >= 1
                  ? [HexColor("FFC200"), HexColor("FF8329")]
                  : [Colors.grey, Colors.grey])),
      width: 130.w,
      height: 30.h,
      child: TextButton(
          onPressed: !isAvailable || load || isOutStock
              ? null
              : () {
                  if (widget.productModel!.productStock != null &&
                      widget.productModel!.productStock != 0) {
                    print(
                        "Product Price Cart : ${widget.productModel!.productPrice}");
                    addCart(widget.productModel!);
                  } else {
                    Navigator.pop(context);
                    snackBar(context, message: 'Product out ouf stock.');
                  }
                },
          child: Text(AppLocalizations.of(context)!.translate('add_to_cart')!,
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: responsiveFont(9),
                  color: Colors.white,
                  fontWeight: FontWeight.bold))),
    );
  }

  _buildBtnBuy() {
    return Container(
      decoration: BoxDecoration(
          borderRadius: widget.type == 'buy'
              ? BorderRadius.circular(15)
              : BorderRadius.only(
                  bottomRight:
                      lang == 'ar' ? Radius.circular(0) : Radius.circular(15),
                  topRight:
                      lang == 'ar' ? Radius.circular(0) : Radius.circular(15),
                  topLeft:
                      lang == 'ar' ? Radius.circular(15) : Radius.circular(0),
                  bottomLeft:
                      lang == 'ar' ? Radius.circular(15) : Radius.circular(0)),
          gradient: LinearGradient(
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
              colors: widget.productModel!.stockStatus != 'outofstock' &&
                      widget.productModel!.productStock! >= 1
                  ? [HexColor("FF3000"), HexColor("FF640E")]
                  : [Colors.grey, Colors.grey])),
      width: 130.w,
      height: 30.h,
      child: TextButton(
        onPressed: !isAvailable || load
            ? null
            : () {
                buyNow();
              },
        child: Text(
          AppLocalizations.of(context)!.translate('buy_now')!,
          style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: responsiveFont(9)),
        ),
      ),
    );
  }

  _buildVarianNonImage(CustomVariationModel customVariation, int i) {
    OptionVariation optionVariation = customVariation.optionVariation![i];
    return InkWell(
      onTap: () {
        setState(() {
          customVariation.selectedName = optionVariation.name;
          customVariation.selectedValue = optionVariation.value;
        });
        variation.forEach((element) {
          if (element.id != 0) {
            if (element.columnName == customVariation.slug) {
              setState(() {
                element.value = optionVariation.value;
              });
            }
          } else {
            if (element.columnName == customVariation.name) {
              setState(() {
                element.value = optionVariation.name;
              });
            }
          }
        });
        checkProductVariant(widget.productModel!);
      },
      child: Container(
        padding: EdgeInsets.all(5),
        width: 90.w,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(
              width: 2,
              color: customVariation.selectedName == optionVariation.name
                  ? primaryColor
                  : Colors.grey[300]!),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          optionVariation.name!,
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}
