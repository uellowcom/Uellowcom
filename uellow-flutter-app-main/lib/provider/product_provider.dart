import 'dart:convert';
import 'dart:io';

import 'package:flutter/cupertino.dart';
import 'package:image_picker/image_picker.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/models/attribute_filter_model.dart';
import 'package:nyoba/models/countries_model.dart';
import 'package:nyoba/models/filter_data_model.dart';
import 'package:nyoba/models/product_extend_model.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/models/shipping_method_model.dart';
import 'package:nyoba/models/variation_model.dart';
import 'package:nyoba/provider/urlProvider.dart';
import 'package:nyoba/services/product_api.dart';
import 'package:nyoba/services/review_api.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import 'home_provider.dart';

class ProductProvider with ChangeNotifier {
  bool loadingFeatured = false;
  bool loadingBestDeals = false;
  bool loadingNew = false;

  bool loadingExtends = true;
  bool loadingSpecial = true;
  bool loadingBest = true;
  bool loadingRecommendation = true;
  bool loadingDetail = true;
  bool loadingCategory = false;
  bool loadingBrand = false;
  bool loadingMore = true;

  bool loadingReview = false;
  bool loadAddReview = false;
  bool loadingRecent = false;

  bool loadingFormProduct = false;
  bool isFormSucces = false;

  String? message;

  List<ProductModel> listFeaturedProduct = [];
  List<ProductModel> listMoreFeaturedProduct = [];

  List<ProductModel> listBestDeal = [];

  List<ProductModel> listNewProduct = [];
  List<ProductModel> listMoreNewProduct = [];

  List<ProductModel> listSpecialProduct = [];
  List<ProductModel> listMoreSpecialProduct = [];

  List<ProductModel> listBestProduct = [];
  List<ProductModel> listRecentProduct = [];
  List<ProductModel> listRecommendationProduct = [];
  List<ProductModel> listCategoryProduct = [];
  List<ProductModel> listBrandProduct = [];

  List<ProductModel> listMoreExtendProduct = [];
  List<ProductModel> listTempProduct = [];

  // List<ReviewHistoryModel> listReviewLimit = [];

  List<AttributeFilter>? attributeFilter = [];
  String? paramAttrFilter;

  late ProductExtendModel productSpecial;
  late ProductExtendModel productBest;
  late ProductExtendModel productRecommendation;

  String? productRecent;

  ProductModel? productDetail;

  // Image Review Product
  List<XFile>? imageFileList = [];
  List<TextEditingController>? textImageList = [];
  List<XFile>? imageFileInvalidList = [];
  List<XFile>? imageFileVideoList = [];
  List<TextEditingController>? textVideoList = [];
  List<XFile>? imageFileInvalidVideoList = [];
  List<String>? imageBase64 = [];

  final ImagePicker _picker = ImagePicker();
  dynamic pickImageError;

  final HomeProvider homeProvider = HomeProvider();
  String currentPosition = "";

  bool isLastBestDeals = false;

  ProductProvider(BuildContext context) {
    fetchFeaturedProducts(context: context);
    fetchExtendProducts('our_best_seller', context);
    fetchExtendProducts('special', context);
    fetchExtendProducts('recomendation', context);
  }

  fetchFormProduct(
      {required String name,
      required String email,
      required String subject,
      required String message,
      int? id,
      required BuildContext context}) async {
    loadingFormProduct = true;
    notifyListeners();
    await ProductAPI()
        .fetchProductForm(
            name: name,
            email: email,
            subject: subject,
            message: message,
            id: id,
            context: context)
        .then((data) {
      if (data != null) {
        if (data['status'] == 'success') {
          printLog("$data", name: "DATA FORM");
          isFormSucces = true;
        } else {
          isFormSucces = false;
          printLog("gagal");
        }
        loadingFormProduct = false;
        notifyListeners();
      } else {
        loadingFormProduct = false;
        notifyListeners();
      }
    });
  }

