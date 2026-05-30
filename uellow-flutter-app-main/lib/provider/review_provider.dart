import 'dart:convert';

import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:nyoba/models/review_model.dart';
import 'package:nyoba/services/review_api.dart';
import 'package:nyoba/utils/utility.dart';

class ReviewProvider with ChangeNotifier {
  bool isLoading = false;
  bool isLoadingReview = false;

  List<ReviewHistoryModel> listHistory = [];
  List<NewReviewModel> listReviewLimit = [];
  List<NewReviewImage> listReviewImage = [];

  List<NewReviewModel> listReviewAllStar = [];
  List<NewReviewModel> listReviewFiveStar = [];
  List<NewReviewModel> listReviewFourStar = [];
  List<NewReviewModel> listReviewThreeStar = [];
  List<NewReviewModel> listReviewTwoStar = [];
  List<NewReviewModel> listReviewOneStar = [];

  Future<List?> fetchHistoryReview(BuildContext context) async {
    isLoading = !isLoading;
    var result;
    await ReviewAPI().historyReview(context).then((data) {
      result = data;

      listHistory.clear();

      printLog("${jsonEncode(result)}", name: "response review");

      for (Map item in result['review']) {
        listHistory.add(ReviewHistoryModel.fromJson(item));
      }

      isLoading = !isLoading;
      notifyListeners();
      printLog(result.toString());
    });
    return result;
  }

  fetchReviewProductLimit(productId, BuildContext context) async {
    isLoadingReview = true;
    var result;
    await ReviewAPI().limitReview(productId, context).then((data) {
      result = data;
      printLog("${jsonEncode(data)}", name: "result review");

      listReviewLimit.clear();
      listReviewImage.clear();

      printLog(result.toString());

      for (Map item in result['review']) {
        listReviewLimit.add(NewReviewModel.fromJson(item));
      }

      for (Map item in result['review_images']) {
        printLog("$item", name: "item in review images");
        listReviewImage.add(NewReviewImage.fromJson(item));
      }

      printLog("$listReviewImage", name: "list review image");

      isLoadingReview = false;
      notifyListeners();
      printLog(result.toString(), name: "result review");
    });
  }

  fetchReviewProduct(productId, BuildContext context) async {
    isLoadingReview = true;
    listReviewAllStar.clear();
    listReviewOneStar.clear();
    listReviewTwoStar.clear();
    listReviewThreeStar.clear();
    listReviewFourStar.clear();
    listReviewFiveStar.clear();
    var result;
    await ReviewAPI().productReview(productId, context).then((data) {
      result = data;
      printLog(result.toString());

      for (Map item in result['review']) {
        listReviewAllStar.add(NewReviewModel.fromJson(item));
      }

      listReviewAllStar.forEach((element) {
        printLog("${element.star}", name: "STAR");
        if (int.parse(double.parse(element.star!).round().toString()) == 5) {
          listReviewFiveStar.add(element);
        } else if (int.parse(double.parse(element.star!).round().toString()) ==
            4) {
          listReviewFourStar.add(element);
        } else if (int.parse(double.parse(element.star!).round().toString()) ==
            3) {
          listReviewThreeStar.add(element);
        } else if (int.parse(double.parse(element.star!).round().toString()) ==
            2) {
          listReviewTwoStar.add(element);
        } else if (int.parse(double.parse(element.star!).round().toString()) ==
            1) {
          listReviewOneStar.add(element);
        }
      });

      isLoadingReview = false;
      notifyListeners();
      printLog(result.toString());
    });
    // return result;
  }
}
