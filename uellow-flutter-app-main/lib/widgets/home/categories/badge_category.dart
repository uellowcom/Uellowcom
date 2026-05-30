import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:nyoba/models/categories_model.dart';
import 'package:nyoba/pages/category/brand_product_screen.dart';
import 'package:nyoba/pages/category/category_screen.dart';
import 'package:nyoba/utils/utility.dart';

import '../../../app_localizations.dart';

class BadgeCategory extends StatelessWidget {
  final List<CategoriesModel> dataCategories;

  BadgeCategory(this.dataCategories);

  final int item = 6;
  @override
  Widget build(BuildContext context) {
    printLog(json.encode(dataCategories));
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 10),
      child: Wrap(
        spacing: 10,
        direction: Axis.horizontal,
        runSpacing: 5,
        children: [
          for (int i = 0; i < dataCategories.length; i++)
            category(context, dataCategories[i].categories.toString(),
                dataCategories[i].image!, i, dataCategories[i].titleCategories!)
        ],
      ),
    );
    // Container(
    //   padding: EdgeInsets.symmetric(horizontal: 15),
    //   alignment: Alignment.center,
    //   width: MediaQuery.of(context).size.width,
    //   height: MediaQuery.of(context).size.height / 6,
    //   child: ListView.separated(
    //       physics: BouncingScrollPhysics(),
    //       shrinkWrap: true,
    //       scrollDirection: Axis.horizontal,
    //       itemBuilder: (context, i) {
    //         var categories = dataCategories[i];
    //         var imageCategories = categories.image;
    //         var titleCategories = categories.titleCategories;
    //         var idCategories = categories.id;
    //         return Container(
    //             child: InkWell(
    //           onTap: () {
    //             if (idCategories == "view_more") {
    //               Navigator.push(
    //                   context,
    //                   MaterialPageRoute(
    //                       builder: (context) => CategoryScreen(
    //                             isFromHome: false,
    //                           )));
    //             } else {
    //               Navigator.push(
    //                   context,
    //                   MaterialPageRoute(
    //                       builder: (context) => BrandProducts(
    //                             withFilter: true,
    //                             categoryId:
    //                                 dataCategories[i].categories.toString(),
    //                             brandName: dataCategories[i].titleCategories,
    //                           )));
    //             }
    //           },
    //           child: Column(
    //             children: [
    //               itemCategory(imageCategories, i,
    //                   type: idCategories == "view_more" ? 'asset' : 'url'),
    //               Container(
    //                 height: 5,
    //               ),
    //               Flexible(
    //                 flex: 3,
    //                 child: Container(
    //                   child: Text(
    //                     idCategories != "view_more"
    //                         ? convertHtmlUnescape(titleCategories)
    //                         : AppLocalizations.of(context)!
    //                             .translate('view_more'),
    //                     textAlign: TextAlign.center,
    //                     maxLines: 2,
    //                     overflow: TextOverflow.ellipsis,
    //                     style: TextStyle(
    //                         fontSize: responsiveFont(11),
    //                         height: 1,
    //                         fontWeight: FontWeight.w600),
    //                   ),
    //                 ),
    //               )
    //             ],
    //           ),
    //         ));
    //       },
    //       separatorBuilder: (BuildContext context, int index) {
    //         return SizedBox(
    //           width: 15,
    //         );
    //       },
    //       itemCount: dataCategories.length),
    // );
  }

  Widget category(context, String idCategories, String imageCategories, int i,
      String titleCategories) {
    return Container(
        width: MediaQuery.of(context).size.width / 6,
        // height: MediaQuery.of(context).size.height / 7,
        // margin: EdgeInsets.only(bottom: 20),

        child: InkWell(
          onTap: () {
            if (idCategories == "view_more") {
              Navigator.push(
                  context,
                  MaterialPageRoute(
                      builder: (context) => CategoryScreen(
                            isFromHome: false,
                          )));
            } else {
              Navigator.push(
                  context,
                  MaterialPageRoute(
                      builder: (context) => BrandProducts(
                            isNeedSub: true,
                            withFilter: true,
                            categoryId: dataCategories[i].categories.toString(),
                            brandName: dataCategories[i].titleCategories,
                          )));
            }
          },
          child: Column(
            children: [
              itemCategory(imageCategories, i,
                  type: idCategories == "view_more" ? 'asset' : 'url'),
              Container(
                height: 5,
              ),
              Container(
                child: Text(
                  idCategories != "view_more"
                      ? convertHtmlUnescape(titleCategories)
                      : AppLocalizations.of(context)!.translate('view_more'),
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  style: TextStyle(
                    color: Colors.black,
                    fontSize: responsiveFont(7),
                  ),
                ),
              )
            ],
          ),
        ));
  }

  Widget itemCategory(String? image, int i, {String type = 'url'}) {
    return Container(
      height: 60,
      width: 60,
      padding: EdgeInsets.all(5),
      child: type == 'url'
          ? ClipRRect(
              borderRadius: BorderRadius.circular(200),
              child: Image.network(
                image!,
              ))
          : Image.asset(image!),
    );
  }
}