  Future<List<String>> generateImageBase64() async {
    loadAddReview = true;
    List<String> _temp = [];
    if (imageFileList!.isNotEmpty) {
      imageBase64 = [];

      for (var element in imageFileList!) {
        final file = File(element.path);
        final bytes = file.readAsBytesSync().lengthInBytes;
        final kb = bytes / 1024;
        List<int> imageBytes = await file.readAsBytes();
        String base64Image = base64Encode(imageBytes);
        printLog(kb.toString(), name: 'File Size KB');
        imageBase64!.add(base64Image);
        printLog(imageBase64.toString(), name: 'ListBase64');
      }
      _temp = imageBase64!;
      printLog(_temp.toString(), name: 'Temps');
    }
    notifyListeners();
    return _temp;
  }

  Future<void> onImageButtonPressed(
      BuildContext context, ImageSource source, bool image) async {
    try {
      if (image) {
        final maxSize =
            Provider.of<HomeProvider>(context, listen: false).photoMaxSize;
        final maxFiles =
            Provider.of<HomeProvider>(context, listen: false).photoMaxFiles;

        imageFileInvalidList = [];

        final List<XFile>? pickedFileList = await _picker.pickMultiImage();

        pickedFileList!.forEach((element) async {
          final file = File(element.path);
          final bytes = file.readAsBytesSync().lengthInBytes;
          final kb = bytes / 1024;

          if (kb < maxSize!) {
            printLog(imageFileList!.length.toString());
            if (imageFileList!.length < maxFiles!) {
              imageFileList!.add(element);
            } else {
              imageFileInvalidList!.add(element);
            }
          } else {
            imageFileInvalidList!.add(element);
          }
          textImageList?.add(new TextEditingController());
        });

        printLog("${imageFileList!.length}", name: 'Image Total');
        notifyListeners();
      } else if (!image) {
        final maxSize =
            Provider.of<HomeProvider>(context, listen: false).photoMaxSize;
        final maxFiles =
            Provider.of<HomeProvider>(context, listen: false).photoMaxFiles;

        imageFileInvalidVideoList = [];

        final XFile? pickedFile = await _picker.pickVideo(source: source);

        final file = File(pickedFile!.path);
        final bytes = file.readAsBytesSync().lengthInBytes;
        final kb = bytes / 1024;

        if (kb < maxSize!) {
          printLog(imageFileVideoList!.length.toString());
          if (imageFileVideoList!.length < maxFiles!) {
            imageFileVideoList!.add(pickedFile);
          } else {
            imageFileInvalidVideoList!.add(pickedFile);
          }
        } else {
          imageFileInvalidVideoList!.add(pickedFile);
        }
        textVideoList?.add(new TextEditingController());

        printLog("${imageFileVideoList!.length}", name: 'Video Total');
        notifyListeners();
      }
    } catch (e) {
      pickImageError = e;
      notifyListeners();
    }
  }

