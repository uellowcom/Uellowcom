import 'dart:async';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_facebook_auth/flutter_facebook_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:nyoba/models/login_model.dart';
import 'package:nyoba/models/user_model.dart';
import 'package:nyoba/pages/home/home_screen.dart';
import 'dart:convert';
import 'package:nyoba/services/login_api.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:provider/provider.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

import 'home_provider.dart';

class LoginProvider with ChangeNotifier {
  LoginModel? userLogin;
  bool loading = false;
  String? message;
  String? countryCode = '+965';

  AccessToken? fbAccessToken;
  Map<String, dynamic>? fbUserData;

  late FirebaseAuth _firebaseAuth;

  Stream<User?> get authStateChanges => _firebaseAuth.authStateChanges();

  Future<Map<String, dynamic>?> login(context, {username, password}) async {
    var result;
    try {
      loading = true;
      await LoginAPI().loginByDefault(username, password, context).then((data) {
        result = data;

        if (result['cookie'] != null) {
          UserModel user = UserModel.fromJson(result['user']);
          Session().saveUser(user, result['cookie']);
          Session.data.setString("login_type", 'default');
          final home = Provider.of<HomeProvider>(context, listen: false);

          home.isReload = true;
          Navigator.pushAndRemoveUntil(
              context,
              MaterialPageRoute(
                  builder: (BuildContext context) => HomeScreen()),
              (Route<dynamic> route) => false);
          inputDeviceToken(context);
        } else {
          snackBar(context, message: result['message'], color: Colors.red);
        }
        loading = false;

        notifyListeners();
        printLog(result.toString());
      });
    } catch (e) {
      print(e.toString());
      loading = false;
      notifyListeners();
      snackBar(context,
          message: 'Opps, something is wrong. Please contact the developer',
          color: Colors.red);
    }
    return result;
  }

  Future<void> signInOTP(context, phone) async {
    loading = true;
    await LoginAPI().loginByOTP(phone, context).then((data) {
      if (data.statusCode == 200) {
        final responseJson = json.decode(data.body);
        Session.data.setBool('isLogin', true);
        Session.data.setString("cookie", responseJson['cookie']);
        Session.data.setString("login_type", 'otp');

        if (responseJson['user'] != null &&
            responseJson['user'] != "User OTP") {
          Session.data.setString("firstname", responseJson['user']);
        } else {
          Session.data.setString("firstname", responseJson['user_login']);
        }
        Session.data.setInt("id", responseJson['wp_user_id']);

        final home = Provider.of<HomeProvider>(context, listen: false);

        home.isReload = true;
        loading = false;

        inputDeviceToken(context);
        notifyListeners();
      } else {
        loading = false;
        notifyListeners();
      }
    });
  }

  Future signInWithGoogle(BuildContext context) async {
  final FirebaseAuth auth = FirebaseAuth.instance;
  final GoogleSignIn googleSignIn = GoogleSignIn.instance;

  try {
    // Trigger Google Sign-In
    final GoogleSignInAccount? googleUser =
        await googleSignIn.authenticate();

    if (googleUser == null) {
      // User canceled the sign-in
      return;
    }

    // Get auth details
    final GoogleSignInAuthentication googleAuth =
        await googleUser.authentication;

    // Create Firebase credential
    final OAuthCredential credential = GoogleAuthProvider.credential(
      idToken: googleAuth.idToken,
    );

    // Sign in to Firebase
    final UserCredential authResult =
        await auth.signInWithCredential(credential);

    final User? user = authResult.user;
    if (user == null) return;
final authorization = await googleUser.authorizationClient
        .authorizationForScopes(['email', 'profile']);

    final String? accessToken = authorization?.accessToken;

    if (accessToken == null) {
      throw Exception('Failed to obtain Google access token');
    }
    // Call your backend
    final data = await LoginAPI()
        .loginByGoogle(googleAuth.idToken, context);

    final responseJson = json.decode(data.body);

    if (data.statusCode == 200) {
      Session.data.setBool('isLogin', true);
      Session.data.setString("cookie", responseJson['cookie']);
      Session.data.setString("username", responseJson['user_login']);
      Session.data.setString("login_type", 'google');

      final home = Provider.of<HomeProvider>(context, listen: false);
      home.isReload = true;

      inputDeviceToken(context);
    }

    loading = false;
    notifyListeners();
    return responseJson;
  } catch (e) {
    loading = false;
    notifyListeners();
    debugPrint('Google sign-in failed: $e');
  }
}

  String prettyPrint(Map json) {
    JsonEncoder encoder = new JsonEncoder.withIndent('  ');
    String pretty = encoder.convert(json);
    return pretty;
  }

  void _printCredentials() {
    print(
      prettyPrint(fbAccessToken!.toJson()),
    );
  }

