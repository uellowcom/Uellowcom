// =============================================================================
// Uellow brand theme — single source of truth for colors, radii, gradients,
// text styles. Used by every v2 screen + widget.
// =============================================================================
import 'package:flutter/material.dart';

class UellowColors {
  UellowColors._();
  static const yellow      = Color(0xFFF5C320);   // primary brand
  static const yellowLight = Color(0xFFFFD340);
  static const yellowSoft  = Color(0xFFFFF5D0);
  static const yellowFaint = Color(0xFFFFFCEF);
  static const darkBrown   = Color(0xFF412402);   // primary dark
  static const darkSoft    = Color(0xFF1F1100);

  static const ink         = Color(0xFF1A1108);
  static const text        = Color(0xFF5D4D2E);
  static const muted       = Color(0xFF9C8A5E);
  static const border      = Color(0xFFF2EBD3);
  static const bg          = Color(0xFFF8F4E3);

  static const success     = Color(0xFF10B981);
  static const successDk   = Color(0xFF047857);
  static const successBg   = Color(0xFFECFDF5);
  static const danger      = Color(0xFFFF4D4D);
  static const dangerDk    = Color(0xFFB91C1C);
  static const dangerBg    = Color(0xFFFFE3E3);
  static const warn        = Color(0xFFC99000);
  static const warnBg      = Color(0xFFFFE8A0);

  // Gradients
  static const heroLoyalty = LinearGradient(
    begin: Alignment.topLeft, end: Alignment.bottomRight,
    colors: [yellowLight, Color(0xFFF5A800)],
  );
  static const heroWallet = LinearGradient(
    begin: Alignment.topLeft, end: Alignment.bottomRight,
    colors: [darkBrown, darkSoft],
  );
  static const heroFlash = LinearGradient(
    begin: Alignment.topLeft, end: Alignment.bottomRight,
    colors: [danger, Color(0xFFC81212)],
  );
}

class UellowRadius {
  UellowRadius._();
  static const xs   = Radius.circular(6);
  static const sm   = Radius.circular(8);
  static const md   = Radius.circular(12);
  static const lg   = Radius.circular(14);
  static const xl   = Radius.circular(18);
  static const xxl  = Radius.circular(20);
  static const pill = Radius.circular(999);

  static const all_md   = BorderRadius.all(md);
  static const all_lg   = BorderRadius.all(lg);
  static const all_xl   = BorderRadius.all(xl);
  static const all_pill = BorderRadius.all(pill);
}

class UellowSpace {
  UellowSpace._();
  static const xs = 4.0;
  static const sm = 6.0;
  static const md = 10.0;
  static const lg = 14.0;
  static const xl = 18.0;
  static const xxl = 24.0;
}

ThemeData uellowThemeData() {
  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: UellowColors.yellow,
      primary: UellowColors.darkBrown,
      secondary: UellowColors.yellow,
      surface: Colors.white,
    ),
    scaffoldBackgroundColor: UellowColors.bg,
    fontFamily: 'SF Pro Display',
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      elevation: 0,
      iconTheme: IconThemeData(color: UellowColors.darkBrown),
      titleTextStyle: TextStyle(
        color: UellowColors.ink, fontWeight: FontWeight.w800, fontSize: 17,
      ),
      centerTitle: false,
    ),
    textTheme: const TextTheme(
      headlineLarge: TextStyle(color: UellowColors.ink, fontWeight: FontWeight.w800),
      headlineMedium: TextStyle(color: UellowColors.ink, fontWeight: FontWeight.w800),
      titleLarge:  TextStyle(color: UellowColors.ink, fontWeight: FontWeight.w800),
      titleMedium: TextStyle(color: UellowColors.ink, fontWeight: FontWeight.w700),
      bodyLarge:   TextStyle(color: UellowColors.text),
      bodyMedium:  TextStyle(color: UellowColors.text),
      bodySmall:   TextStyle(color: UellowColors.muted, fontSize: 11),
      labelLarge:  TextStyle(fontWeight: FontWeight.w800),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: UellowColors.darkBrown,
        foregroundColor: UellowColors.yellowLight,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        textStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
        shape: const RoundedRectangleBorder(borderRadius: UellowRadius.all_md),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: UellowColors.border,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      border: const OutlineInputBorder(
        borderRadius: UellowRadius.all_md, borderSide: BorderSide.none,
      ),
      focusedBorder: const OutlineInputBorder(
        borderRadius: UellowRadius.all_md,
        borderSide: BorderSide(color: UellowColors.yellow, width: 1.5),
      ),
    ),
    cardTheme: const CardThemeData(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: UellowRadius.all_lg),
    ),
    dividerTheme: const DividerThemeData(
      color: UellowColors.border, thickness: 1, space: 1,
    ),
  );
}

/// Helper: text style shortcuts used all over.
class UT {
  UT._();
  static const display = TextStyle(fontSize: 28, fontWeight: FontWeight.w900,
      color: UellowColors.darkBrown, letterSpacing: -0.3);
  static const h1 = TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: UellowColors.ink);
  static const h2 = TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: UellowColors.ink);
  static const h3 = TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: UellowColors.darkBrown);
  static const body = TextStyle(fontSize: 13.5, height: 1.5, color: UellowColors.text);
  static const small = TextStyle(fontSize: 11.5, color: UellowColors.muted);
  static const tiny = TextStyle(fontSize: 10, color: UellowColors.muted, fontWeight: FontWeight.w700);
  static const price = TextStyle(fontSize: 17, fontWeight: FontWeight.w900,
      color: UellowColors.darkBrown, letterSpacing: -0.3);
  static const button = TextStyle(fontSize: 14, fontWeight: FontWeight.w800);
}
