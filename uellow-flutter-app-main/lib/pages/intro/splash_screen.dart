import 'dart:async';
import 'dart:convert';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:geocoding/geocoding.dart';
import 'package:geolocator/geolocator.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/pages/category/brand_product_screen.dart';
import 'package:nyoba/pages/intro/intro_screen.dart';
import 'package:nyoba/pages/home/home_screen.dart';
import 'package:nyoba/pages/product/product_detail_screen.dart';
import 'package:nyoba/provider/general_settings_provider.dart';
import 'package:nyoba/provider/home_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:provider/provider.dart';
import 'package:video_player/video_player.dart';
import 'package:path/path.dart' as p;

import '../../app_localizations.dart';

class SplashScreen extends StatefulWidget {
  final Future Function()? onLinkClicked;
  SplashScreen({Key? key, this.onLinkClicked}) : super(key: key);

  @override
  _SplashScreenState createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  bool loadHomeSuccess = true;

  String? _versionName;

  bool isVideo = false;
  late VideoPlayerController _controller;

  Timer? _timer;
  int _start = 3;

  bool skip = false;

  var jsonData;

  String? _currentAddress;
  Position? _currentPosition;

  Future startSplashScreen() async {
    final home = Provider.of<HomeProvider>(context, listen: false);
    final ext = p.extension(home.splashscreen.image!);
    printLog(ext, name: 'Extension Splash');
    var duration = Duration(milliseconds: 3000);

    if (ext == '.mp4') {
      var videoDuration;
      setState(() {
        isVideo = true;
      });
      _controller = VideoPlayerController.network(home.splashscreen.image!)
        ..initialize().then((_) {
          setState(() {
            videoDuration = _controller.value.duration;
            printLog(videoDuration.toString(), name: 'DurationVideo');
            duration = videoDuration;
          });
          _controller.play();

          navigateScreen(duration);
        });
    } else if (ext == '.gif') {
      duration = Duration(milliseconds: 5000);

      navigateScreen(duration);
    } else {
      navigateScreen(duration);
    }
  }

