import 'package:cached_network_image/cached_network_image.dart';
import 'package:card_swiper/card_swiper.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:nyoba/pages/category/brand_product_screen.dart';
import 'package:nyoba/pages/product/product_detail_screen.dart';
import 'package:nyoba/utils/utility.dart';

class BannerContainer extends StatefulWidget {
  final List<dynamic> dataSlider;
  final int dataSliderLength;
  final double contentHeight;
  final Widget loading;
  final bool? isFromCategory;

  BannerContainer(
      {required this.dataSliderLength,
      required this.contentHeight,
      required this.dataSlider,
      required this.loading,
      this.isFromCategory = false});

  @override
  State<BannerContainer> createState() => _BannerContainerState();
}

class _BannerContainerState extends State<BannerContainer> {
  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(10),
          ),
          height: widget.isFromCategory == true ? 75.h : 145.h,
          margin: EdgeInsets.all(10),
          child: Swiper(
            itemBuilder: (BuildContext context, int i) {
              var slide = widget.dataSlider[i];

              var imageSlider = slide.image;
              var product = slide.product;
              var linkTo = slide.linkTo;
              var name = slide.name;

              return InkWell(
                onTap: () {
                  if (product != null && linkTo == 'product') {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => ProductDetail(
                                  productId: product.toString(),
                                )));
                  } else if (linkTo == 'category') {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => BrandProducts(
                                  isNeedSub: true,
                                  withFilter: false,
                                  categoryId: product.toString(),
                                  brandName: name,
                                )));
                  }
                },
                child: CachedNetworkImage(
                  imageUrl: imageSlider,
                  placeholder: (context, url) => Container(
                      decoration: BoxDecoration(color: Colors.grey[300])),
                  errorWidget: (context, url, error) => Icon(Icons.error),
                  imageBuilder: (context, imageProvider) => Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(10),
                      image: DecorationImage(
                        image: imageProvider,
                        fit: BoxFit.fill,
                      ),
                    ),
                  ),
                ),
              );
            },
            itemCount: widget.dataSlider.length,
            viewportFraction: 1,
            autoplay: true,
            loop: true,
            scale: 0.8,
            autoplayDelay: 5500,
            duration: 2500,
            // pagination: SwiperPagination(
            //     margin: EdgeInsets.zero,
            //     builder: SwiperCustomPagination(builder: (context, config) {
            //       return Row(
            //         mainAxisAlignment: MainAxisAlignment.center,
            //         children: widget.dataSlider.asMap().entries.map((entry) {
            //           return Container(
            //             decoration: BoxDecoration(
            //                 shape: BoxShape.circle,
            //                 color: config.activeIndex == entry.key
            //                     ? primaryColor
            //                     : Colors.white),
            //           );
            //         }).toList(),
            //       );
            //     })),
            // pagination: SwiperPagination(
            //     margin: EdgeInsets.zero,
            //     builder: SwiperCustomPagination(builder: (context, config) {
            //       return ConstrainedBox(
            //         child: Row(
            //           children: <Widget>[
            //             Expanded(
            //               child: Align(
            //                 alignment: Alignment.center,
            //                 child: DotSwiperPaginationBuilder(
            //                         color: Colors.white,
            //                         activeColor: primaryColor,
            //                         size: 12.0,
            //                         activeSize: 12.0)
            //                     .build(context, config),
            //               ),
            //             )
            //           ],
            //         ),
            //         constraints: const BoxConstraints.expand(height: 35.0),
            //       );
            //     })),
          ),
        ),
      ],
    );
  }
}
