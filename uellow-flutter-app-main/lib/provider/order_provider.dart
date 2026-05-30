import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:nyoba/models/cart_model.dart';
import 'package:nyoba/models/order_model.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/pages/auth/login_screen.dart';
import 'package:nyoba/pages/order/checkout_native/detail_data_checkout_native.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/services/order_api.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:nyoba/widgets/webview/checkout_webview.dart';
import 'package:provider/provider.dart';

import '../app_localizations.dart';
import 'coupon_provider.dart';

class OrderProvider with ChangeNotifier {
  ProductModel? productDetail;
  String? status;
  String? search;

  bool isLoading = false;
  bool loadDataOrder = false;

  List<OrderModel> listOrder = [];
  List<OrderModel> tempOrder = [];
  int orderPage = 1;
  int limit = 100;

  List<ProductModel?> listProductOrder = [];

  OrderModel? detailOrder;
  int cartCount = 0;

  List<ProductModel?> tempProductOrder = [];

  bool loadingBuyAgain = false;

  Future checkout(order, BuildContext context) async {
    var result;
    await OrderAPI().checkoutOrder(order, context).then((data) {
      printLog(data, name: 'Link Order From API');
      result = data;
    });
    return result;
  }

  Future<List?> fetchOrders(
      {status, search, orderId, required BuildContext context}) async {
    isLoading = true;
    List result = [];
    String country = base64Encode(
        utf8.encode(context.read<ProductProvider>().currentPosition));
    try {
      await OrderAPI()
          .listMyOrder(
        status,
        search,
        orderId,
        orderPage,
        limit,
        context,
        country: country,
      )
          .then((data) {
        result = data;
        List _order = result;
        tempOrder = [];
        tempOrder
            .addAll(_order.map((order) => OrderModel.fromJson(order)).toList());
        List<OrderModel> list = List.from(listOrder);
        list.addAll(tempOrder);
        listOrder = list;
        if (tempOrder.length % 10 == 0) {
          orderPage++;
        }

        listOrder.forEach((element) {
          element.productItems!.sort((a, b) => b.image!.compareTo(a.image!));
        });

        isLoading = false;
        notifyListeners();
        printLog("${jsonEncode(result)}");
      });
    } catch (e) {
      printLog(e.toString());
      isLoading = false;
      notifyListeners();
    }
    return result;
  }

  Future<List?> fetchDetailOrder(orderId, BuildContext context) async {
    isLoading = true;
    var result;
    String country = base64Encode(
        utf8.encode(context.read<ProductProvider>().currentPosition));
    await OrderAPI()
        .detailOrder(
      orderId,
      context,
      country: country,
    )
        .then((data) {
      result = data;
      printLog("${jsonEncode(result)}", name: "response detail order");

      for (Map item in result) {
        detailOrder = OrderModel.fromJson(item);
      }

      isLoading = false;
      notifyListeners();
      printLog(result.toString());
    });
    return result;
  }

