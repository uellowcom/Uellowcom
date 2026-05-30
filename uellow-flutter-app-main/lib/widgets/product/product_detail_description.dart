import 'package:flutter/material.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:modal_bottom_sheet/modal_bottom_sheet.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/models/product_model.dart';

class ProductDetailDescription extends StatelessWidget {
  final ProductModel? productModel;
  const ProductDetailDescription({Key? key, this.productModel})
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
          builder: (context) => buildBodyDescription(context),
        );
      },
      child: Container(
        padding: EdgeInsets.only(left: 5, right: 5, top: 5, bottom: 5),
        child:
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(
            "${AppLocalizations.of(context)!.translate('item_description')}",
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

  Widget buildBodyDescription(context) {
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
                "${AppLocalizations.of(context)!.translate('item_description')}",
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
            child: Container(
                padding: EdgeInsets.symmetric(horizontal: 15),
                child: HtmlWidget(
                  productModel!.productDescription!,
                  textStyle: TextStyle(color: HexColor("929292")),
                )),
          ),
        )
      ]),
    );
  }
}
