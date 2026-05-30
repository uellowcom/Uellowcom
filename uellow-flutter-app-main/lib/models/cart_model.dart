class CartModel {
  // Model
  int? customerId;
  String? paymentMethod;
  String? paymentMethodTitle;
  bool? setPaid;
  String? status;
  String? token;
  List<CartProductItem>? listItem = [];
  List<CartCoupon>? listCoupon = [];

  CartModel({
    this.customerId,
    this.paymentMethod,
    this.paymentMethodTitle,
    this.setPaid,
    this.status,
    this.token,
    this.listItem,
    this.listCoupon,
  });

  Map toJson() => {
        'payment_method': paymentMethod,
        'payment_method_title': paymentMethodTitle,
        'set_paid': setPaid,
        'customer_id': customerId,
        'status': status,
        'token': token,
        'line_items': listItem,
        'coupon_lines': listCoupon,
      };
}

class CartProductItem {
  final int? productId;
  final int? quantity;
  final int? variationId;
  List<dynamic>? variation = [];
  final String? a2wShippingMethod;
  final List? a2wShipping;
  bool? codPayment;

  CartProductItem({
    this.productId,
    this.quantity,
    this.variationId,
    this.variation,
    this.a2wShippingMethod,
    this.a2wShipping,
    this.codPayment,
  });

  Map toJson() => {
        'product_id': productId,
        'quantity': quantity,
        'variation_id': variationId,
        'variation': variation,
        'a2w_shipping_method': a2wShippingMethod,
        'a2w_shipping': a2wShipping,
        'cod_payment': codPayment,
      };
}

class CartCoupon {
  final String? code;

  CartCoupon({this.code});

  Map toJson() => {
        'code': code,
      };
}
