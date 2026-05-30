// =============================================================================
// EXAMPLE — How to wire UellowApi + AuthState into main.dart
// =============================================================================
//
// This is a reference snippet, NOT a drop-in replacement. Copy the relevant
// blocks into your actual main.dart (the existing one has a lot of legacy
// provider wiring you'll want to keep migrating piece-by-piece).
//
// The three things that MUST be in main():
//   1. UellowApi.init() before runApp
//   2. setAppMeta() with platform + version
//   3. AuthState added to MultiProvider (and call .bootstrap() right away)
// =============================================================================

import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:nyoba/api/uellow_api.dart';
import 'package:nyoba/api/uellow_auth_state.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:provider/provider.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp();

  // ── Initialize the API client ───────────────────────────────────────
  await UellowApi.init();

  // App metadata — version flows in every request header.
  final pkg = await PackageInfo.fromPlatform();
  UellowApi.instance.setAppMeta(
    appVersion: pkg.version,
    platform: Platform.isIOS ? 'ios' : 'android',
  );

  // ── Push notifications: register device with the API ────────────────
  // Safe for guests too — token attached to mobile.session row.
  try {
    final fcm = await FirebaseMessaging.instance.getToken();
    if (fcm != null && fcm.isNotEmpty) {
      await UellowApi.instance.notifications.registerDevice(
        deviceId:   pkg.appName + '-${pkg.buildNumber}',
        pushToken:  fcm,
        platform:   Platform.isIOS ? 'ios' : 'android',
        appVersion: pkg.version,
      );
    }
  } catch (_) {/* network might be down; not fatal */}

  // Re-register on token rotation (FCM does this every now and then).
  FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
    UellowApi.instance.notifications.registerDevice(
      deviceId: pkg.appName + '-${pkg.buildNumber}',
      pushToken: newToken,
      platform: Platform.isIOS ? 'ios' : 'android',
      appVersion: pkg.version,
    );
  });

  runApp(const UellowApp());
}

class UellowApp extends StatelessWidget {
  const UellowApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // The auth provider — single source of truth for user state.
        // Calls bootstrap() to verify any saved token at startup.
        ChangeNotifierProvider(create: (_) => AuthState()..bootstrap()),

        // ── Keep your existing legacy providers here for now — ───────
        // migrate them to the v2 client one by one as you refactor
        // pages. Each refactored page deletes one legacy provider.
        // (e.g. ChangeNotifierProvider(create: (_) => HomeProvider()),)
      ],
      child: MaterialApp(
        title: 'Uellow',
        // Sync the API's lang with the active locale, so server-side
        // bilingual text and search match the UI.
        builder: (context, child) {
          final code = Localizations.localeOf(context).languageCode;
          UellowApi.instance.setLang(code);
          return child!;
        },
        home: const _RootRouter(),
      ),
    );
  }
}

/// Routes between login screen and home based on auth state. While
/// bootstrap() is verifying a stored token, show a splash so the user
/// doesn't briefly see the login screen on every cold start.
class _RootRouter extends StatelessWidget {
  const _RootRouter();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthState>();
    if (auth.isBootstrapping) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    // Both guest and logged-in users can browse — the app gates
    // checkout / wishlist / orders individually via require_auth.
    return const HomeScreen();
  }
}

// Placeholder — your actual HomeScreen lives in pages/home/home_screen.dart
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});
  @override
  Widget build(BuildContext context) => const Scaffold();
}
