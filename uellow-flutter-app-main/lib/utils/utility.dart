import 'dart:developer' as dev;
import 'dart:math';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_phoenix/flutter_phoenix.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:html_unescape/html_unescape.dart';
import 'package:intl/intl.dart';
import 'package:modal_bottom_sheet/modal_bottom_sheet.dart';
import 'package:nyoba/models/discount_model.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/pages/auth/login_screen.dart';
import 'package:nyoba/pages/product/modal_sheet_cart/modal_sheet_cart.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/order_provider.dart';
import 'package:nyoba/widgets/home/card_item_shimmer.dart';
import 'package:provider/provider.dart';

import '../app_localizations.dart';
import '../models/checkout_data_model.dart';

Color primaryColor = HexColor("ED1D1D");
Color secondaryColor = HexColor("960000");

double responsiveFont(double designFont) {
  return ScreenUtil().setSp(designFont + 2);
}

Widget customLoading({Color? color, double? size = 30.0}) {
  return SpinKitFadingCircle(
    color: color == null ? primaryColor : color,
    size: size!,
  );
}

printLog(String message, {String? name}) {
  return dev.log(message, name: name ?? 'log');
}

convertDateFormatShortMonth(date) {
  String dateTime = DateFormat("dd MMM yyyy").format(date);
  return dateTime;
}

convertDateFormatSlash(date) {
  String dateTime = DateFormat("dd/MM/yyyy").format(date);
  return dateTime;
}

convertDateFormatFull(date) {
  String dateTime = DateFormat("dd MMMM yyyy").format(date);
  return dateTime;
}

convertDateFormatDash(date) {
  String dateTime = DateFormat("dd-MM-yyyy").format(date);
  return dateTime;
}

snackBar(context, {required String message, Color? color, int duration = 2}) {
  final snackBar = SnackBar(
    content: Text(message),
    backgroundColor: color != null ? color : null,
    duration: Duration(seconds: duration),
  );
  return ScaffoldMessenger.of(context).showSnackBar(snackBar);
}

String? alertPhone(context) {
  return AppLocalizations.of(context)!.translate('hint_otp');
}

loadingPop(context) {
  showDialog(
    context: context,
    builder: (_) {
      return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
          content: Container(
              height: MediaQuery.of(context).size.height * 0.05,
              margin: EdgeInsets.all(10),
              child: Row(
                children: [
                  customLoading(),
                  SizedBox(width: 10),
                  Text("${AppLocalizations.of(context)!.translate('loading')}")
                ],
              )));
    },
    barrierDismissible: false,
  );
}

buildNoAuth(context) {
  final imageNoLogin =
      Provider.of<HomeProvider>(context, listen: false).imageNoLogin;
  return Column(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      imageNoLogin.image == null
          ? Icon(
              Icons.not_interested,
              color: primaryColor,
              size: 75,
            )
          : CachedNetworkImage(
              imageUrl: imageNoLogin.image!,
              height: MediaQuery.of(context).size.height * 0.08,
              placeholder: (context, url) => Container(),
              errorWidget: (context, url, error) => Icon(
                    Icons.not_interested,
                    color: primaryColor,
                    size: 75,
                  )),
      SizedBox(
        height: 10,
      ),
      Text(
        "${AppLocalizations.of(context)!.translate('please_login_first')}",
        style: TextStyle(
            color: Colors.black, fontWeight: FontWeight.w500, fontSize: 14),
        textAlign: TextAlign.center,
      ),
      SizedBox(
        height: 10,
      ),
      Container(
        decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(5),
            gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [primaryColor, secondaryColor])),
        height: 30.h,
        width: MediaQuery.of(context).size.width * 0.5,
        child: TextButton(
          onPressed: () {
            Navigator.push(
                context, MaterialPageRoute(builder: (context) => Login()));
          },
          child: Text(
            "${AppLocalizations.of(context)!.translate('login')}",
            style: TextStyle(
                color: Colors.black,
                fontSize: responsiveFont(10),
                fontWeight: FontWeight.w500),
          ),
        ),
      ),
    ],
  );
}

convertHtmlUnescape(String textCharacter) {
  var unescape = HtmlUnescape();
  var text = unescape.convert(textCharacter);
  return text;
}

Widget shimmerProductItemSmall() {
  return ListView.separated(
    itemCount: 6,
    scrollDirection: Axis.horizontal,
    itemBuilder: (context, i) {
      return CardItemShimmer(
        i: i,
        itemCount: 6,
      );
    },
    separatorBuilder: (BuildContext context, int index) {
      return SizedBox(
        width: 5,
      );
    },
  );
}

Widget buildSearchEmpty(context, text) {
  final searchEmpty =
      Provider.of<HomeProvider>(context, listen: false).imageSearchEmpty;
  return Center(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        searchEmpty.image == null
            ? Icon(
                Icons.search,
                color: primaryColor,
                size: 75,
              )
            : CachedNetworkImage(
                imageUrl: searchEmpty.image!,
                height: MediaQuery.of(context).size.height * 0.4,
                placeholder: (context, url) => Container(),
                errorWidget: (context, url, error) => Icon(
                      Icons.search,
                      color: primaryColor,
                      size: 75,
                    )),
        Container(
          alignment: Alignment.topCenter,
          child: Text(
            text,
            style: TextStyle(fontSize: 18),
          ),
        )
      ],
    ),
  );
}

