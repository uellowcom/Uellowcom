import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/shipping_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:nyoba/widgets/product/product_shipping_dialog.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../../app_localizations.dart';

class ProductDetailShipping extends StatelessWidget {
  final ProductModel? productModel;
  const ProductDetailShipping({Key? key, this.productModel}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final shipping = Provider.of<ShippingProvider>(listen: false, context);
    final selectedCountry =
        Provider.of<HomeProvider>(listen: false, context).selectedCountriesName;

    return InkWell(
      onTap: () async {
        return showDialog(
          context: context,
          builder: (ctx) => ProductShippingDialog(productModel: productModel),
        );
      },
      child: Container(
        padding: EdgeInsets.only(left: 15, right: 5, top: 10, bottom: 10),
        child: Column(
          children: [
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text(
                "Shipping:",
                style: TextStyle(fontWeight: FontWeight.w500),
              ),
              Icon(
                Icons.chevron_right,
                color: Colors.grey[400],
              )
            ]),
            shipping.loading!
                ? Shimmer.fromColors(
                    child: Container(
                      margin: EdgeInsets.only(right: 15),
                      width: double.infinity,
                      height: 40.h,
                      decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(10)),
                    ),
                    baseColor: Colors.grey[100]!,
                    highlightColor: Colors.grey[300]!)
                : shipping.shippingAli!.items!.isNotEmpty
                    ? Container(
                        margin: EdgeInsets.only(right: 15),
                        child: HtmlWidget(
                          shipping.shippingAli!.items!.first.freightLayout!
                              .displayShipping!
                              .join(", "),
                          textStyle: TextStyle(fontSize: responsiveFont(10)),
                        ),
                      )
                    : Container(
                        margin: EdgeInsets.only(right: 15),
                        child: Text(
                          selectedCountry != null
                              ? "${AppLocalizations.of(context)!.translate('cant_delivered')} $selectedCountry"
                              : "${AppLocalizations.of(context)!.translate('cant_delivered')} ${AppLocalizations.of(context)!.translate('selected_country')}",
                          style: TextStyle(fontWeight: FontWeight.w500),
                        ),
                      )
          ],
        ),
      ),
    );
  }
}
