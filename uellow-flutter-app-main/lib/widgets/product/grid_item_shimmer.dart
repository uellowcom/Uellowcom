import 'package:flutter/material.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:shimmer/shimmer.dart';

class GridItemShimmer extends StatelessWidget {
  final int? i, itemCount;

  GridItemShimmer({this.i, this.itemCount});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 250,
      decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(8)),
      child: Shimmer.fromColors(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: double.infinity,
                height: 180,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(5),
                  color: Colors.white,
                ),
              ),
              Container(
                margin: EdgeInsets.symmetric(vertical: 3, horizontal: 5),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 100,
                      height: 10,
                      color: Colors.white,
                    ),
                    Container(
                      height: 5,
                    ),
                    Row(
                      children: [
                        Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(5),
                            color: secondaryColor,
                          ),
                          padding:
                              EdgeInsets.symmetric(vertical: 3, horizontal: 7),
                          child: Container(
                            width: 5,
                            height: 9,
                            color: Colors.white,
                          ),
                        ),
                        Container(
                          width: 5,
                        ),
                        Container(
                          width: 50,
                          height: 8,
                          color: Colors.white,
                        ),
                      ],
                    ),
                    FittedBox(
                      child: Container(
                        height: 10,
                        width: 30,
                        color: Colors.white,
                      ),
                    ),
                    Container(
                      height: 5,
                    ),
                    Container(
                      width: 50,
                      height: 8,
                      color: Colors.white,
                    ),
                  ],
                ),
              )
            ],
          ),
          baseColor: Colors.grey[300]!,
          highlightColor: Colors.grey[100]!),
    );
  }
}