buildButtonCart(context, product) {
  final loadCount =
      Provider.of<OrderProvider>(context, listen: false).loadCartCount;
  return GestureDetector(
    onTap: () {
      if (product.stockStatus != 'outofstock' && product.productStock >= 1) {
        showMaterialModalBottomSheet(
          context: context,
          backgroundColor: Theme.of(context).colorScheme.surface,
          builder: (context) => ModalSheetCart(
            product: product,
            type: 'add',
            loadCount: loadCount,
          ),
        );
      } else {
        snackBar(context,
            message:
                AppLocalizations.of(context)!.translate('product_out_stock')!);
      }
    },
    child: Icon(
      Icons.add_shopping_cart,
      color: secondaryColor,
      size: 20.h,
    ),
  );
}

buildError(context) {
  return Container(
    padding: EdgeInsets.all(15),
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Image.asset(
          'images/icon/icon.png',
          height: 100,
        ),
        SizedBox(
          height: 10,
        ),
        Container(
          child: Text(
            "Oops!",
            style: TextStyle(
              fontSize: responsiveFont(24),
            ),
          ),
        ),
        Container(
          child: Text(
            "Sorry, we're down for rescheduled maintenance right now.",
            style: TextStyle(
              fontSize: responsiveFont(18),
            ),
            textAlign: TextAlign.center,
          ),
        ),
        SizedBox(
          height: 15,
        ),
        MaterialButton(
          padding: EdgeInsets.all(10),
          onPressed: () {
            Phoenix.rebirth(context);
          },
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              Icon(
                Icons.refresh,
              ),
              Text(
                'Refresh App',
              )
            ],
          ),
        )
      ],
    ),
  );
}

num roundDouble(num value, context) {
  final decimalNum =
      Provider.of<HomeProvider>(context, listen: false).formatCurrency.slug;

  num mod = pow(10.0, int.parse(decimalNum!));
  return ((value * mod).round().toDouble() / mod);
}

ProductModel checkDiscountRules(context, ProductModel product) {
  final Discount? discount =
      Provider.of<HomeProvider>(context, listen: false).discount;
  if (discount!.calculateDiscountFrom == 'regular_price') {
    product.discProduct =
        double.parse(discount.discountRules!.ranges!.first.value);
    if (discount.discountRules!.ranges!.first.type == 'percentage') {
      if (product.type == 'variable') {
        List<num> _variationPrices = [];
        product.variationPrices!.forEach((element) {
          var _element = roundDouble(element, context) -
              (roundDouble(element, context) * (product.discProduct! / 100));
          _variationPrices.add(roundDouble(_element, context));
        });
        product.variationPricesDisc = _variationPrices;
      } else {
        product.productPrice = roundDouble(
            (double.parse(product.productRegPrice!) -
                (double.parse(product.productRegPrice!) *
                    (product.discProduct! / 100))),
            context);
      }
    }
  }
  return product;
}

LineItem checkLineItemDiscountRules(context, LineItem product) {
  final Discount? discount =
      Provider.of<HomeProvider>(context, listen: false).discount;
  if (discount!.calculateDiscountFrom == 'regular_price') {
    product.discProduct =
        double.parse(discount.discountRules!.ranges!.first.value);
    if (discount.discountRules!.ranges!.first.type == 'percentage') {
      printLog(
          "masuk if checkLineItemDiscountRules ${product.productRegPrice} ${product.discProduct}");
      product.price =
          "${roundDouble((double.parse(product.productRegPrice!) - (double.parse(product.productRegPrice!) * (product.discProduct! / 100))), context)}";
    }
  }
  printLog("checkLineItemDiscountRules price: ${product.price}");
  return product;
}

num checkVariationDiscPrice(context, num value) {
  final Discount? discount =
      Provider.of<HomeProvider>(context, listen: false).discount;
  num _element = 0;
  if (discount!.calculateDiscountFrom == 'regular_price') {
    double discProduct =
        double.parse(discount.discountRules!.ranges!.first.value);
    if (discount.discountRules!.ranges!.first.type == 'percentage') {
      _element = roundDouble(value, context) -
          (roundDouble(value, context) * (discProduct / 100));
    }
  }
  return roundDouble(_element, context);
}