  Future<bool> fetchFeaturedProducts(
      {int page = 1,
      String? order = '',
      String? orderBy = '',
      required BuildContext context}) async {
    loadingFeatured = true;
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchMoreProduct(
      page: page,
      order: order!,
      orderBy: orderBy,
      featured: true,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        if (page == 1) {
          listFeaturedProduct.clear();
          listMoreFeaturedProduct.clear();
        }

        for (Map item in responseJson) {
          if (page == 1) {
            listFeaturedProduct.add(ProductModel.fromJson(item));
          }
          listMoreFeaturedProduct.add(ProductModel.fromJson(item));
        }

        loadingFeatured = false;
        notifyListeners();
      } else {
        loadingFeatured = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchNewProducts(String category,
      {int page = 1, required BuildContext context}) async {
    loadingNew = true;
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchProduct(
      category: category,
      page: page,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;
        if (page == 1) {
          listNewProduct.clear();
          listMoreNewProduct.clear();
        }
        for (Map item in responseJson) {
          if (page == 1) {
            listNewProduct.add(ProductModel.fromJson(item));
            listMoreNewProduct.add(ProductModel.fromJson(item));
          } else {
            listMoreNewProduct.add(ProductModel.fromJson(item));
          }
        }
        loadingNew = false;
        notifyListeners();
      } else {
        loadingNew = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchExtendProducts(type, BuildContext context) async {
    await ProductAPI().fetchExtendProduct(type, context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);

        for (Map item in responseJson) {
          if (type == 'our_best_seller') {
            productBest = ProductExtendModel.fromJson(item);
          } else if (type == 'special') {
            productSpecial = ProductExtendModel.fromJson(item);
          } else if (type == 'recomendation') {
            productRecommendation = ProductExtendModel.fromJson(item);
          }
        }
        notifyListeners();
      } else {
        notifyListeners();
        print("Load Extend Failed");
      }
    });
    return true;
  }

  Future<bool> fetchSpecialProducts(
      String productId, BuildContext context) async {
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchProduct(
      include: productId,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;
        // printLog(responseJson.toString(), name: 'Special Product');

        listSpecialProduct.clear();
        for (Map item in responseJson) {
          listSpecialProduct.add(ProductModel.fromJson(item));
        }
        loadingSpecial = false;
        notifyListeners();
      } else {
        print("Load Special Failed");
        loadingSpecial = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchBestProducts(String productId, BuildContext context) async {
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchProduct(
      include: productId,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        // printLog(responseJson.toString(), name: 'Best Product');
        listBestProduct.clear();
        for (Map item in responseJson) {
          listBestProduct.add(ProductModel.fromJson(item));
        }
        loadingBest = false;
        notifyListeners();
      } else {
        print("Load Best Failed");
        loadingBest = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchRecentProducts(BuildContext context) async {
    await ProductAPI().fetchRecentViewProducts(context).then((data) {
      if (data["products"].toString().isNotEmpty) {
        productRecent = data["products"];
        this.fetchListRecentProducts(productRecent, context);
      }
      notifyListeners();
    });
    return true;
  }

  Future<bool> fetchListRecentProducts(productId, BuildContext context) async {
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchMoreProduct(
      include: productId,
      order: 'desc',
      orderBy: 'popularity',
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        listRecentProduct.clear();
        for (Map item in responseJson) {
          listRecentProduct.add(ProductModel.fromJson(item));
        }

        loadingRecent = false;
        notifyListeners();
      } else {
        print("Load Recent Failed");
        loadingRecent = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> hitViewProducts(productId, BuildContext context) async {
    await ProductAPI().hitViewProductsAPI(productId, context).then((data) {
      notifyListeners();
    });
    return true;
  }

  Future<bool> fetchRecommendationProducts(
      String productId, BuildContext context) async {
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchProduct(
      include: productId,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        listRecommendationProduct.clear();
        for (Map item in responseJson) {
          listRecommendationProduct.add(ProductModel.fromJson(item));
        }
        loadingRecommendation = false;
        notifyListeners();
      } else {
        print("Load Failed");
        loadingRecommendation = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<ProductModel?> fetchProductDetail(
      String? productId, BuildContext context) async {
    loadingDetail = true;
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchDetailProduct(
      productId: productId,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        productDetail = ProductModel.fromJson(responseJson.first);
        printLog("${jsonEncode(productDetail)}",
            name: "Product detail provider");
        loadingDetail = false;
        notifyListeners();
      } else {
        print("Load Failed");
        loadingDetail = false;
        notifyListeners();
      }
    });
    return productDetail;
  }

  Future<ProductModel?> fetchProductDetailSlug(
      String? slug, BuildContext context) async {
    loadingDetail = true;
    await ProductAPI().fetchDetailProductSlug(slug, context).then((data) {
      if (data != null) {
        final responseJson = data;

        for (Map item in responseJson) {
          productDetail = ProductModel.fromJson(item);
        }

        notifyListeners();
      } else {
        print("Load Failed");
        notifyListeners();
      }
    });
    return productDetail;
  }

  Future<Map<String, dynamic>?> checkVariation(
      {productId, list, required BuildContext context}) async {
    var result;
    await ProductAPI()
        .checkVariationProduct(productId, list, context)
        .then((data) {
      result = data;
      notifyListeners();
      printLog("${jsonEncode(result)}", name: "response check variation");
    });
    return result;
  }

  Future<bool> fetchCategoryProduct(String category, int page, String order,
      String orderBy, BuildContext context) async {
    loadingCategory = true;
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchBrandProduct(
      category: category,
      order: order,
      orderBy: orderBy,
      page: page,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        if (page == 1) {
          listCategoryProduct.clear();
        }
        for (Map item in responseJson) {
          listCategoryProduct.add(ProductModel.fromJson(item));
        }

        loadingCategory = false;
        notifyListeners();
      } else {
        loadingCategory = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchBrandProductBySlug(
      {String? category,
      int? page,
      String? order,
      String? orderBy,
      String? attribute,
      String? slug,
      required BuildContext context}) async {
    loadingBrand = true;
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchBrandProduct(
      page: page,
      attributeFilter: attributeFilter,
      slug: slug,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        listTempProduct.clear();
        if (page == 1) {
          listBrandProduct.clear();
        }
        for (Map item in responseJson) {
          listBrandProduct.add(ProductModel.fromJson(item));
        }
        for (int i = 0; i < listBrandProduct.length; i++) {
          if (listBrandProduct[i].type == 'variable') {
            for (int j = 0;
                j < listBrandProduct[i].availableVariations!.length;
                j++) {
              if (listBrandProduct[i]
                          .availableVariations![j]
                          .displayRegularPrice -
                      listBrandProduct[i]
                          .availableVariations![j]
                          .displayPrice !=
                  0) {
                double temp = ((listBrandProduct[i]
                                .availableVariations![j]
                                .displayRegularPrice -
                            listBrandProduct[i]
                                .availableVariations![j]
                                .displayPrice) /
                        listBrandProduct[i]
                            .availableVariations![j]
                            .displayRegularPrice) *
                    100;
                if (listBrandProduct[i].discProduct! < temp) {
                  listBrandProduct[i].discProduct = temp;
                }
              }
            }
          }
        }

        loadingBrand = false;
        notifyListeners();
      } else {
        loadingBrand = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<bool> fetchBrandProduct(
      {String? category,
      int? page,
      String? order,
      String? orderBy,
      required BuildContext context}) async {
    loadingBrand = true;
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchBrandProduct(
      category: category,
      order: order,
      orderBy: orderBy,
      page: page,
      attributeFilter: attributeFilter,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        listTempProduct.clear();
        if (page == 1) {
          listBrandProduct.clear();
        }
        for (Map item in responseJson) {
          listBrandProduct.add(ProductModel.fromJson(item));
        }

        loadingBrand = false;
        notifyListeners();
      } else {
        loadingBrand = false;
        notifyListeners();
      }
    });
    return true;
  }

  // Future<Map<String, dynamic>?> addReview(context,
  //     {productId, review, rating}) async {
  //   loadAddReview = !loadAddReview;
  //   var result;

  //     printLog(imageBase64.toString(), name: 'Image Base64');

  //   await ReviewAPI().inputReview(productId, review, rating, image: imageBase64).then((data) {
  //     result = data;
  //     printLog(result.toString());

  //     if (result['status'] == 'success') {
  //       var _ratingCountTemp = (productDetail!.ratingCount! + 1);
  //       var _avgTemp = ((double.parse(productDetail!.avgRating!) *
  //                   productDetail!.ratingCount!) +
  //               rating) /
  //           _ratingCountTemp;

  //       productDetail!.ratingCount = _ratingCountTemp;
  //       productDetail!.avgRating = _avgTemp.toStringAsFixed(2);

  //       loadAddReview = !loadAddReview;

  //       snackBar(context, message: 'Successfully add your product review');
  //     } else {
  //       loadAddReview = !loadAddReview;

  //       snackBar(context, message: 'Error, ${result['message']}');
  //     }

  //     notifyListeners();
  //     printLog(result.toString());
  //   });
  //   return result;
  // }

  Future<Map<String, dynamic>?> addReview(context,
      {productId, review, rating, reviewTitle, name, email}) async {
    loadAddReview = true;
    var result;
    notifyListeners();
    try {
      printLog(imageBase64.toString(), name: 'Image Base64');
      List<File> listTemp = [];
      String textTemp = "";
      textImageList!.forEach((element) {
        if (textTemp == "") {
          if (element.text.isNotEmpty) textTemp += element.text;
          if (element.text.isEmpty) textTemp += "{empty}";
        } else {
          if (element.text.isNotEmpty) textTemp += "|${element.text}";
          if (element.text.isEmpty) textTemp += "|{empty}";
        }
      });
      textVideoList!.forEach((element) {
        if (textTemp == "") {
          if (element.text.isNotEmpty) textTemp += element.text;
          if (element.text.isEmpty) textTemp += "{empty}";
        } else {
          if (element.text.isNotEmpty) textTemp += "|${element.text}";
          if (element.text.isEmpty) textTemp += "|{empty}";
        }
      });
      imageFileList!.forEach((element) {
        listTemp.add(File(element.path));
      });
      imageFileVideoList!.forEach((element) {
        listTemp.add(File(element.path));
      });
      await ReviewAPI()
          .inputReview(productId, review, rating, reviewTitle, textTemp,
              image: listTemp, name: name, email: email, context: context)
          .then((data) {
        result = data;
        printLog(json.encode(result), name: "Result");
        if (result['status'] == 'success') {
          imageBase64 = [];
          Navigator.pop(context);
          snackBar(context,
              message:
                  '${AppLocalizations.of(context)!.translate('success_review')}');
        } else {
          Navigator.pop(context);
          snackBar(context, message: 'Error, ${result['message']}');
        }
        loadAddReview = false;

        notifyListeners();
        printLog(result.toString());
      });
      return result;
    } catch (e) {
      result = {"message": "$e"};
      printLog(e.toString());
      loadAddReview = false;
      notifyListeners();
      return result;
    }
  }

  Future<bool> fetchMoreExtendProduct(String? productId,
      {int? page,
      required String order,
      String? orderBy,
      required BuildContext context}) async {
    loadingMore = true;
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchMoreProduct(
      include: productId,
      page: page,
      order: order,
      orderBy: orderBy,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        listTempProduct.clear();
        if (page == 1) {
          listMoreExtendProduct.clear();
        }
        for (Map item in responseJson) {
          listMoreExtendProduct.add(ProductModel.fromJson(item));
        }

        loadingMore = false;
        notifyListeners();
      } else {
        print("Load Failed");
        loadingMore = false;
        notifyListeners();
      }
    });
    return true;
  }

  Future<VariationModel?> fetchProductVariations(
      String productId, BuildContext context) async {
    loadingDetail = true;
    VariationModel? variations;
    try {
      await ProductAPI()
          .productVariations(productId: productId, context: context)
          .then((data) {
        if (data.statusCode == 200) {
          final responseJson = json.decode(data.body);

          for (Map item in responseJson) {
            variations = VariationModel.fromJson(item);
          }

          notifyListeners();
        } else {
          print("Load Failed");
          notifyListeners();
        }
      });
      return variations;
    } catch (e) {
      print("Load Failed");
      notifyListeners();
      return variations;
    }
  }

  Future<bool> fetchBestDeals(String category,
      {int page = 1,
      String? order = 'desc',
      String? orderBy = 'rand',
      required BuildContext context}) async {
    loadingBestDeals = true;
    printLog("load best deals");
    String country = base64Encode(utf8.encode(currentPosition));
    await ProductAPI()
        .fetchMoreProduct(
      category: category,
      page: page,
      order: order!,
      orderBy: orderBy,
      context: context,
      country: country,
    )
        .then((data) {
      if (data != null) {
        final responseJson = data;

        if (page == 1) {
          listBestDeal.clear();
        }

        if (responseJson.length == 0) {
          isLastBestDeals = true;
          notifyListeners();
          return;
        }

        for (Map item in responseJson) {
          listBestDeal.add(ProductModel.fromJson(item));
        }

        loadingBestDeals = false;
        notifyListeners();
      } else {
        loadingBestDeals = false;
        notifyListeners();
      }
    });
    return true;
  }

  setAttributeFilter(FilterDataModel filter) {
    attributeFilter!.clear();
    filter.dataFilter!.forEach((element) {
      List<TermFilter> termFilter = element.termFilter;
      List<String> terms = [];
      termFilter.forEach((e) {
        if (e.isSelected!) {
          terms.add(e.nameTranslate!);
        }
      });
      if (terms.isNotEmpty) {
        attributeFilter!.add(new AttributeFilter(
            taxonomy: element.taxonomy,
            field: 'slug',
            operator: 'IN',
            terms: terms));
      }
    });
    notifyListeners();
  }

  bool loadingHistory = false;
  List<ProductModel> listHistoryProduct = [];

  Future<void> loadHistoryProduct(BuildContext context) async {
    loadingHistory = true;
    notifyListeners();
    await ProductAPI().fetchHistory(context).then((data) {
      printLog(json.encode(data), name: "Recently View");
      if (data != null) {
        listHistoryProduct.clear();
        data.forEach((v) {
          listHistoryProduct.add(ProductModel.fromJson(v));
        });
        loadingHistory = false;
        notifyListeners();
      }
    });
  }

  bool loadingShipping = false;
  List<ShippingMethodModel> shippingMethods = [];
  String responseShippingInfo = "";
  String responseShippingCountry = "";
  int selectedShipping = 0;

  setSelectedShipping(int val) {
    selectedShipping = val;
    notifyListeners();
  }

  Future<bool> getShippingMethod({
    String? productId = "",
    int? qty = 1,
    required BuildContext context,
    String? country,
  }) async {
    loadingShipping = true;
    bool _haveShipping = false;
    String currentCountry = context.read<ProductProvider>().currentPosition;
    notifyListeners();
    try {
      await ProductAPI()
          .fetchProductShippingMethod(
              country: country == null ? currentCountry : country,
              productId: productId,
              qty: qty,
              context: context)
          .then((data) {
        printLog("${jsonEncode(data)}", name: "RESPONSE FETCH SHIPPING METHOD");
        if (data != null) {
          if (data['status'] == "error") {
            responseShippingInfo = "";
            responseShippingCountry = "";
            shippingMethods = [];
            _haveShipping = false;
            loadingShipping = false;
            notifyListeners();
            return _haveShipping;
          }
          if (data['status'] == "success") {
            if (data['data']['shipping_methods'].isEmpty) {
              _haveShipping = true;
              loadingShipping = false;
              responseShippingCountry =
                  data['data']['country'].toString().toUpperCase();
              responseShippingInfo = data['data']['shipping_info'];
              notifyListeners();
              return _haveShipping;
            }
            responseShippingCountry =
                data['data']['country'].toString().toUpperCase();
            responseShippingInfo = "";
            shippingMethods = [];
            data['data']['shipping_methods'].forEach((v) {
              shippingMethods.add(ShippingMethodModel.fromJson(v));
            });
            selectedShipping = 0;
            _haveShipping = true;
            loadingShipping = false;
            notifyListeners();
          }
        }
      });
    } catch (e) {
      loadingShipping = false;
      printLog(e.toString());
      notifyListeners();
      return _haveShipping;
    }
    return _haveShipping;
  }

  bool loadingCartApply = false;

  Future<void> cartApplyShippingMethods(BuildContext context) async {
    await ProductAPI()
        .cartApplyShippingMethods(responseShippingCountry, context);
  }

  bool loading = false;
  List<CountriesModel> countries = [];
  CountriesModel? selectedCountry;

  Future<bool> fetchCountries(BuildContext context) async {
    final url = Provider.of<UrlProvider>(context, listen: false).baseAPI;
    loading = true;
    bool _isSuccess = false;
    try {
      var response = await url.getAsync('data/countries');

      countries = [];
      printLog("masuk " + response.statusCode.toString(), name: "country");
      if (response.statusCode == 200) {
        final responseJson = json.decode(response.body);

        for (Map item in responseJson) {
          countries.add(CountriesModel.fromJson(item));
        }
        if (countries.isNotEmpty) {
          Session.data.setString('countries', json.encode(countries));
        }
        loading = false;
        _isSuccess = true;
        notifyListeners();
      } else {
        loading = false;
        _isSuccess = false;
        notifyListeners();
      }
    } catch (e) {
      loading = false;
      _isSuccess = false;
      notifyListeners();
    }
    return _isSuccess;
  }

  setCountry(val) {
    if (Session.data.containsKey('countries')) {
      List<dynamic> temp = json.decode(Session.data.getString('countries')!);
      countries = temp.map((e) => CountriesModel.fromJson(e)).toList();
    }
    if (countries.isNotEmpty) {
      countries.forEach((element) {
        if (element.code == val) {
          selectedCountry = element;
          notifyListeners();
        }
      });
    }
    notifyListeners();
  }

  reset() {
    loadingBrand = true;
    attributeFilter = [];
    notifyListeners();
  }

  resetReview() {
    imageFileList = [];
    imageFileInvalidList = [];
    imageBase64 = [];
    notifyListeners();
  }
}
