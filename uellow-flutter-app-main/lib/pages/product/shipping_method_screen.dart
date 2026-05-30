import 'package:flutter/material.dart';
import 'package:flutter/src/widgets/framework.dart';
import 'package:flutter/src/widgets/placeholder.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/models/shipping_method_model.dart';
import 'package:nyoba/pages/product/select_country_screen.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';

import '../../app_localizations.dart';
import '../../utils/currency_format.dart';

class ShippingMethodScreen extends StatefulWidget {
  ProductModel? productModel;
  ShippingMethodScreen({Key? key, this.productModel}) : super(key: key);

  @override
  State<ShippingMethodScreen> createState() => _ShippingMethodScreenState();
}

class _ShippingMethodScreenState extends State<ShippingMethodScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        elevation: 0,
        title: Text(
          "${AppLocalizations.of(context)!.translate('shipping_methods')}",
          style: TextStyle(color: Colors.black),
        ),
        leading: GestureDetector(
            onTap: () => Navigator.pop(context),
            child: Icon(
              Icons.arrow_back,
              color: Colors.black,
            )),
        backgroundColor: primaryColor,
      ),
      body: Consumer<ProductProvider>(
        builder: (context, value, child) {
          return Container(
            padding: EdgeInsets.all(10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("${AppLocalizations.of(context)!.translate('deliver_to')}",
                    style: TextStyle(fontWeight: FontWeight.w600)),
                SizedBox(
                  height: 10,
                ),
                GestureDetector(
                  onTap: () async {
                    await Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => SelectCountryScreen(),
                        ));
                    // )).then((val) {
                    //   printLog(val.toString());
                    //   if (val)
                    //     context.read<ProductProvider>().getShippingMethod(
                    //         context: context,
                    //         // country: value.selectedCountry!.code,
                    //         productId: widget.productModel!.id.toString(),
                    //         qty: widget.productModel!.cartQuantity);
                    // });
                    context.read<ProductProvider>().getShippingMethod(
                          context: context,
                          productId: widget.productModel!.id.toString(),
                          qty: widget.productModel!.cartQuantity,
                          country: context
                              .read<ProductProvider>()
                              .selectedCountry!
                              .code
                              .toString(),
                        );
                  },
                  child: Container(
                    padding: EdgeInsets.all(8),
                    decoration: BoxDecoration(
                        color: Colors.grey[200],
                        borderRadius: BorderRadius.circular(5)),
                    child: Row(
                      children: [
                        Icon(
                          Icons.location_on_outlined,
                          color: Colors.grey,
                        ),
                        SizedBox(
                          width: 10,
                        ),
                        Text(
                          "${value.selectedCountry!.name}",
                          style: TextStyle(fontSize: 13),
                        )
                      ],
                    ),
                  ),
                ),
                SizedBox(
                  height: 10,
                ),
                Text(
                    "${AppLocalizations.of(context)!.translate('shipping_methods')}",
                    style: TextStyle(fontWeight: FontWeight.w600)),
                SizedBox(
                  height: 10,
                ),
                value.loadingShipping
                    ? Shimmer.fromColors(
                        child: Container(
                          width: double.infinity,
                          height: 100,
                          decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(10),
                              color: Colors.white),
                        ),
                        baseColor: Colors.grey[300]!,
                        highlightColor: Colors.grey[100]!)
                    : value.responseShippingInfo != ""
                        ? Text.rich(
                            TextSpan(
                                style: TextStyle(color: Colors.grey),
                                children: [
                                  WidgetSpan(
                                      child: Icon(
                                    Icons.info_outline,
                                    size: 20,
                                    color: Colors.grey,
                                  )),
                                  TextSpan(
                                    text: " " + value.responseShippingInfo,
                                  )
                                ]),
                            // style: TextStyle(fontWeight: FontWeight.w600),
                          )
                        : Expanded(
                            child: ListView.builder(
                              itemBuilder: (context, index) {
                                return _buildShipping(
                                    value.shippingMethods[index], index, value);
                              },
                              itemCount: value.shippingMethods.length,
                              shrinkWrap: true,
                              physics: ScrollPhysics(),
                            ),
                          ),
              ],
            ),
          );
        },
      ),
    );
  }

  _buildShipping(
      ShippingMethodModel shipping, int i, ProductProvider productProvider) {
    return GestureDetector(
      onTap: () {
        productProvider.setSelectedShipping(i);
      },
      child: Container(
        padding: EdgeInsets.all(8),
        margin: EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
            border: Border.all(color: Colors.grey[400]!),
            borderRadius: BorderRadius.circular(10),
            color: Colors.grey[200]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              shipping.price! > 0
                  ? Text(
                      "${AppLocalizations.of(context)!.translate('delivery')}: ${stringToCurrency(shipping.price!, context)}",
                      style: TextStyle(fontWeight: FontWeight.w600),
                    )
                  : Text(
                      "${AppLocalizations.of(context)!.translate('free_delivery')}",
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
              Visibility(
                  visible: productProvider.selectedShipping == i,
                  child: Icon(
                    Icons.check_circle,
                    size: 20,
                  ))
            ],
          ),
          HtmlWidget(
            shipping.label ?? "-",
            textStyle:
                TextStyle(fontSize: responsiveFont(8), color: Colors.black),
          ),
          Container(
            padding: EdgeInsets.all(5),
            decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(5),
                color: Colors.grey[300]),
            child: Text(
              shipping.tracking!
                  ? "${AppLocalizations.of(context)!.translate('tracking_available')}"
                  : "${AppLocalizations.of(context)!.translate('tracking_not_available')}",
              style: TextStyle(fontSize: 10),
            ),
          )
        ]),
      ),
    );
  }
}