  Future<void> signInWithFacebook(context) async {
    final LoginResult result = await FacebookAuth.instance
        .login(); // by the fault we request the email and the public profilea

    if (result.status == LoginStatus.success) {
      fbAccessToken = result.accessToken;

      final userData = await FacebookAuth.instance.getUserData();
      fbUserData = userData;
      _printCredentials();
      await LoginAPI()
          .loginByFacebook(fbAccessToken!.token, context)
          .then((data) {
        final responseJson = json.decode(data.body);
        if (data.statusCode == 200) {
          Session.data.setBool('isLogin', true);
          Session.data.setString("cookie", responseJson['cookie']);
          Session.data.setString("username", responseJson['user_login']);
          Session.data.setString("login_type", 'facebook');

          final home = Provider.of<HomeProvider>(context, listen: false);
          home.isReload = true;

          loading = false;
          inputDeviceToken(context);
          notifyListeners();
          return responseJson;
        } else {
          loading = false;
          notifyListeners();
          return responseJson;
        }
      });
    } else {
      print(result.status);
      print(result.message);
    }
  }

  Future<Map<String, dynamic>?> inputDeviceToken(BuildContext context) async {
    var result;
    await LoginAPI().inputTokenAPI(context).then((data) {
      result = data;
      loading = false;
      notifyListeners();
      printLog(result.toString());
    });
    return result;
  }

  Future<bool?> forgotPassword(context, {email}) async {
    bool? isSuccess;
    loading = true;
    var result;
    await LoginAPI().forgotPasswordAPI(email, context).then((data) {
      result = data;

      if (result['status'] == 'success') {
        isSuccess = true;
      } else {
        isSuccess = false;
        snackBar(context, message: result['message'], color: Colors.red);
      }
      loading = false;

      notifyListeners();
      printLog(result.toString());
    });
    return isSuccess;
  }

  Future<void> signOut() async {
    await _firebaseAuth.signOut();
  }

  /// Generates a cryptographically secure random nonce, to be included in a
  /// credential request.
  String generateNonce([int length = 32]) {
    final charset =
        '0123456789ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz-._';
    final random = Random.secure();
    return List.generate(length, (_) => charset[random.nextInt(charset.length)])
        .join();
  }

  /// Returns the sha256 hash of [input] in hex notation.
  String sha256ofString(String input) {
    final bytes = utf8.encode(input);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }

  signInWithApple(context, {username}) async {
    // To prevent replay attacks with the credential returned from Apple, we
    // include a nonce in the credential request. When signing in in with
    // Firebase, the nonce in the id token returned by Apple, is expected to
    // match the sha256 hash of `rawNonce`.
    final firebaseAuth = FirebaseAuth.instance;
    final rawNonce = generateNonce();
    final nonce = sha256ofString(rawNonce);
    String? userEmail, userName, displayName;

    final appleCredential = await SignInWithApple.getAppleIDCredential(
      scopes: [
        AppleIDAuthorizationScopes.email,
        AppleIDAuthorizationScopes.fullName,
      ],
      nonce: nonce,
    );

    printLog(appleCredential.toString(), name: 'Apple Credential');

    // Create an `OAuthCredential` from the credential returned by Apple.
    final oauthCredential = OAuthProvider("apple.com").credential(
      idToken: appleCredential.identityToken,
      rawNonce: rawNonce,
    );

    printLog(oauthCredential.toString(), name: 'OAUTH');

    final dynamic authResult = await firebaseAuth
        .signInWithCredential(oauthCredential)
        .then((value) async {
      displayName =
          '${appleCredential.givenName} ${appleCredential.familyName}';
      userName = '${appleCredential.familyName}${appleCredential.familyName}';

      if (appleCredential.email != null) {
        userEmail = '${appleCredential.email}';
        Session.data.setString('email_apple', userEmail!);
      } else {
        userEmail = Session.data.getString('email_apple');
      }

      String messageError = "";

      await LoginAPI()
          .loginByApple(userEmail.toString(), displayName.toString(),
              userName.toString().toLowerCase(),
              username1: username, context: context)
          .then((data) {
        printLog(data.toString(), name: 'API Apple SignIn');
        messageError = "";
        if (data['message'].toString() == ("create username first")) {
          messageError = data['message'];
          loading = false;
          notifyListeners();
        } else if (data['message'].toString() ==
            ("username already exist, please try using another username")) {
          messageError = data['message'];
          loading = false;
          notifyListeners();
        } else if (data['message'].toString() ==
            ("email already exist, please try using another email")) {
          messageError = data['message'];
          loading = false;
          notifyListeners();
        } else if (data['wp_user_id'] != null) {
          Session.data.setBool('isLogin', true);
          Session.data.setString("cookie", data['cookie']);
          Session.data.setString("username", data['user_login']);
          Session.data.setString("login_type", 'apple');

          printLog("${Session.data.getString("cookie")}",
              name: "masuk else data login");
          final home = Provider.of<HomeProvider>(context, listen: false);
          home.isReload = true;

          loading = false;
          inputDeviceToken(context);
          notifyListeners();
          printLog("${jsonEncode(data)}", name: "data login");
          return data;
        } else {
          loading = false;
          notifyListeners();
          return data;
        }
      });
    });
  }
}
