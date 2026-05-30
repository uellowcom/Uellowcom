import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:nyoba/pages/notification/notification_screen.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:webview_flutter/webview_flutter.dart';

class WebViewScreen extends StatefulWidget {
  final url;
  final String? title;
  final bool? fromNotif ;

  WebViewScreen({Key? key, this.url, this.title, this.fromNotif=false})
      : super(key: key);
  @override
  WebViewScreenState createState() => WebViewScreenState();
}

class WebViewScreenState extends State<WebViewScreen> {
  final Completer<WebViewController> _controller =
      Completer<WebViewController>();

  late WebViewController _webViewController;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    if (Platform.isAndroid) WebView.platform = SurfaceAndroidWebView();
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: () async {
        // backPopDialog();
        if (widget.fromNotif == true) {
          Navigator.pushAndRemoveUntil(
              context,
              MaterialPageRoute(
                builder: (context) => NotificationScreen(fromPushNotif: true),
              ),
              (route) => false);
        }

        return true;
      },
      child: Scaffold(
          appBar: AppBar(
            elevation: 0,
            backgroundColor: Colors.white,
            title: Text(
              widget.title!,
              style: TextStyle(color: Colors.black),
            ),
            leading: IconButton(
              color: Colors.black,
              onPressed: () {
                // backPopDialog();
                if (widget.fromNotif == true) {
                  Navigator.pushAndRemoveUntil(
                      context,
                      MaterialPageRoute(
                        builder: (context) =>
                            NotificationScreen(fromPushNotif: true),
                      ),
                      (route) => false);
                } else {
                  Navigator.pop(context);
                }
              },
              icon: Platform.isIOS
                  ? Icon(Icons.arrow_back_ios)
                  : Icon(Icons.arrow_back),
            ),
          ),
          body: Stack(
            children: [
              WebView(
                initialUrl: widget.url,
                javascriptMode: JavascriptMode.unrestricted,
                onProgress: (int progress) {
                  print("WebView is loading (progress : $progress%)");

                  _webViewController.runJavascript(
                      "document.getElementById('headerwrap').style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementById('footerwrap').style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByTagName('header')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByTagName('footer')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('return-to-shop')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('page-title')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('woocommerce-error')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('woocommerce-breadcrumb')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('useful-links')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('widget woocommerce widget_product_search')[1].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.querySelector('.nasa-bottom-bar').remove()");
                },
                onWebViewCreated: (WebViewController webViewController) {
                  _webViewController = webViewController;
                  _controller.complete(webViewController);
                },
                onPageStarted: (String url) {
                  print('Page started loading: $url');
                },
                onPageFinished: (String url) {
                  print('Page finished loading: $url');
                  setState(() {
                    isLoading = false;
                  });
                  _webViewController.runJavascript(
                      "document.getElementById('headerwrap').style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementById('footerwrap').style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByTagName('header')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByTagName('footer')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('return-to-shop')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('page-title')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('woocommerce-error')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('woocommerce-breadcrumb')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('useful-links')[0].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.getElementsByClassName('widget woocommerce widget_product_search')[1].style.display= 'none';");
                  _webViewController.runJavascript(
                      "document.querySelector('.nasa-bottom-bar').remove()");
                },
                gestureNavigationEnabled: true,
              ),
              isLoading
                  ? Center(
                      child: customLoading(),
                    )
                  : Stack(),
            ],
          )),
    );
  }
}
