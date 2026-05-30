import 'package:flutter/material.dart';
import 'package:modal_bottom_sheet/modal_bottom_sheet.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/utils/utility.dart';

class ProductDetailSpecification extends StatelessWidget {
  final ProductModel? productModel;
  const ProductDetailSpecification({Key? key, this.productModel})
      : super(key: key);

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {
        showMaterialModalBottomSheet(
          context: context,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(
              top: Radius.circular(12),
            ),
          ),
          clipBehavior: Clip.antiAliasWithSaveLayer,
          expand: false,
          backgroundColor: Theme.of(context).colorScheme.surface,
          builder: (context) => _buildBodyDescription(context),
        );
      },
      child: Container(
        padding: EdgeInsets.only(left: 5, right: 5, top: 5, bottom: 5),
        child:
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(
            "${AppLocalizations.of(context)!.translate('specifications')}",
            style: TextStyle(fontWeight: FontWeight.w500),
          ),
          Icon(
            Icons.chevron_right,
            color: Colors.grey[400],
          )
        ]),
      ),
    );
  }

  Widget _buildBodyDescription(context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.8,
      child: Column(children: [
        Container(
          padding: EdgeInsets.all(10),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                  child: Icon(
                Icons.square,
                color: Colors.transparent,
              )),
              Text(
                "${AppLocalizations.of(context)!.translate('specifications')}",
                style: TextStyle(fontWeight: FontWeight.w500),
              ),
              GestureDetector(
                onTap: () => Navigator.pop(context),
                child: Container(child: Icon(Icons.clear)),
              )
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            child: productModel!.specifications!.length == 0
                ? Container()
                : DataTable(
                    headingRowHeight: 0,
                    columnSpacing: 80,
                    columns: [
                      DataColumn(
                          label: Text('name',
                              style: TextStyle(
                                  fontSize: 18, fontWeight: FontWeight.bold))),
                      DataColumn(
                          label: Text('option',
                              style: TextStyle(
                                  fontSize: 18, fontWeight: FontWeight.bold))),
                    ],
                    rows: [
                      for (int i = 0;
                          i < productModel!.specifications!.length;
                          i++)
                        DataRow(cells: [
                          DataCell(Text(
                            productModel!.specifications![i].name,
                            style: TextStyle(
                                color: Colors.grey,
                                fontSize: responsiveFont(11)),
                          )),
                          DataCell(Text(
                            productModel!.specifications![i].options!.first,
                            style: TextStyle(fontSize: responsiveFont(11)),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          )),
                        ]),
                    ],
                  ),
          ),
        )
      ]),
    );
  }
}
