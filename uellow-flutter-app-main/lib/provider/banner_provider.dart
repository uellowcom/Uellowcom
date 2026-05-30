import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:nyoba/models/banner_mini_model.dart';
import 'package:nyoba/models/banner_model.dart';
import 'dart:convert';
import 'package:nyoba/services/banner_api.dart';

class BannerProvider with ChangeNotifier {
  //Provider
  BannerModel? bannerModel;
  String? errorMessage;

  bool loading = true;
  bool loadingBlog = true;

  List<BannerModel> banners = [];
  List<BannerMiniModel> bannerSpecial = [];
  List<BannerMiniModel> bannerLove = [];

  BannerMiniModel bannerBlog = new BannerMiniModel();

  BannerProvider(BuildContext context) {
    fetchBannerBlog('true', context);
  }

  Future<bool> fetchBanner(BuildContext context) async {
    await BannerAPI().fetchBanner(context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);

        for (Map item in responseJson) {
          banners.add(BannerModel.fromJson(item));
        }
        loading = false;
        notifyListeners();
      } else {
        loading = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchBannerMini(BuildContext context) async {
    await BannerAPI().fetchMiniBanner(context: context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);

        bannerSpecial.clear();
        bannerLove.clear();
        for (Map item in responseJson) {
          if (item['type'] == 'Special Promo') {
            bannerSpecial.add(BannerMiniModel.fromJson(item));
          } else if (item['type'] == 'Love These Items') {
            bannerLove.add(BannerMiniModel.fromJson(item));
          }
        }
        loading = false;
        notifyListeners();
      } else {
        loading = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchBannerBlog(String blog, BuildContext context) async {
    await BannerAPI()
        .fetchMiniBanner(isBlog: blog, context: context)
        .then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);

        for (Map item in responseJson) {
          if (blog == 'true') {
            bannerBlog = BannerMiniModel.fromJson(item);
          }
        }
        loadingBlog = false;
        notifyListeners();
      } else {
        loadingBlog = false;
        notifyListeners();
      }
    });
    return true;
  }
}