  Future navigateScreen(duration) async {
    printLog(duration.toString(), name: 'Duration');
    final home = Provider.of<HomeProvider>(context, listen: false);

    startTimer();
    return Timer(duration, () {
      if (skip == false) {
        if (mounted) {
          Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) {
            if (home.introStatus == 'show') {
              return IntroScreen(
                intro: home.intro,
              );
            } else {
              if (!Session.data.containsKey('isIntro')) {
                Session.data.setBool('isLogin', false);
                Session.data.setBool('isIntro', false);
              }
              return Session.data.getBool('isIntro')!
                  ? HomeScreen()
                  : IntroScreen(
                      intro: home.intro,
                    );
            }
          }));
          printLog("${widget.onLinkClicked}", name: "On link clicked");
          if (widget.onLinkClicked != null) {
            print("URL Available");
            if (home.introStatus == 'show') {
              Navigator.of(context)
                  .pushReplacement(MaterialPageRoute(builder: (_) {
                return HomeScreen();
              }));
            }
            widget.onLinkClicked!();
          }
        }
      }
    });
  }

  void startTimer() {
    const oneSec = const Duration(seconds: 1);
    _timer = new Timer.periodic(
      oneSec,
      (Timer timer) {
        if (_start == 0) {
          setState(() {
            timer.cancel();
          });
        } else {
          setState(() {
            _start--;
          });
        }
      },
    );
  }

  Future _init() async {
    final _packageInfo = await PackageInfo.fromPlatform();

    context.read<HomeProvider>().setPackageInfo(_packageInfo);

    return _packageInfo.version;
  }

  @override
  void initState() {
    super.initState();
    printLog(widget.onLinkClicked.toString());

    // _getCurrentPosition().then((data) {
    //   _getAddressFromLatLng(_currentPosition!);
    // });

    loadHome();
  }

  @override
  void setState(fn) {
    if (mounted) {
      super.setState(fn);
    }
  }

  @override
  void dispose() {
    super.dispose();
  }

  loadHome() async {
    setState(() {
      context.read<HomeProvider>().loading = true;
    });
    printLog("HOME LOADING " + context.read<HomeProvider>().loading.toString());
    await _getCurrentPosition().then((data) {
      _getAddressFromLatLng(_currentPosition!);
    });

    // if (!Session.data.containsKey('currency_code')) {
    //   Session.data.setString('currency_code', "USD");
    // }
    if (!Session.data.containsKey('countries')) {
      Provider.of<ProductProvider>(context, listen: false)
          .fetchCountries(context);
    }
    await Provider.of<GeneralSettingsProvider>(context, listen: false)
        .fetchGeneralSettings(context);
    await Provider.of<HomeProvider>(context, listen: false)
        .fetchDiscountRule(context);
    await Provider.of<GeneralSettingsProvider>(context, listen: false)
        .loadAllCurrency(context);
    await Provider.of<HomeProvider>(context, listen: false)
        .fetchHome(context)
        .then((value) async {
      final appColors =
          Provider.of<HomeProvider>(context, listen: false).appColors;
      this.setState(() {
        loadHomeSuccess = value!;
      });
      appColors.forEach((element) {
        setState(() {
          if (element.title == 'primary') {
            primaryColor = HexColor(element.description!);
          } else if (element.title == 'secondary') {
            secondaryColor = HexColor(element.description!);
          }
        });
      });
      if (loadHomeSuccess) {
        setState(() {
          context.read<HomeProvider>().loading = false;
        });
        if (mounted) await startSplashScreen();
      }
    });
  }

  //LOCATION
  Future<void> _getAddressFromLatLng(Position position) async {
    final String jsonString = await rootBundle
        .loadString('assets/json/country-by-currency-code.json');
    setState(() {
      jsonData = jsonDecode(jsonString);
    });
    await placemarkFromCoordinates(
            _currentPosition!.latitude, _currentPosition!.longitude)
        .then((List<Placemark> placemarks) {
      Placemark place = placemarks[0];
      printLog(
          "${place.administrativeArea} - ${place.country} - ${place.isoCountryCode} - ${place.locality} - ${place.name} - ${place.postalCode} - ${place.subThoroughfare} - ${place.thoroughfare}");
      for (var i in jsonData) {
        if (i['country'] == place.country) {
          Session.data.setString('currency_code', i['currency_code'] ?? "USD");
          break;
        }
      }
      setState(() {
        _currentAddress =
            '${place.street}, ${place.subLocality}, ${place.subAdministrativeArea}, ${place.postalCode}';
        context.read<ProductProvider>().currentPosition = place.isoCountryCode!;
      });
    });
    printLog(_currentAddress!);
  }

  Future<void> _getCurrentPosition() async {
    final hasPermission = await _handleLocationPermission();
    if (!hasPermission) return;
    await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high)
        .then((Position position) {
      setState(() => _currentPosition = position);
    }).catchError((e) {
      debugPrint(e);
    });
  }

  Future<bool> _handleLocationPermission() async {
    bool serviceEnabled;
    LocationPermission permission;

    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      snackBar(context,
          message:
              "Location services are disabled. Please enable the services");
      return false;
    }
    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        snackBar(context, message: 'Location permissions are denied');

        return false;
      }
    }
    if (permission == LocationPermission.deniedForever) {
      snackBar(context,
          message:
              'Location permissions are permanently denied, we cannot request permissions.');

      return false;
    }
    return true;
  }
  //END OF LOCATION

  @override
  Widget build(BuildContext context) {
    final home = Provider.of<HomeProvider>(context, listen: false);
    return Scaffold(
        backgroundColor: Colors.white,
        body: home.loading
            ? Center(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        padding: EdgeInsets.all(20),
                        child: Image.asset(
                          "images/icon/icon_full.png",
                          height: 220,
                        ),
                      ),
                      SizedBox(
                        height: 20,
                      ),
                      customLoading(size: 75, color: Colors.black),
                      SizedBox(
                        height: 20,
                      ),
                      Text(
                        "${AppLocalizations.of(context)!.translate('loading')}",
                        style: TextStyle(fontSize: 22, color: Colors.black),
                      ),
                    ]),
              )
            : loadHomeSuccess
                ? isVideo
                    ? videoSplashScreen()
                    : imageSplashScreen()
                : buildError(context));
  }

  imageSplashScreen() {
    final home = Provider.of<HomeProvider>(context, listen: false);

    return Stack(
      children: [
        RawGestureDetector(
          gestures: {
            AllowMultipleVerticalDragGestureRecognizer:
                GestureRecognizerFactoryWithHandlers<
                    AllowMultipleVerticalDragGestureRecognizer>(
              () => AllowMultipleVerticalDragGestureRecognizer(),
              (AllowMultipleVerticalDragGestureRecognizer instance) {
                instance
                  ..onEnd = (_) {
                    printLog("${home.splashscreen.redirect?.to}",
                        name: "splash screen redirect");
                    setState(() {
                      skip = true;
                    });
                    printLog("$skip skip splah");
                    if (home.splashscreen.redirect?.to == 'product') {
                      printLog("Masuk ke redirect Categories");
                      Navigator.of(context)
                          .pushReplacement(MaterialPageRoute(builder: (_) {
                        return ProductDetail(
                          isFromSplashScreen: true,
                          productId: home.splashscreen.redirect?.objectId,
                        );
                      }));
                    } else if (home.splashscreen.redirect?.to == 'categories' ||
                        home.splashscreen.redirect?.to == 'category') {
                      printLog("Masuk ke redirect Categories");
                      Navigator.of(context)
                          .pushReplacement(MaterialPageRoute(builder: (_) {
                        return BrandProducts(
                          isNeedSub: true,
                          categoryId: home.splashscreen.redirect?.objectId,
                          isFromSplashScreen: true,
                          brandName: home.splashscreen.title,
                          withFilter: true,
                        );
                      }));
                    }
                  };
              },
            )
          },
          // onTap: () {
          //   if (home.splashscreen.redirect?.to == 'product') {
          //     Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) {
          //       return ProductDetail(
          //         // isFromSplashScreen: true,
          //         productId: home.splashscreen.redirect?.objectId,
          //       );
          //     }));
          //   } else if (home.splashscreen.redirect?.to == 'categories') {
          //     Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) {
          //       return BrandProducts(
          //         categoryId: home.splashscreen.redirect?.objectId,
          //       );
          //     }));
          //   }
          // },
          child: Container(
              decoration: BoxDecoration(
                  image: DecorationImage(
                      fit: BoxFit.cover,
                      image: CachedNetworkImageProvider(
                        home.splashscreen.image!,
                      ))),
              width: MediaQuery.of(context).size.width,
              height: MediaQuery.of(context).size.height,
              child: Column(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          home.splashscreen.title!,
                          style: TextStyle(fontSize: 22, color: Colors.grey),
                        ),
                        Text(
                          home.splashscreen.description!,
                          style: TextStyle(fontSize: 18, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                  FutureBuilder(
                    future: _init(),
                    builder: (context, snapshot) {
                      if (snapshot.hasData) {
                        _versionName = snapshot.data as String?;
                        return Text(
                          'Version ' + _versionName!,
                        );
                      } else {
                        return Container();
                      }
                    },
                  ),
                ],
              )),
        ),
        Positioned(
          top: 30.h,
          right: 10.w,
          child: RawGestureDetector(
            gestures: {
              AllowMultipleVerticalDragGestureRecognizer:
                  GestureRecognizerFactoryWithHandlers<
                      AllowMultipleVerticalDragGestureRecognizer>(
                () => AllowMultipleVerticalDragGestureRecognizer(),
                (AllowMultipleVerticalDragGestureRecognizer instance) {
                  instance
                    ..onEnd = (_) {
                      printLog("Skipped..");
                      Navigator.of(context)
                          .pushReplacement(MaterialPageRoute(builder: (_) {
                        if (home.introStatus == 'show') {
                          return IntroScreen(
                            intro: home.intro,
                          );
                        } else {
                          if (!Session.data.containsKey('isIntro')) {
                            Session.data.setBool('isLogin', false);
                            Session.data.setBool('isIntro', false);
                          }
                          return Session.data.getBool('isIntro')!
                              ? HomeScreen()
                              : IntroScreen(
                                  intro: home.intro,
                                );
                        }
                      }));
                      printLog("${widget.onLinkClicked}",
                          name: "On link clicked");
                      if (widget.onLinkClicked != null) {
                        print("URL Available");
                        if (home.introStatus == 'show') {
                          Navigator.of(context)
                              .pushReplacement(MaterialPageRoute(builder: (_) {
                            return HomeScreen();
                          }));
                        }
                        widget.onLinkClicked!();
                      } else {
                        Navigator.of(context)
                            .pushReplacement(MaterialPageRoute(builder: (_) {
                          return HomeScreen();
                        }));
                      }
                    };
                },
              )
            },
            child: Container(
              height: 23.h,
              width: 70.w,
              decoration: BoxDecoration(
                  color: Colors.black45,
                  borderRadius: BorderRadius.circular(10)),
              child: Center(
                child: Text(
                  "${AppLocalizations.of(context)!.translate('skip')} $_start",
                  style: TextStyle(color: Colors.white),
                ),
              ),
            ),
          ),
        )
      ],
    );
  }

  videoSplashScreen() {
    return Center(
      child: _controller.value.isInitialized
          ? SizedBox(
              width: MediaQuery.of(context).size.width,
              height: MediaQuery.of(context).size.height,
              child: VideoPlayer(_controller),
            )
          : Container(),
    );
  }
}

class AllowMultipleVerticalDragGestureRecognizer
    extends VerticalDragGestureRecognizer {
  @override
  void rejectGesture(int pointer) {
    acceptGesture(pointer);
  }
}
