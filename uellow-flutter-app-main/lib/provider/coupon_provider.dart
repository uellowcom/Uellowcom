import 'package:flutter/cupertino.dart';
import 'package:html_unescape/html_unescape.dart';
import 'package:nyoba/models/coupon_model.dart';
import 'dart:convert';
import 'package:nyoba/services/coupon_api.dart';
import 'package:nyoba/utils/utility.dart';

class CouponProvider with ChangeNotifier {
  bool loading = false;
  bool loadingUse = false;

  List<CouponModel> coupons = [];
  List<CouponModel> couponSearched = [];

  CouponModel? couponUsed;
  int? choosenIndex;
  String? searchCoupon;
  int? currentPage;

  Future<void> fetchCoupon(
      {page, required BuildContext context, String? productId = ""}) async {
    printLog("Fetching Coupon");
    loading = true;
    currentPage = page;
    coupons.clear();
    await CouponAPI()
        .fetchListCoupon(page, context, productId: productId)
        .then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);
        printLog("${jsonEncode(responseJson)}", name: "coupon");
        for (Map item in responseJson) {
          DateTime exp = DateTime.now();
          if (item['date_expires'] != null) {
            exp = DateTime.parse(item['date_expires']);
          }
          if (exp.isAfter(DateTime.now()) || item['date_expires'] == null) {
            coupons.add(CouponModel.fromJson(item));
          }
        }
        loading = false;
        notifyListeners();
      } else {
        coupons.clear();
        loading = false;
        notifyListeners();
      }
    });
    try {} catch (e) {
      printLog(e.toString(), name: "Error Coupons");
      coupons.clear();
      loading = false;
      notifyListeners();
    }
  }

  Future<void> useCoupon({i, search, required BuildContext context}) async {
    searchCoupon = search;
    CouponModel? _couponUsed;
    loadingUse = true;
    choosenIndex = i;
    notifyListeners();
    printLog("$search data apply coupon");
    await CouponAPI().searchCoupon(search, context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);
        printLog("${jsonEncode(responseJson)} response apply coupon");
        couponSearched.clear();
        for (Map item in responseJson) {
          couponSearched.add(CouponModel.fromJson(item));
        }

        if (couponSearched.isNotEmpty) {
          _couponUsed = couponSearched[0];
        }

        couponUsed = _couponUsed;
        printLog("coupon used: ${json.encode(couponUsed)}");
        print(couponUsed.toString());
        loadingUse = false;
        notifyListeners();
      } else {
        couponSearched.clear();

        loadingUse = false;
        notifyListeners();
      }
    });
  }

  Future<void> newUseCoupon(context,
      {List<SearchCouponModel>? products, String? code}) async {
    loadingUse = true;
    await CouponAPI()
        .newSearchCoupon(products: products, code: code, context: context)
        .then((data) {
      couponSearched.clear();
      if (data != null && data["code"] != "invalid_coupon") {
        couponUsed = CouponModel.fromJson(data);
        loadingUse = false;
        notifyListeners();
      } else {
        loadingUse = false;
        notifyListeners();
        snackBar(context, message: HtmlUnescape().convert(data["message"]));
      }
    });
  }
}