List<ProductModel> isDiscountRuleValid(context, List<ProductModel> products) {
  bool _isValid = true;
  final Discount? discount =
      Provider.of<HomeProvider>(context, listen: false).discount;
  if (discount!.calculateDiscountFrom == 'regular_price') {
    int? _startRange = discount.discountRules!.ranges!.first.from != ""
        ? int.parse(discount.discountRules!.ranges!.first.from)
        : 0;
    int? _endRange = discount.discountRules!.ranges!.first.to != ""
        ? int.parse(discount.discountRules!.ranges!.first.to)
        : 0;
    if (discount.discountRules!.operator == 'variation') {
      if (discount.discountRules!.ranges!.first.type == 'percentage') {
        products.forEach((p) {
          int index = products.indexWhere((prod) => prod.id == p.id);

          if (index != -1) {
            if (products[index].variantId != p.variantId) {
              products[index].qtyTotal =
                  products[index].cartQuantity! + p.cartQuantity!;
              p.qtyTotal = products[index].qtyTotal;
            } else {
              p.qtyTotal = p.cartQuantity;
            }
          }
        });

        products.forEach((p) {
          if (_startRange <= p.cartQuantity! &&
              _endRange >= p.cartQuantity! &&
              _startRange <= p.qtyTotal! &&
              _endRange >= p.qtyTotal!) {
            _isValid = true;
            if (p.type == 'simple') {
              p.cartPrice = p.productPrice;
            } else {
              p.cartPrice = p.productPriceDisc;
            }
          } else {
            _isValid = false;
            if (p.type == 'simple') {
              p.cartPrice = num.parse(p.productRegPrice);
            } else {
              p.cartPrice = p.productPrice;
            }
          }
          p.isDiscRuleValid = _isValid;
          p.priceTotal = p.cartQuantity! * p.cartPrice!;
        });
      }
    } else if (discount.discountRules!.operator == 'product_cumulative') {
      if (discount.discountRules!.ranges!.first.type == 'percentage') {
        int _totalCartCumulative = 0;
        products.forEach((p) {
          _totalCartCumulative = _totalCartCumulative + p.cartQuantity!;
        });

        printLog(
            "masuk percentage: ${_startRange <= _totalCartCumulative && _endRange >= _totalCartCumulative}");
        products.forEach((p) {
          if (_startRange <= _totalCartCumulative &&
              _endRange >= _totalCartCumulative) {
            _isValid = true;
            if (p.type == 'simple') {
              printLog("simple");
              p.cartPrice = p.productPrice;
            } else {
              p.cartPrice = p.productPriceDisc;
            }
          } else {
            _isValid = false;
            if (p.type == 'simple') {
              p.cartPrice = num.parse(p.productRegPrice);
            } else {
              p.cartPrice = p.productPrice;
            }
          }
          p.isDiscRuleValid = _isValid;
          p.priceTotal = p.cartQuantity! * p.cartPrice!;
        });
      }
    } else if (discount.discountRules!.operator == 'product') {
      if (discount.discountRules!.ranges!.first.type == 'percentage') {
        products.forEach((p) {
          if (_startRange < p.cartQuantity! && _endRange >= p.cartQuantity!) {
            _isValid = true;
            if (p.type == 'simple') {
              p.cartPrice = p.productPrice;
            } else {
              p.cartPrice = p.productPriceDisc;
            }
          } else {
            _isValid = false;
            if (p.type == 'simple') {
              p.cartPrice = num.parse(p.productRegPrice);
            } else {
              p.cartPrice = p.productPrice;
            }
          }
          p.isDiscRuleValid = _isValid;
          p.priceTotal = p.cartQuantity! * p.cartPrice!;
        });
      }
    }
  }
  return products;
}

List<LineItem> isLineItemDiscountRuleValid(context, List<LineItem> products) {
  bool _isValid = true;
  final Discount? discount =
      Provider.of<HomeProvider>(context, listen: false).discount;
  if (discount!.calculateDiscountFrom == 'regular_price') {
    int? _startRange = discount.discountRules!.ranges!.first.from != ""
        ? int.parse(discount.discountRules!.ranges!.first.from)
        : 0;
    int? _endRange = discount.discountRules!.ranges!.first.to != ""
        ? int.parse(discount.discountRules!.ranges!.first.to)
        : 0;
    if (discount.discountRules!.operator == 'variation') {
      if (discount.discountRules!.ranges!.first.type == 'percentage') {
        products.forEach((p) {
          if (_startRange <= p.qty! && _endRange >= p.qty!) {
            _isValid = true;
            p.price = p.price;
          } else {
            _isValid = false;
            p.price = p.productRegPrice;
          }
          p.isDiscRuleValid = _isValid;
        });
      }
    } else if (discount.discountRules!.operator == 'product_cumulative') {
      if (discount.discountRules!.ranges!.first.type == 'percentage') {
        int _totalCartCumulative = 0;
        products.forEach((p) {
          _totalCartCumulative = _totalCartCumulative + p.qty!;
        });

        products.forEach((p) {
          if (_startRange <= _totalCartCumulative &&
              _endRange >= _totalCartCumulative) {
            _isValid = true;
            p.price = p.price;
          } else {
            _isValid = false;
            p.price = p.productRegPrice;
          }
          p.isDiscRuleValid = _isValid;
        });
      }
    } else if (discount.discountRules!.operator == 'product') {
      if (discount.discountRules!.ranges!.first.type == 'percentage') {
        products.forEach((p) {
          if (_startRange < p.qty! && _endRange >= p.qty!) {
            _isValid = true;
            p.price = p.price;
          } else {
            _isValid = false;
            p.price = p.productRegPrice;
          }
          p.isDiscRuleValid = _isValid;
        });
      }
    }
  }
  return products;
}
