import 'package:flutter/material.dart';
import 'package:flutter/src/widgets/framework.dart';
import 'package:flutter/src/widgets/placeholder.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/utils/currency_format.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../../app_localizations.dart';

class ProductForm extends StatelessWidget {
  final String? productName, productImage;
  final int? productId;
  final double? regularPrice, discPrice;
  final bool? isFromAccount;
  const ProductForm(
      {super.key,
      this.productName,
      this.productImage,
      this.productId,
      this.regularPrice,
      this.discPrice,
      this.isFromAccount = false});

  @override
  Widget build(BuildContext context) {
    TextEditingController nameController = TextEditingController();
    TextEditingController emailController = TextEditingController();
    TextEditingController subjectController = TextEditingController();
    TextEditingController messageController = TextEditingController();

    final product = Provider.of<ProductProvider>(context, listen: false);

    return Scaffold(
      body: Center(
        child: Container(
          padding: EdgeInsets.symmetric(
            horizontal: 15.w,
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                isFromAccount != true
                    ? CircleAvatar(
                        radius: 50,
                        backgroundImage: NetworkImage(productImage ?? ""),
                      )
                    : Container(),
                isFromAccount != true
                    ? SizedBox(
                        height: 10.h,
                      )
                    : SizedBox(),
                isFromAccount != true
                    ? Text(
                        "$productName",
                        textAlign: TextAlign.center,
                      )
                    : SizedBox(),
                isFromAccount != true
                    ? SizedBox(
                        height: 5.h,
                      )
                    : SizedBox(),
                isFromAccount != true
                    ? Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          regularPrice != 0.0
                              ? Text(
                                  "${stringToCurrency(regularPrice!, context)}",
                                  style: TextStyle(
                                      color: Colors.grey,
                                      decoration: TextDecoration.lineThrough))
                              : SizedBox(),
                          SizedBox(
                            width: 5.w,
                          ),
                          Text("${stringToCurrency(discPrice!, context)}")
                        ],
                      )
                    : SizedBox(),
                isFromAccount != true
                    ? SizedBox(
                        height: 10.h,
                      )
                    : SizedBox(),
                Text(
                  isFromAccount == true
                      ? "${AppLocalizations.of(context)!.translate('contact_us')}"
                      : "${AppLocalizations.of(context)!.translate('ask_question')}",
                  style: TextStyle(fontSize: responsiveFont(18)),
                ),
                SizedBox(
                  height: 10.h,
                ),
                TextField(
                  controller: nameController,
                  decoration: InputDecoration(
                    label: Text(
                        "${AppLocalizations.of(context)!.translate('your_name')}"),
                    enabledBorder: const OutlineInputBorder(
                      borderSide:
                          const BorderSide(color: Colors.grey, width: 1),
                    ),
                  ),
                ),
                SizedBox(
                  height: 10.h,
                ),
                TextField(
                  controller: emailController,
                  decoration: InputDecoration(
                    label: Text(
                        "${AppLocalizations.of(context)!.translate('your_email')}"),
                    enabledBorder: const OutlineInputBorder(
                      borderSide:
                          const BorderSide(color: Colors.grey, width: 1),
                    ),
                  ),
                ),
                SizedBox(
                  height: 10.h,
                ),
                TextField(
                  controller: subjectController,
                  decoration: InputDecoration(
                    label: Text(
                        "${AppLocalizations.of(context)!.translate('subject')}"),
                    enabledBorder: const OutlineInputBorder(
                      borderSide:
                          const BorderSide(color: Colors.grey, width: 1),
                    ),
                  ),
                ),
                SizedBox(
                  height: 10.h,
                ),
                TextField(
                  controller: messageController,
                  maxLines: 9,
                  decoration: InputDecoration(
                    label: Text(
                        "${AppLocalizations.of(context)!.translate('your_message')}"),
                    enabledBorder: const OutlineInputBorder(
                      borderSide:
                          const BorderSide(color: Colors.grey, width: 1),
                    ),
                  ),
                ),
                SizedBox(
                  height: 20.h,
                ),
                Consumer<ProductProvider>(
                  builder: (context, value, child) {
                    return Row(
                      children: [
                        Expanded(
                          child: GestureDetector(
                            onTap: () {
                              if (value.loadingFormProduct == false) {
                                Navigator.pop(context);
                              }
                            },
                            child: Container(
                              padding: EdgeInsets.symmetric(vertical: 7.h),
                              decoration: BoxDecoration(
                                color: primaryColor,
                                borderRadius: BorderRadius.circular(5),
                              ),
                              child: Center(
                                  child: value.loadingFormProduct == true
                                      ? customLoading(color: Colors.white)
                                      : Text(
                                          "${AppLocalizations.of(context)!.translate('back')}"
                                              .toUpperCase())),
                            ),
                          ),
                        ),
                        SizedBox(
                          width: 5.w,
                        ),
                        Expanded(
                          child: GestureDetector(
                            onTap: () async {
                              if (nameController.text == "") {
                                snackBar(context,
                                    message:
                                        "${AppLocalizations.of(context)!.translate('name_empty')}",
                                    color: Colors.red);
                              } else if (emailController.text == "") {
                                snackBar(context,
                                    message:
                                        "${AppLocalizations.of(context)!.translate('email_empty')}",
                                    color: Colors.red);
                              } else if (subjectController.text == "") {
                                snackBar(context,
                                    message:
                                        "${AppLocalizations.of(context)!.translate('subject')}",
                                    color: Colors.red);
                              } else {
                                if (value.loadingFormProduct == false) {
                                  if (isFromAccount == true) {
                                    await product.fetchFormProduct(
                                      context: context,
                                      email: emailController.text,
                                      message: messageController.text,
                                      name: nameController.text,
                                      subject: subjectController.text,
                                    );
                                  } else {
                                    await product.fetchFormProduct(
                                        context: context,
                                        email: emailController.text,
                                        message: messageController.text,
                                        name: nameController.text,
                                        subject: subjectController.text,
                                        id: productId);
                                  }

                                  if (product.isFormSucces == true) {
                                    snackBar(context,
                                        message:
                                            "${AppLocalizations.of(context)!.translate('form_success')}",
                                        color: primaryColor);
                                    Navigator.pop(context);
                                  } else {
                                    snackBar(context,
                                        message:
                                            "${AppLocalizations.of(context)!.translate('form_failed')}",
                                        color: primaryColor);
                                    Navigator.pop(context);
                                  }
                                }
                              }
                            },
                            child: Container(
                              padding: EdgeInsets.symmetric(vertical: 7.h),
                              decoration: BoxDecoration(
                                color: primaryColor,
                                borderRadius: BorderRadius.circular(5),
                              ),
                              child: Center(
                                  child: value.loadingFormProduct == true
                                      ? customLoading(color: Colors.white)
                                      : Text(
                                          "${AppLocalizations.of(context)!.translate('submit')}"
                                              .toUpperCase())),
                            ),
                          ),
                        )
                      ],
                    );
                  },
                )
              ],
            ),
          ),
        ),
      ),
    );
  }
}
