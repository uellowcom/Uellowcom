import 'package:flutter/material.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/shipping_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../../app_localizations.dart';

class ProductShippingDialog extends StatefulWidget {
  final ProductModel? productModel;
  const ProductShippingDialog({Key? key, this.productModel}) : super(key: key);

  @override
  State<ProductShippingDialog> createState() => _ProductShippingDialogState();
}

class _ProductShippingDialogState extends State<ProductShippingDialog> {
  String? _to;

  @override
  void initState() {
    super.initState();
    checkCountry();
  }

  checkCountry() {
    final selectedCountry =
        Provider.of<HomeProvider>(listen: false, context).selectedCountries;
    if (selectedCountry != null) {
      setState(() {
        _to = selectedCountry;
      });
    } else {
      setState(() {
        _to = widget.productModel!.countryTo;
      });
    }
  }

  checkAPI() async {
    final shipping = Provider.of<ShippingProvider>(listen: false, context);
    shipping
        .checkShipping(context, widget.productModel!, to: _to)
        .then((value) => this.setState(() {}));
  }

  @override
  Widget build(BuildContext context) {
    final double width = MediaQuery.of(context).size.width;
    final countries =
        Provider.of<HomeProvider>(listen: false, context).a2wCountries;
    final shipping = Provider.of<ShippingProvider>(listen: false, context);
    final selectedCountry =
        Provider.of<HomeProvider>(listen: false, context).selectedCountriesName;

    return AlertDialog(
      contentPadding: EdgeInsets.symmetric(horizontal: 15),
      clipBehavior: Clip.antiAliasWithSaveLayer,
      titlePadding: EdgeInsets.zero,
      insetPadding: EdgeInsets.all(10),
      shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(15))),
      title: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisSize: MainAxisSize.min,
          children: [
            InkWell(
              onTap: () => Navigator.pop(context),
              child: Container(
                padding: EdgeInsets.all(5),
                decoration: BoxDecoration(
                  color: primaryColor,
                  borderRadius: BorderRadius.only(
                    topRight: Radius.circular(15),
                  ),
                ),
                child: Icon(Icons.close),
              ),
            ),
            Divider(
              height: 1,
            ),
          ]),
      content: Container(
        width: MediaQuery.of(context).size.width,
        child: SingleChildScrollView(
            scrollDirection: Axis.vertical,
            child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    margin: EdgeInsets.symmetric(vertical: 10),
                    child: Text("Ship To:", style: TextStyle(fontSize: 12)),
                  ),
                  Container(
                      width: width,
                      padding: EdgeInsets.symmetric(horizontal: 5),
                      decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(10),
                          color: Colors.grey[300]),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton(
                          value: _to,
                          isExpanded: true,
                          items: countries.map((value) {
                            return DropdownMenuItem(
                              child: Text(
                                value.country,
                                style: TextStyle(fontSize: 14),
                              ),
                              value: value.id,
                            );
                          }).toList(),
                          onChanged: (dynamic value) {
                            print(value);
                            context.read<HomeProvider>().changeCountries(value);
                            setState(() {
                              _to = value;
                            });
                            checkAPI();
                          },
                        ),
                      )),
                  shipping.loading!
                      ? Center(
                          child: Container(
                              margin: EdgeInsets.symmetric(vertical: 15),
                              height: 150,
                              child: customLoading()),
                        )
                      : Container(
                          child: shipping.shippingAli!.items!.isEmpty
                              ? Container(
                                  margin: EdgeInsets.symmetric(vertical: 5),
                                  child: Text(
                                    selectedCountry != null
                                        ? "${AppLocalizations.of(context)!.translate('cant_delivered')} $selectedCountry"
                                        : "${AppLocalizations.of(context)!.translate('cant_delivered')} ${AppLocalizations.of(context)!.translate('selected_country')}",
                                    style: TextStyle(
                                        fontWeight: FontWeight.w500,
                                        fontSize: 14),
                                    textAlign: TextAlign.center,
                                  ),
                                )
                              : SingleChildScrollView(
                                  scrollDirection: Axis.horizontal,
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        margin:
                                            EdgeInsets.symmetric(vertical: 10),
                                        child: Text("Shipping Method:",
                                            style: TextStyle(fontSize: 12)),
                                      ),
                                      Container(
                                        decoration: BoxDecoration(
                                            borderRadius:
                                                BorderRadius.circular(15),
                                            border: Border.all(
                                                width: 1,
                                                color: Colors.grey[350]!)),
                                        child: DataTable(
                                          border: TableBorder(
                                              horizontalInside: BorderSide(
                                                  width: 1,
                                                  color: Colors.grey[350]!,
                                                  style: BorderStyle.solid)),
                                          columnSpacing: 15,
                                          columns: [
                                            DataColumn(
                                                label: Container(
                                              width: width * .25,
                                              child: Text('Estimated\nDelivery',
                                                  style: TextStyle(
                                                      fontSize: 12,
                                                      fontWeight:
                                                          FontWeight.bold)),
                                            )),
                                            DataColumn(
                                                label: Container(
                                              width: width * .25,
                                              child: Text('Cost',
                                                  textAlign: TextAlign.center,
                                                  style: TextStyle(
                                                      fontSize: 12,
                                                      fontWeight:
                                                          FontWeight.bold)),
                                            )),
                                            DataColumn(
                                                label: Container(
                                              width: width * .2,
                                              child: Text('Tracking',
                                                  textAlign: TextAlign.center,
                                                  style: TextStyle(
                                                      fontSize: 12,
                                                      fontWeight:
                                                          FontWeight.bold)),
                                            )),
                                            DataColumn(
                                                label: Container(
                                              width: width * .4,
                                              child: Text('Carrier',
                                                  textAlign: TextAlign.center,
                                                  style: TextStyle(
                                                      fontSize: 12,
                                                      fontWeight:
                                                          FontWeight.bold)),
                                            )),
                                          ],
                                          rows: [
                                            for (int i = 0;
                                                i <
                                                    shipping.shippingAli!.items!
                                                        .length;
                                                i++)
                                              _dataRow(i, width)
                                          ],
                                        ),
                                      )
                                    ],
                                  )),
                        ),
                ])),
      ),
      actions: <Widget>[],
    );
  }

  _dataRow(int i, double width) {
    final shipping =
        Provider.of<ShippingProvider>(listen: false, context).shippingAli;

    String? shippingEst = shipping!.items![i].time;
    List<String> _result = shipping.items![i].time!.split('-');

    if (_result.first == _result.last) {
      shippingEst = _result.first;
    }

    return DataRow(cells: [
      DataCell(Container(
        width: width * .25,
        child: Text(
          '$shippingEst days',
        ),
      )),
      DataCell(Container(
        width: width * .25,
        child: Text(shipping.items![i].priceFormatStr!,
            textAlign: TextAlign.center),
      )),
      DataCell(Container(
        width: width * .2,
        child: Text(shipping.items![i].tracking! ? "yes" : "no",
            textAlign: TextAlign.center),
      )),
      DataCell(Container(
        width: width * .4,
        child: Text(
            shipping.items![i].company!
                .replaceAll('AliExpress', 'YellowStores'),
            textAlign: TextAlign.center),
      )),
    ]);
  }
}
