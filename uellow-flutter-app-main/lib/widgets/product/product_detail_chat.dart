import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_sms/flutter_sms.dart';
import 'package:modal_bottom_sheet/modal_bottom_sheet.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/models/product_model.dart';
import 'package:nyoba/pages/product/product_form.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher_string.dart';

class ProductDetailChat extends StatelessWidget {
  final ProductModel? productModel;
  const ProductDetailChat({Key? key, this.productModel}) : super(key: key);

  void _sendSMS(String message, List<String> recipents) async {
    String _result = await sendSMS(message: message, recipients: recipents)
        .catchError((onError) {
      print(onError);
    });
    print(_result);
  }

  _launchPhoneURL(String phoneNumber) async {
    String url = 'tel:' + phoneNumber;
    if (await canLaunchUrlString(url)) {
      await launchUrlString(url);
    } else {
      throw 'Could not launch $url';
    }
  }

  _launchWAURL(String? phoneNumber) async {
    String url = 'https://api.whatsapp.com/send?phone=$phoneNumber&text=Hi';
    if (await canLaunchUrlString(url)) {
      await launchUrlString(url, mode: LaunchMode.externalApplication);
    } else {
      throw 'Could not launch $url';
    }
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {
        Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ProductForm(
                productName: productModel!.productName!,
                productImage: productModel!.images![0].src!,
                productId: productModel!.id!,
                regularPrice:
                    double.parse(productModel!.productRegPrice.toString()),
                discPrice: double.parse(productModel!.productPrice!.toString()),
              ),
            ));
        // showMaterialModalBottomSheet(
        //   context: context,
        //   shape: RoundedRectangleBorder(
        //     borderRadius: BorderRadius.vertical(
        //       top: Radius.circular(12),
        //     ),
        //   ),
        //   clipBehavior: Clip.antiAliasWithSaveLayer,
        //   expand: false,
        //   builder: (context) => _buildBodyDescription(context),
        // );
      },
      child: Container(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
                width: 20.w,
                height: 20.h,
                child: Image.asset("images/product_detail/messenger.png")),
            Container(
              child: Text(
                "${AppLocalizations.of(context)!.translate('chat')}",
                style: TextStyle(
                  fontSize: responsiveFont(9),
                ),
              ),
            )
          ],
        ),
      ),
    );
  }

  Widget _buildBodyDescription(context) {
    final contact = Provider.of<HomeProvider>(context, listen: false);

    return Material(
      child: ListView(
          shrinkWrap: true,
          padding: EdgeInsets.zero,
          controller: ModalScrollController.of(context),
          children: [
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
                    "Chat",
                    style: TextStyle(fontWeight: FontWeight.w500),
                  ),
                  GestureDetector(
                    onTap: () => Navigator.pop(context),
                    child: Container(child: Icon(Icons.clear)),
                  )
                ],
              ),
            ),
            ListTile(
              onTap: () {
                _launchWAURL(contact.wa.description);
              },
              leading: Container(
                  height: 20.h,
                  width: 20.w,
                  padding: EdgeInsets.all(2),
                  decoration: BoxDecoration(
                      color: Colors.black,
                      borderRadius: BorderRadius.circular(5)),
                  child: Image.asset("images/account/whatsapp.png")),
              title: Text("WhatsApp"),
            ),
            ListTile(
              onTap: () {
                _launchPhoneURL(contact.phone.description!);
              },
              leading: Container(
                  height: 20.h,
                  width: 20.w,
                  padding: EdgeInsets.all(2),
                  decoration: BoxDecoration(
                      color: Colors.black,
                      borderRadius: BorderRadius.circular(5)),
                  child: Image.asset("images/account/call.png")),
              title: Text("Phone"),
            ),
            ListTile(
              onTap: () {
                _sendSMS('', [contact.sms.description!]);
              },
              leading: Container(
                  height: 20.h,
                  width: 20.w,
                  padding: EdgeInsets.all(2),
                  decoration: BoxDecoration(
                      color: Colors.black,
                      borderRadius: BorderRadius.circular(5)),
                  child: Image.asset("images/account/sms.png")),
              title: Text("SMS"),
            )
          ]),
    );
  }
}
