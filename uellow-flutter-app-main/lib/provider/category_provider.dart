import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart';
import 'package:nyoba/models/categories_model.dart';
import 'package:nyoba/models/filter_data_model.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'dart:convert';
import 'package:nyoba/services/categories_api.dart';
import 'package:nyoba/services/product_api.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

class CategoryProvider with ChangeNotifier {
  CategoriesModel? category;
  bool loading = true;
  bool loadingAll = true;

  bool loadingSub = false;
  bool loadingFilter = false;

  List<CategoriesModel> categories = [];
  List<ProductCategoryModel> productCategories = [];

  List<AllCategoriesModel> allCategories = [];
  List<AllCategoriesModel> subAllCategories = [];
  List<ProductCategoryModel> subCategories = [];
  List<PopularCategoriesModel> popularCategories = [];
  int? currentSelectedCategory;
  int? currentSelectedCountSub;
  int? currentPage;

  List<ProductModel> listProductCategory = [];
  List<ProductModel> listTempProduct = [];
  FilterDataModel? filterDataModel;
  bool? isFilterSelected = false;

  // final HomeProvider homeProvider = HomeProvider();
  // final ProductProvider productProvider = ProductProvider();

  CategoryProvider() {
    // fetchCategories();
    // fetchProductCategories();
  }

  Future<bool> fetchCategories(BuildContext context) async {
    await CategoriesAPI().fetchCategories(context: context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);

        for (Map item in responseJson) {
          categories.add(CategoriesModel.fromJson(item));
        }
        categories.add(new CategoriesModel(
            image: 'images/lobby/viewMore.png',
            categories: null,
            id: null,
            titleCategories: 'View More'));
        loading = false;
        notifyListeners();
      } else {
        loading = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchProductCategories(BuildContext context) async {
    await CategoriesAPI().fetchProductCategories(context: context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);
        productCategories.add(
            ProductCategoryModel(id: 0, image: "", name: "All", slug: "all"));
        for (Map item in responseJson) {
          productCategories.add(ProductCategoryModel.fromJson(item));
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

  Future<bool> fetchAllCategories(BuildContext context, bool isFromSplash,
      {int? count, bool isFromSub = false}) async {
    var result;
    loadingAll = true;
    await CategoriesAPI()
        .fetchAllCategories(context, isFromSplash, count: count)
        .then((data) {
      result = data;
      printLog("${jsonEncode(result)}", name: "hasil fetch category");
      if (isFromSub == true) {
        subAllCategories.clear();
        for (Map item in result) {
          subAllCategories.add(AllCategoriesModel.fromJson(item));
        }
      } else {
        allCategories.clear();
        for (Map item in result) {
          allCategories.add(AllCategoriesModel.fromJson(item));
        }
      }
      loadingAll = false;
      loading = false;
      notifyListeners();
    });
    return true;
  }

  resetSubAllCategories() {
    subAllCategories.clear();
    notifyListeners();
  }

  Future<bool> fetchSubCategories(
      int? parent, page, BuildContext context) async {
    loadingSub = true;
    await CategoriesAPI()
        .fetchProductCategories(parent: parent, page: page, context: context)
        .then((data) {
      if (data != null) {
        // final responseJson = json.decode(data.body);
        final responseJson = data;
        printLog("${jsonEncode(responseJson)} response subcategories");
        if (page == 1) {
          subCategories.clear();
        }

        for (Map item in responseJson) {
          subCategories.add(ProductCategoryModel.fromJson(item));
        }
        loadingSub = false;
        notifyListeners();
      } else {
        loadingSub = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchPopularCategories(BuildContext context) async {
    loadingSub = true;
    await CategoriesAPI().fetchPopularCategories(context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);
        printLog("${jsonEncode(responseJson)}");
        popularCategories.clear();
        for (Map item in responseJson) {
          popularCategories.add(PopularCategoriesModel.fromJson(item));
        }
        loadingSub = false;
        notifyListeners();
      } else {
        loadingSub = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchProductsCategory(String category, BuildContext context,
      {int page = 1}) async {
    loadingSub = true;
    String country = base64Encode(
        utf8.encode(context.read<ProductProvider>().currentPosition));
    notifyListeners();
    try {
      await ProductAPI()
          .fetchProduct(
        category: category,
        page: page,
        perPage: 5,
        context: context,
        country: country,
      )
          .then((data) {
        if (data != null) {
          final responseJson = data;

          listTempProduct.clear();
          if (page == 1) {
            listProductCategory.clear();
          }

          int count = 0;

          for (Map item in responseJson) {
            listProductCategory.add(ProductModel.fromJson(item));
            count++;
          }

          if (count >= 5) {
            listProductCategory.add(ProductModel());
          }

          // loadingSub = false;
          // notifyListeners();
        } else {
          // loadingSub = false;
          // notifyListeners();
        }
      });
      loadingSub = false;
      notifyListeners();
    } catch (e) {
      printLog(e.toString());
      loadingSub = false;
      notifyListeners();
    }

    return true;
  }

  Future<bool> fetchFilterData(String category, BuildContext context) async {
    print(category);
    loadingFilter = true;
    await ProductAPI().filterData(category, context).then((data) {
      if (data != null) {
        final responseJson = data;
        // printLog("${jsonEncode(responseJson)}", name: "response filter");
        filterDataModel = FilterDataModel.fromJson(responseJson);
        loadingFilter = false;
        notifyListeners();
      } else {
        loadingFilter = false;
        notifyListeners();
      }
    });
    return true;
  }

  checkFilter(FilterDataModel filterData) {
    isFilterSelected = false;
    filterData.dataFilter!.forEach((element) {
      List<TermFilter> termFilter = element.termFilter;
      termFilter.forEach((e) {
        if (e.isSelected == true) {
          isFilterSelected = true;
        }
      });
    });
    notifyListeners();
  }

  resetFilter(FilterDataModel filterData) {
    filterData.dataFilter!.forEach((element) {
      List<TermFilter> termFilter = element.termFilter;
      termFilter.forEach((e) {
        if (e.isSelected == true) {
          e.isSelected = false;
        }
      });
    });
    notifyListeners();
  }

  reset() {
    isFilterSelected = false;
    notifyListeners();
  }
}