  Future<dynamic> loadCartCount() async {
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
      cartCount = _count;
      notifyListeners();
    }
    return _count;
  }

  Future checkOutOrder(context,
      {int? totalSelected,
      List<ProductModel>? productCart,
      Future<dynamic> Function()? removeOrderedItems}) async {
    final coupons = Provider.of<CouponProvider>(context, listen: false);
    final guestCheckoutActive =
        Provider.of<HomeProvider>(context, listen: false).guestCheckoutActive;
    print("$guestCheckoutActive is guestcheckout");
    if (totalSelected == 0) {
      snackBar(context, message: "Please select the product first.");
    } else {
      if (Session.data.getBool('isLogin') == false &&
          guestCheckoutActive == false) {
        return Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => Login(),
            ));
      }

      CartModel cart = new CartModel();
      cart.listItem = [];
      productCart!.forEach((element) {
        if (element.isSelected!) {
          var variation = {};
          if (element.selectedVariation!.isNotEmpty) {
            element.selectedVariation!.forEach((elementVar) {
              String columnName = elementVar.columnName!.toLowerCase();
              String? value = elementVar.value;

              variation['attribute_$columnName'] = "$value";
            });
          }
          printLog("${element.a2wShippingCheckoutData}",
              name: "a2wshippingcheckoudata");
          if (Provider.of<HomeProvider>(context, listen: false)
                  .isCheckoutNative ==
              true) {
            cart.listItem!.add(
              new CartProductItem(
                productId: element.id,
                quantity: element.cartQuantity,
                variationId: element.variantId,
                variation: [variation],
                a2wShipping: element.a2wShippingCheckoutData,
                a2wShippingMethod: element.a2wShippingMethod,
                codPayment: element.codPayment,
              ),
            );
          } else {
            cart.listItem!.add(
              new CartProductItem(
                productId: element.id,
                quantity: element.cartQuantity,
                variationId: element.variantId,
                variation: [variation],
                a2wShippingMethod: element.a2wShippingMethod,
                a2wShipping: [],
                codPayment: element.codPayment,
              ),
            );
          }
        }
      });

      //init list coupon
      cart.listCoupon = [];
      //check coupon
      if (coupons.couponUsed != null) {
        cart.listCoupon!.add(new CartCoupon(code: coupons.couponUsed!.code));
      }

      //add to cart model
      cart.paymentMethod = "xendit_bniva";
      cart.paymentMethodTitle = "Bank Transfer - BNI";
      cart.setPaid = true;
      cart.customerId = Session.data.getInt('id');
      cart.status = 'completed';
      cart.token = Session.data.getString('cookie');

      //Encode Json
      final jsonOrder = json.encode(cart);
      printLog(jsonOrder, name: 'Json Order');

      //Convert Json to bytes
      var bytes = utf8.encode(jsonOrder);

      //Convert bytes to base64
      var order = base64.encode(bytes);

      if (Provider.of<HomeProvider>(context, listen: false).isCheckoutNative ==
          true) {
        print("$guestCheckoutActive is guestcheckout");

        await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => DetailDataCheckoutNative(
                line: cart.listItem!,
                cart: cart,
                removeOrderedItems: removeOrderedItems,
              ),
            ));
      } else {
        //Generate link WebView checkout
        printLog("${jsonEncode(order)}", name: "DATA ORDER WEBVIEW");
        await Provider.of<OrderProvider>(context, listen: false)
            .checkout(order, context)
            .then((value) async {
          printLog(value, name: 'Link Order');
          await Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (context) => CheckoutWebView(
                        url: value,
                        onFinish: removeOrderedItems,
                      )));
        });
      }
    }
  }

  Future buyNow(context, ProductModel? product,
      Future<dynamic> Function() onFinishBuyNow) async {
    final guestCheckoutActive =
        Provider.of<HomeProvider>(context, listen: false).guestCheckoutActive;
    print("${Session.data.getBool('isLogin')} login");
    if (Session.data.getBool('isLogin') == false &&
        guestCheckoutActive == false) {
      return Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => Login(),
          ));
    }
    CartModel cart = new CartModel();
    cart.listItem = [];
    printLog(
        "${Provider.of<HomeProvider>(context, listen: false).isCheckoutNative}",
        name: "is checkout native");
    if (Provider.of<HomeProvider>(context, listen: false).isCheckoutNative ==
        true) {
      cart.listItem!.add(
        new CartProductItem(
          productId: product!.id,
          quantity: product.cartQuantity,
          variationId: product.variantId,
          a2wShipping: product.a2wShippingCheckoutData,
          codPayment: product.codPayment,
        ),
      );
    } else {
      cart.listItem!.add(
        new CartProductItem(
          productId: product!.id,
          quantity: product.cartQuantity,
          variationId: product.variantId,
          a2wShippingMethod: product.a2wShippingMethod,
          a2wShipping: [],
          codPayment: product.codPayment,
        ),
      );
    }

    //init list coupon
    cart.listCoupon = [];

    //add to cart model
    cart.paymentMethod = "xendit_bniva";
    cart.paymentMethodTitle = "Bank Transfer - BNI";
    cart.setPaid = true;
    cart.customerId = Session.data.getInt('id');
    cart.status = 'completed';
    cart.token = Session.data.getString('cookie');

    //Encode Json
    final jsonOrder = json.encode(cart);
    printLog(jsonOrder, name: 'Json Order');

    //Convert Json to bytes
    var bytes = utf8.encode(jsonOrder);

    //Convert bytes to base64
    var order = base64.encode(bytes);

    if (Provider.of<HomeProvider>(context, listen: false).isCheckoutNative ==
        true) {
      print(
        "$guestCheckoutActive is guestcheckout",
      );

      await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => DetailDataCheckoutNative(
              isFromBuyNow: true,
              line: cart.listItem!,
              cart: cart,
            ),
          ));
    } else {
      // //Generate link WebView checkout
      printLog("$order", name: "data order");
      await Provider.of<OrderProvider>(context, listen: false)
          .checkout(order, context)
          .then((value) async {
        printLog(value, name: 'Link Order');
        await Navigator.push(
            context,
            MaterialPageRoute(
                builder: (context) => CheckoutWebView(
                      url: value,
                      onFinish: onFinishBuyNow,
                    )));
      });
    }
  }

  Future loadItemOrder(context) async {
    loadDataOrder = true;
    if (detailOrder != null) {
      listProductOrder.clear();
      detailOrder!.productItems!.forEach((element) async {
        await Provider.of<ProductProvider>(context, listen: false)
            .fetchProductDetail(element.productId.toString(), context)
            .then((value) {
          listProductOrder.add(value);
        });
      });
      loadDataOrder = false;
    }
  }

  Future<void> actionBuyAgain(context) async {
    printLog("detail order: ${jsonEncode(detailOrder)}");
    printLog("list product: ${listProductOrder.isEmpty}");
    loadingBuyAgain = true;
    notifyListeners();
    if (listProductOrder.isEmpty) {
      await Future.delayed(Duration(seconds: 3));
    }
    printLog("list product: ${jsonEncode(listProductOrder)}");
    detailOrder!.productItems!.forEach((elementOrder) {
      listProductOrder.forEach((element) {
        if (element!.id == elementOrder.productId) {
          print('${element.id} == ${elementOrder.productId}');
          element.cartQuantity = elementOrder.quantity;
          element.variantId = elementOrder.variationId;
          element.priceTotal = element.productPrice! * element.cartQuantity!;
          element.cartPrice = element.productPrice! * element.cartQuantity!;
          element.attributes!.forEach((elementAttr) {
            elementOrder.metaData!.forEach((elementMeta) {
              if (elementAttr.name!.toLowerCase().replaceAll(" ", "-") ==
                  elementMeta.key) {
                elementAttr.selectedVariant = elementMeta.value;
              }
            });
          });
        }
      });
    });
    for (int i = 0; i < listProductOrder.length; i++) {
      await addCart(listProductOrder[i], context);
    }
    snackBar(context,
        message: AppLocalizations.of(context)!.translate('add_cart_message')!);
    loadingBuyAgain = false;
    notifyListeners();
  }

  /*add to cart*/
  Future addCart(ProductModel? product, context) async {
    /*check sharedprefs for cart*/
    if (!Session.data.containsKey('cart')) {
      List<ProductModel?> listCart = [];

      listCart.add(product);

      await Session.data.setString('cart', json.encode(listCart));
    } else {
      List products = await json.decode(Session.data.getString('cart')!);

      printLog(products.length.toString());
      printLog(products.toString(), name: 'Cart Product');

      List<ProductModel?> listCart =
          products.map((product) => ProductModel.fromJson(product)).toList();

      printLog(listCart.toString(), name: 'List Cart');

      int index = products.indexWhere((prod) =>
          prod["id"] == product!.id && prod["variant_id"] == product.variantId);

      if (index != -1) {
        product!.cartQuantity =
            listCart[index]!.cartQuantity! + product.cartQuantity!;

        listCart[index] = product;

        await Session.data.setString('cart', json.encode(listCart));
      } else {
        listCart.add(product);
        await Session.data.setString('cart', json.encode(listCart));
      }
    }
  }

  Future<List<ProductModel>> fetchProductCart(
      List<ProductModel> cartProduct, context) async {
    isLoading = true;
    List<ProductModel>? _temp = cartProduct;
    try {
      var result;
      List<String> _tempInclude = [];
      cartProduct.forEach((element) {
        _tempInclude.add(element.id.toString());
      });
      await OrderAPI()
          .loadProductCart(_tempInclude.join(','), context)
          .then((data) {
        result = data;
        tempProductOrder = [];
        for (Map item in result) {
          tempProductOrder.add(ProductModel.fromJson(item));
        }

        printLog(json.encode(cartProduct), name: "temp product order");

        tempProductOrder.forEach((tp) {
          cartProduct.forEach((cp) {
            if (tp?.id == cp.id) {
              cp.productPrice = cp.productPrice;
              cp.productRegPrice = cp.productRegPrice;
              cp.productSalePrice = cp.productSalePrice;
              cp.discProduct = tp?.discProduct;
              cp.stockStatus = tp?.stockStatus;
              // cp.showImage = cp.images![0].src;
              printLog(cp.images![0].src.toString(), name: "image variant");
              // cp.minMaxQuantity = tp?.minMaxQuantity;
              cp.manageStock = tp?.manageStock;
              cp.productStock = tp?.productStock;
              if (cp.type == 'simple' && cp.cartQuantity! > cp.productStock!) {
                cp.cartQuantity = 1;
              }
              cp.priceTotal = cp.cartQuantity! * tp!.productPrice!;

              if (cp.type == 'variable') {
                tp.availableVariations?.forEach((elvar) {
                  if (elvar.variationId == cp.variantId) {
                    cp.productPrice = elvar.displayPrice;
                    cp.productRegPrice = elvar.displayRegularPrice.toString();
                    cp.stockStatus =
                        elvar.isInStock! ? 'instock' : 'outofstock';
                    cp.productStock = elvar.maxQty;
                    if (cp.cartQuantity! > cp.productStock!) {
                      cp.cartQuantity = 1;
                    }
                    cp.priceTotal = cp.cartQuantity! * elvar.displayPrice;

                    printLog(
                        "Variable ${cp.variantId} ${cp.productName} ${cp.stockStatus} ${cp.productStock}");
                  }
                });
              }
              if (cp.stockStatus == 'outofstock' || cp.productStock == 0) {
                // cp.isProductAvailable = false;
                cp.isSelected = false;
              } else {
                // cp.isProductAvailable = true;
                cp.isSelected = true;
              }
            }
          });
        });

        _temp = cartProduct;

        isLoading = false;
        notifyListeners();
        printLog(result.toString());
      });
      return _temp!;
    } catch (e) {
      printLog(e.toString(), name: 'Load Cart Error');
      isLoading = false;
      notifyListeners();
      return _temp!;
    }
  }

  resetPage() {
    orderPage = 1;
    listOrder = [];
    tempOrder = [];
    isLoading = true;
    notifyListeners();
  }
}
