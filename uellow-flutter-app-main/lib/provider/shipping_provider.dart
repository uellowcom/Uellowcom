import 'dart:convert';

import 'package:flutter/cupertino.dart';

import 'package:http/http.dart' as http;
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/models/shipping_ali_model.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

class ShippingProvider with ChangeNotifier {
  bool? loading = false;
  ShippingAli? shippingAli;

  Future<bool> shippingAliWoo(context,
      {String? productId,
      String? minPrice,
      String? maxPrice,
      String? from,
      String? to}) async {
    bool? _isValid = false;
    try {
      loading = true;
      String? _token = '8bc1d3c5-88c1-4245-ba21-68db71204cfd';
      String? _version = '1.20';
      String? _lang = 'en';
      String? _curr = 'USD';

      var request;

      request = await http.get(Uri.parse(
          'https://api.ali2woo.com/v1/get_shipping_info.php?token=$_token&version=$_version&lang=$_lang&curr=$_curr&product_id=$productId&quantity=1&country_code=$to&country_code_from=$from&min_price=$minPrice&max_price=$maxPrice&lang_code=en_GB'));

      if (request.statusCode == 200) {
        shippingAli = new ShippingAli.fromJson(json.decode(request.body));
        _isValid = true;
        loading = false;
        notifyListeners();
      } else {
        print(request.body.toString());
        _isValid = false;
        loading = false;
        notifyListeners();
      }
      return _isValid;
    } catch (e) {
      printLog(e.toString(), name: "Catch Error Shipping");
      _isValid = true;
      loading = false;
      notifyListeners();
      return _isValid;
    }
  }

  Future checkShipping(BuildContext context, ProductModel productModel,
      {String? to = ''}) async {
    final selectedCountry =
        Provider.of<HomeProvider>(listen: false, context).selectedCountries;
    if (selectedCountry != null) {
      to = selectedCountry;
    } else {
      to = productModel.countryTo;
    }
    context.read<HomeProvider>().changeCountries(to);

    if (productModel.shippingPrice != null) {
      if (productModel.type == 'simple') {
        await shippingAliWoo(context,
            from: productModel.countryFrom,
            to: to!.isEmpty ? productModel.countryTo : to,
            maxPrice:
                roundDouble(productModel.productPrice!, context).toString(),
            minPrice:
                roundDouble(productModel.productPrice!, context).toString(),
            productId: productModel.idAliProduct);
      } else {
        await shippingAliWoo(context,
            from: productModel.countryFrom,
            to: to!.isEmpty ? productModel.countryTo : to,
            maxPrice: roundDouble(productModel.variationPrices!.last, context)
                .toString(),
            minPrice:
                roundDouble(productModel.productPrice!, context).toString(),
            productId: productModel.idAliProduct);
      }
    }
  }
}
