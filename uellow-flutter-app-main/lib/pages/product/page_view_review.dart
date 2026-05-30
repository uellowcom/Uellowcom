import 'package:flutter/material.dart';
import 'package:flutter/src/widgets/framework.dart';
import 'package:flutter/src/widgets/placeholder.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';
import 'package:nyoba/models/review_model.dart';
import 'package:nyoba/utils/utility.dart';

class PageViewReview extends StatelessWidget {
  final List<NewReviewImage>? listReviewImage;
  final bool? isFromAllReviews;
  final bool? isGeneral;
  final String? image;
  final List<String>? allReviewsImages;
  const PageViewReview(
      {super.key,
      this.listReviewImage,
      this.isFromAllReviews = false,
      this.isGeneral = false,
      this.image,
      this.allReviewsImages});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: isFromAllReviews == true
          ? PageView.builder(
              itemCount: allReviewsImages!.length,
              itemBuilder: (context, index) {
                return Stack(
                  children: [
                    Center(
                      child: Image.network(
                        allReviewsImages![index],
                      ),
                    ),
                    Positioned(
                        top: 35.h,
                        right: 20.w,
                        child: GestureDetector(
                          onTap: () {
                            Navigator.pop(context);
                          },
                          child: Container(
                            padding: EdgeInsets.all(3),
                            decoration: BoxDecoration(
                                color: Colors.black38, shape: BoxShape.circle),
                            child: Icon(
                              Icons.close,
                              color: Colors.white,
                              size: 23,
                            ),
                          ),
                        )),
                  ],
                );
              },
            )
          : isGeneral == true
              ? PageView.builder(
                  itemCount: 1,
                  itemBuilder: (context, index) {
                    return Stack(
                      children: [
                        Center(
                          child: Image.network(
                            image!,
                          ),
                        ),
                        Positioned(
                            top: 35.h,
                            right: 20.w,
                            child: GestureDetector(
                              onTap: () {
                                Navigator.pop(context);
                              },
                              child: Container(
                                padding: EdgeInsets.all(3),
                                decoration: BoxDecoration(
                                    color: Colors.black38,
                                    shape: BoxShape.circle),
                                child: Icon(
                                  Icons.close,
                                  color: Colors.white,
                                  size: 23,
                                ),
                              ),
                            )),
                      ],
                    );
                  },
                )
              : PageView.builder(
                  itemCount: listReviewImage!.length,
                  itemBuilder: (context, index) {
                    return Stack(
                      children: [
                        Center(
                          child: Image.network(
                            listReviewImage![index].image!,
                          ),
                        ),
                        Positioned(
                            top: 35.h,
                            right: 20.w,
                            child: GestureDetector(
                              onTap: () {
                                Navigator.pop(context);
                              },
                              child: Container(
                                padding: EdgeInsets.all(3),
                                decoration: BoxDecoration(
                                    color: Colors.black38,
                                    shape: BoxShape.circle),
                                child: Icon(
                                  Icons.close,
                                  color: Colors.white,
                                  size: 23,
                                ),
                              ),
                            )),
                        Positioned(
                          bottom: 0,
                          child: Container(
                              padding: EdgeInsets.symmetric(
                                  horizontal: 15, vertical: 10),
                              width: MediaQuery.of(context).size.width,
                              color: Colors.black45,
                              child: HtmlWidget(
                                listReviewImage![index].content!,
                                textStyle: TextStyle(color: Colors.white),
                              )),
                        )
                      ],
                    );
                  },
                ),
    );
  }
}
