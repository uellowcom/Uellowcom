import 'package:flutter/material.dart';
import 'package:flutter/src/widgets/framework.dart';
import 'package:flutter/src/widgets/placeholder.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';

import '../../app_localizations.dart';

class SelectCountryScreen extends StatefulWidget {
  const SelectCountryScreen({super.key});

  @override
  State<SelectCountryScreen> createState() => _SelectCountryScreenState();
}

class _SelectCountryScreenState extends State<SelectCountryScreen> {
  back(val) {
    Navigator.pop(context, val);
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: () => back(false),
      child: Scaffold(
        appBar: AppBar(
          elevation: 0,
          title: Text(
            "${AppLocalizations.of(context)!.translate('select_country')}",
            style: TextStyle(color: Colors.black),
          ),
          leading: GestureDetector(
              onTap: () => back(false),
              child: Icon(
                Icons.arrow_back,
                color: Colors.black,
              )),
          backgroundColor: primaryColor,
        ),
        body: Consumer<ProductProvider>(
          builder: (context, value, child) => ListView.separated(
            itemCount: value.countries.length,
            itemBuilder: (context, index) {
              return InkWell(
                onTap: () async {
                  await value.setCountry(value.countries[index].code);
                  back(true);
                },
                child: Container(
                  padding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                  child: Text("${value.countries[index].name}"),
                ),
              );
            },
            separatorBuilder: (context, index) {
              return Divider();
            },
          ),
        ),
      ),
    );
  }
}
