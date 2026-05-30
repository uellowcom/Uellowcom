// =============================================================================
// Typed models for the v2 API
// =============================================================================
//
// Every model is plain-old Dart — no codegen, no build runner, fast to read.
// All bilingual text uses [UellowText] which exposes `.en`, `.ar`, and
// `.current(lang)`. Pass the active app language to `.current()` and you
// don't have to think about l10n again.
//
// Naming convention:
//   *Card    → list / slider items                    (compact)
//   *Full    → detail-page record                     (rich)
//   *Summary → list-page record for orders/reviews   (medium)
// =============================================================================

// ─── Helpers ─────────────────────────────────────────────────────────

class UellowText {
  final String en;
  final String ar;
  const UellowText(this.en, this.ar);

  factory UellowText.fromJson(dynamic v) {
    if (v is Map) {
      return UellowText(
        (v['en'] ?? '').toString(),
        (v['ar'] ?? v['en'] ?? '').toString(),
      );
    }
    final s = (v ?? '').toString();
    return UellowText(s, s);
  }

  String current(String lang) =>
      lang.toLowerCase().startsWith('ar') ? (ar.isEmpty ? en : ar) : en;

  @override
  String toString() => en;
}

class UellowMoney {
  final double amount;
  final String currency;
  final String symbol;
  final int digits;
  const UellowMoney({
    required this.amount,
    required this.currency,
    required this.symbol,
    this.digits = 3,
  });

  factory UellowMoney.fromJson(Map<String, dynamic> j) => UellowMoney(
        amount: (j['amount'] ?? 0).toDouble(),
        currency: (j['currency'] ?? 'KWD').toString(),
        symbol: (j['symbol'] ?? 'KD').toString(),
        digits: (j['digits'] ?? 3) as int,
      );

  String format() => '${amount.toStringAsFixed(digits)} $symbol';
}

class UellowPage<T> {
  final List<T> items;
  final int page;
  final int perPage;
  final int total;
  final int pages;
  final bool hasNext;
  const UellowPage({
    required this.items,
    required this.page,
    required this.perPage,
    required this.total,
    required this.pages,
    required this.hasNext,
  });

  factory UellowPage.fromJson(
      Map<String, dynamic> envelope, T Function(Map<String, dynamic>) ctor) {
    final list = (envelope['data'] as List? ?? const [])
        .map<T>((e) => ctor(e as Map<String, dynamic>))
        .toList();
    final meta = (envelope['meta'] as Map<String, dynamic>?) ?? const {};
    return UellowPage(
      items: list,
      page:    (meta['page'] ?? 1) as int,
      perPage: (meta['per_page'] ?? list.length) as int,
      total:   (meta['total'] ?? list.length) as int,
      pages:   (meta['pages'] ?? 1) as int,
      hasNext: (meta['has_next'] ?? false) as bool,
    );
  }
}

// ─── Auth ────────────────────────────────────────────────────────────

class UellowAuthResult {
  final String token;
  final UellowUser user;
  const UellowAuthResult({required this.token, required this.user});
}

class UellowUser {
  final int id;
  final int? userId;
  final String name;
  final String email;
  final String phone;
  final String avatar;
  final bool isCompany;
  final String? country;
  final String lang;
  final double walletBalance;
  final int loyaltyPoints;
  final int addressesCount;

  const UellowUser({
    required this.id,
    this.userId,
    required this.name,
    required this.email,
    required this.phone,
    required this.avatar,
    required this.isCompany,
    this.country,
    required this.lang,
    required this.walletBalance,
    required this.loyaltyPoints,
    required this.addressesCount,
  });

  factory UellowUser.fromJson(Map<String, dynamic> j) => UellowUser(
        id:        (j['id'] ?? 0) as int,
        userId:    j['user_id'] as int?,
        name:      (j['name'] ?? '').toString(),
        email:     (j['email'] ?? '').toString(),
        phone:     (j['phone'] ?? '').toString(),
        avatar:    (j['avatar'] ?? '').toString(),
        isCompany: (j['is_company'] ?? false) as bool,
        country:   j['country'] as String?,
        lang:      (j['lang'] ?? 'en_US').toString(),
        walletBalance: (j['wallet_balance'] ?? 0).toDouble(),
        loyaltyPoints: (j['loyalty_points'] ?? 0) as int,
        addressesCount: (j['addresses_count'] ?? 0) as int,
      );
}

// ─── Home ────────────────────────────────────────────────────────────

class UellowHome {
  final List<UellowSlider> sliders;
  final List<UellowCategoryIcon> categoryIcons;
  final List<UellowFeatureBanner> featureBanners;
  final List<UellowSection> sections;
  final List<UellowPopup> popups;
  const UellowHome({
    required this.sliders,
    required this.categoryIcons,
    required this.featureBanners,
    required this.sections,
    required this.popups,
  });
  factory UellowHome.fromJson(Map<String, dynamic> j) => UellowHome(
        sliders:        (j['sliders'] as List? ?? []).map((e) => UellowSlider.fromJson(e)).toList(),
        categoryIcons:  (j['category_icons'] as List? ?? []).map((e) => UellowCategoryIcon.fromJson(e)).toList(),
        featureBanners: (j['feature_banners'] as List? ?? []).map((e) => UellowFeatureBanner.fromJson(e)).toList(),
        sections:       (j['sections'] as List? ?? []).map((e) => UellowSection.fromJson(e)).toList(),
        popups:         (j['popups'] as List? ?? []).map((e) => UellowPopup.fromJson(e)).toList(),
      );
}

class UellowSlider {
  final int id;
  final UellowText title;
  final UellowText subtitle;
  final String imageUrl;
  final String actionType;
  final dynamic actionValue;
  final UellowText? ctaLabel;
  const UellowSlider({
    required this.id, required this.title, required this.subtitle,
    required this.imageUrl, required this.actionType, this.actionValue,
    this.ctaLabel,
  });
  factory UellowSlider.fromJson(Map<String, dynamic> j) => UellowSlider(
        id: (j['id'] ?? 0) as int,
        title: UellowText.fromJson(j['title']),
        subtitle: UellowText.fromJson(j['subtitle'] ?? {'en': '', 'ar': ''}),
        imageUrl: (j['image_url'] ?? '').toString(),
        actionType: (j['action_type'] ?? '').toString(),
        actionValue: j['action_value'],
        ctaLabel: j['cta_label'] != null ? UellowText.fromJson(j['cta_label']) : null,
      );
}

class UellowCategoryIcon {
  final int id;
  final UellowText label;
  final String iconUrl;
  final String actionType;
  final dynamic actionValue;
  const UellowCategoryIcon({
    required this.id, required this.label, required this.iconUrl,
    required this.actionType, this.actionValue,
  });
  factory UellowCategoryIcon.fromJson(Map<String, dynamic> j) => UellowCategoryIcon(
        id: (j['id'] ?? 0) as int,
        label: UellowText.fromJson(j['label']),
        iconUrl: (j['icon_url'] ?? '').toString(),
        actionType: (j['action_type'] ?? '').toString(),
        actionValue: j['action_value'],
      );
}

class UellowFeatureBanner {
  final int id;
  final UellowText title;
  final UellowText subtitle;
  final String iconType;
  final String iconEmoji;
  final String? iconUrl;
  final String? backgroundColor;
  final String? textColor;
  const UellowFeatureBanner({
    required this.id, required this.title, required this.subtitle,
    required this.iconType, required this.iconEmoji,
    this.iconUrl, this.backgroundColor, this.textColor,
  });
  factory UellowFeatureBanner.fromJson(Map<String, dynamic> j) => UellowFeatureBanner(
        id: (j['id'] ?? 0) as int,
        title: UellowText.fromJson(j['title']),
        subtitle: UellowText.fromJson(j['subtitle']),
        iconType: (j['icon_type'] ?? '').toString(),
        iconEmoji: (j['icon_emoji'] ?? '').toString(),
        iconUrl: j['icon_url'] as String?,
        backgroundColor: j['background_color'] as String?,
        textColor: j['text_color'] as String?,
      );
}

class UellowSection {
  final int id;
  final UellowText title;
  final String sectionType;
  final String displayStyle;
  final bool showDiscountBadge;
  final bool showSoldCount;
  final bool showRating;
  final bool showViewMore;
  final bool showTimer;
  final String? timerEnd;
  final int maxProducts;
  final String moreActionType;
  final dynamic moreActionValue;
  final String productsEndpoint;
  const UellowSection({
    required this.id, required this.title, required this.sectionType,
    required this.displayStyle, required this.showDiscountBadge,
    required this.showSoldCount, required this.showRating,
    required this.showViewMore, required this.showTimer, this.timerEnd,
    required this.maxProducts, required this.moreActionType,
    this.moreActionValue, required this.productsEndpoint,
  });
  factory UellowSection.fromJson(Map<String, dynamic> j) => UellowSection(
        id: (j['id'] ?? 0) as int,
        title: UellowText.fromJson(j['title']),
        sectionType: (j['section_type'] ?? '').toString(),
        displayStyle: (j['display_style'] ?? '').toString(),
        showDiscountBadge: (j['show_discount_badge'] ?? false) as bool,
        showSoldCount:     (j['show_sold_count'] ?? false) as bool,
        showRating:        (j['show_rating'] ?? false) as bool,
        showViewMore:      (j['show_view_more'] ?? false) as bool,
        showTimer:         (j['show_timer'] ?? false) as bool,
        timerEnd:          j['timer_end'] as String?,
        maxProducts:       (j['max_products'] ?? 20) as int,
        moreActionType:    (j['more_action_type'] ?? '').toString(),
        moreActionValue:   j['more_action_value'],
        productsEndpoint:  (j['products_endpoint'] ?? '').toString(),
      );
}

class UellowPopup {
  final int id;
  final UellowText name;
  final String imageUrl;
  final String trigger;
  final String frequency;
  final String actionType;
  final dynamic actionValue;
  const UellowPopup({
    required this.id, required this.name, required this.imageUrl,
    required this.trigger, required this.frequency,
    required this.actionType, this.actionValue,
  });
  factory UellowPopup.fromJson(Map<String, dynamic> j) => UellowPopup(
        id: (j['id'] ?? 0) as int,
        name: UellowText.fromJson(j['name']),
        imageUrl: (j['image_url'] ?? '').toString(),
        trigger: (j['trigger'] ?? '').toString(),
        frequency: (j['frequency'] ?? '').toString(),
        actionType: (j['action_type'] ?? '').toString(),
        actionValue: j['action_value'],
      );
}

// ─── Products ────────────────────────────────────────────────────────

class UellowRating {
  final double avg;
  final int count;
  const UellowRating({required this.avg, required this.count});
  factory UellowRating.fromJson(Map<String, dynamic> j) => UellowRating(
        avg: (j['avg'] ?? 0).toDouble(),
        count: (j['count'] ?? 0) as int,
      );
}

class UellowProductCard {
  final int id;
  final UellowText name;
  final String slug;
  final String image;
  final UellowMoney price;
  final UellowMoney? comparePrice;
  final int discountPct;
  final bool inStock;
  final int? qtyAvailable;
  final UellowRating rating;
  final bool isPublished;
  final List<String> badges;

  const UellowProductCard({
    required this.id, required this.name, required this.slug,
    required this.image, required this.price, this.comparePrice,
    required this.discountPct, required this.inStock, this.qtyAvailable,
    required this.rating, required this.isPublished, required this.badges,
  });

  factory UellowProductCard.fromJson(Map<String, dynamic> j) => UellowProductCard(
        id: (j['id'] ?? 0) as int,
        name: UellowText.fromJson(j['name']),
        slug: (j['slug'] ?? '').toString(),
        image: (j['image'] ?? '').toString(),
        price: UellowMoney.fromJson(j['price'] as Map<String, dynamic>),
        comparePrice: j['compare_price'] == null
            ? null
            : UellowMoney.fromJson(j['compare_price'] as Map<String, dynamic>),
        discountPct: (j['discount_pct'] ?? 0) as int,
        inStock:     (j['in_stock'] ?? true) as bool,
        qtyAvailable: j['qty_available'] as int?,
        rating: UellowRating.fromJson(
            (j['rating'] as Map<String, dynamic>?) ?? const {}),
        isPublished: (j['is_published'] ?? true) as bool,
        badges: List<String>.from((j['badges'] as List?) ?? const []),
      );
}

class UellowProductFull extends UellowProductCard {
  final UellowText descriptionShort;
  final UellowText descriptionHtml;
  final List<String> images;
  final List<UellowAttributeLine> attributes;
  final List<UellowCategoryRef> categories;
  final String sku;
  final String barcode;
  final int warrantyMonths;
  final UellowText shippingInfoLabel;

  UellowProductFull({
    required int id, required UellowText name, required String slug,
    required String image, required UellowMoney price,
    UellowMoney? comparePrice, required int discountPct,
    required bool inStock, int? qtyAvailable, required UellowRating rating,
    required bool isPublished, required List<String> badges,
    required this.descriptionShort, required this.descriptionHtml,
    required this.images, required this.attributes,
    required this.categories, required this.sku, required this.barcode,
    required this.warrantyMonths, required this.shippingInfoLabel,
  }) : super(
            id: id, name: name, slug: slug, image: image, price: price,
            comparePrice: comparePrice, discountPct: discountPct,
            inStock: inStock, qtyAvailable: qtyAvailable, rating: rating,
            isPublished: isPublished, badges: badges);

  factory UellowProductFull.fromJson(Map<String, dynamic> j) => UellowProductFull(
        id: (j['id'] ?? 0) as int,
        name: UellowText.fromJson(j['name']),
        slug: (j['slug'] ?? '').toString(),
        image: (j['image'] ?? '').toString(),
        price: UellowMoney.fromJson(j['price'] as Map<String, dynamic>),
        comparePrice: j['compare_price'] == null
            ? null
            : UellowMoney.fromJson(j['compare_price'] as Map<String, dynamic>),
        discountPct: (j['discount_pct'] ?? 0) as int,
        inStock:     (j['in_stock'] ?? true) as bool,
        qtyAvailable: j['qty_available'] as int?,
        rating: UellowRating.fromJson(
            (j['rating'] as Map<String, dynamic>?) ?? const {}),
        isPublished: (j['is_published'] ?? true) as bool,
        badges: List<String>.from((j['badges'] as List?) ?? const []),
        descriptionShort: UellowText.fromJson(j['description_short']),
        descriptionHtml:  UellowText.fromJson(j['description_html']),
        images: List<String>.from((j['images'] as List?) ?? const []),
        attributes: ((j['attributes'] as List?) ?? const [])
            .map((e) => UellowAttributeLine.fromJson(e))
            .toList(),
        categories: ((j['categories'] as List?) ?? const [])
            .map((e) => UellowCategoryRef.fromJson(e))
            .toList(),
        sku: (j['sku'] ?? '').toString(),
        barcode: (j['barcode'] ?? '').toString(),
        warrantyMonths: (j['warranty_months'] ?? 12) as int,
        shippingInfoLabel: UellowText.fromJson(j['shipping_info_label']),
      );
}

class UellowAttributeLine {
  final int attributeId;
  final UellowText attributeName;
  final String displayType;
  final List<UellowAttributeValue> values;
  const UellowAttributeLine({
    required this.attributeId, required this.attributeName,
    required this.displayType, required this.values,
  });
  factory UellowAttributeLine.fromJson(Map<String, dynamic> j) =>
      UellowAttributeLine(
        attributeId: (j['attribute_id'] ?? 0) as int,
        attributeName: UellowText.fromJson(j['attribute_name']),
        displayType: (j['display_type'] ?? '').toString(),
        values: ((j['values'] as List?) ?? const [])
            .map((e) => UellowAttributeValue.fromJson(e))
            .toList(),
      );
}

class UellowAttributeValue {
  final int id;
  final UellowText name;
  final String htmlColor;
  final String? image;
  const UellowAttributeValue({
    required this.id, required this.name, required this.htmlColor, this.image,
  });
  factory UellowAttributeValue.fromJson(Map<String, dynamic> j) =>
      UellowAttributeValue(
        id: (j['id'] ?? 0) as int,
        name: UellowText.fromJson(j['name']),
        htmlColor: (j['html_color'] ?? '').toString(),
        image: j['image'] as String?,
      );
}

class UellowCategoryRef {
  final int id;
  final UellowText name;
  const UellowCategoryRef({required this.id, required this.name});
  factory UellowCategoryRef.fromJson(Map<String, dynamic> j) => UellowCategoryRef(
        id: (j['id'] ?? 0) as int,
        name: UellowText.fromJson(j['name']),
      );
}

class UellowProductVariant {
  final int id;
  final String sku;
  final String barcode;
  final UellowMoney price;
  final int? qtyAvailable;
  final bool inStock;
  final String image;
  final List<Map<String, dynamic>> attributes;
  const UellowProductVariant({
    required this.id, required this.sku, required this.barcode,
    required this.price, this.qtyAvailable, required this.inStock,
    required this.image, required this.attributes,
  });
  factory UellowProductVariant.fromJson(Map<String, dynamic> j) =>
      UellowProductVariant(
        id: (j['id'] ?? 0) as int,
        sku: (j['sku'] ?? '').toString(),
        barcode: (j['barcode'] ?? '').toString(),
        price: UellowMoney.fromJson(j['price'] as Map<String, dynamic>),
        qtyAvailable: j['qty_available'] as int?,
        inStock: (j['in_stock'] ?? true) as bool,
        image: (j['image'] ?? '').toString(),
        attributes: List<Map<String, dynamic>>.from(
            (j['attributes'] as List?) ?? const []),
      );
}

// ─── Categories ──────────────────────────────────────────────────────

class UellowCategory {
  final int id;
  final UellowText name;
  final int? parentId;
  final String? image;
  final int productCount;
  final List<UellowCategory> children;
  const UellowCategory({
    required this.id, required this.name, this.parentId, this.image,
    required this.productCount, required this.children,
  });
  factory UellowCategory.fromJson(Map<String, dynamic> j) => UellowCategory(
        id: (j['id'] ?? 0) as int,
        name: UellowText.fromJson(j['name']),
        parentId: j['parent_id'] as int?,
        image: j['image'] as String?,
        productCount: (j['product_count'] ?? 0) as int,
        children: ((j['children'] as List?) ?? const [])
            .map((e) => UellowCategory.fromJson(e))
            .toList(),
      );
}

// ─── Cart ────────────────────────────────────────────────────────────

class UellowCart {
  final int? orderId;
  final String cartToken;
  final String currency;
  final List<UellowCartLine> lines;
  final int lineCount;
  final UellowCartTotals totals;
  final List<String> coupons;
  const UellowCart({
    this.orderId, required this.cartToken, required this.currency,
    required this.lines, required this.lineCount, required this.totals,
    required this.coupons,
  });
  factory UellowCart.fromJson(Map<String, dynamic> j) => UellowCart(
        orderId: j['order_id'] as int?,
        cartToken: (j['cart_token'] ?? '').toString(),
        currency: (j['currency'] ?? '').toString(),
        lines: ((j['lines'] as List?) ?? const [])
            .map((e) => UellowCartLine.fromJson(e))
            .toList(),
        lineCount: (j['line_count'] ?? 0) as int,
        totals: UellowCartTotals.fromJson(j['totals'] as Map<String, dynamic>),
        coupons: List<String>.from((j['coupons'] as List?) ?? const []),
      );
}

class UellowCartLine {
  final int id;
  final int productId;
  final int variantId;
  final UellowText name;
  final String sku;
  final String image;
  final double qty;
  final UellowMoney unitPrice;
  final UellowMoney subtotal;
  final UellowMoney total;
  final List<Map<String, dynamic>> attributes;
  const UellowCartLine({
    required this.id, required this.productId, required this.variantId,
    required this.name, required this.sku, required this.image,
    required this.qty, required this.unitPrice, required this.subtotal,
    required this.total, required this.attributes,
  });
  factory UellowCartLine.fromJson(Map<String, dynamic> j) => UellowCartLine(
        id: (j['id'] ?? 0) as int,
        productId: (j['product_id'] ?? 0) as int,
        variantId: (j['variant_id'] ?? 0) as int,
        name: UellowText.fromJson(j['name']),
        sku: (j['sku'] ?? '').toString(),
        image: (j['image'] ?? '').toString(),
        qty: (j['qty'] ?? 0).toDouble(),
        unitPrice: UellowMoney.fromJson(j['unit_price'] as Map<String, dynamic>),
        subtotal: UellowMoney.fromJson(j['subtotal'] as Map<String, dynamic>),
        total: UellowMoney.fromJson(j['total'] as Map<String, dynamic>),
        attributes: List<Map<String, dynamic>>.from(
            (j['attributes'] as List?) ?? const []),
      );
}

class UellowCartTotals {
  final UellowMoney subtotal;
  final UellowMoney tax;
  final UellowMoney shipping;
  final UellowMoney discount;
  final UellowMoney total;
  const UellowCartTotals({
    required this.subtotal, required this.tax, required this.shipping,
    required this.discount, required this.total,
  });
  factory UellowCartTotals.fromJson(Map<String, dynamic> j) => UellowCartTotals(
        subtotal: UellowMoney.fromJson(j['subtotal'] as Map<String, dynamic>),
        tax:      UellowMoney.fromJson(j['tax'] as Map<String, dynamic>),
        shipping: UellowMoney.fromJson(j['shipping'] as Map<String, dynamic>),
        discount: UellowMoney.fromJson(j['discount'] as Map<String, dynamic>),
        total:    UellowMoney.fromJson(j['total'] as Map<String, dynamic>),
      );
}

// ─── Orders ──────────────────────────────────────────────────────────

class UellowOrderSummary {
  final int id;
  final String name;
  final String state;
  final UellowText stateLabel;
  final String? date;
  final UellowMoney total;
  final int lineCount;
  const UellowOrderSummary({
    required this.id, required this.name, required this.state,
    required this.stateLabel, this.date, required this.total,
    required this.lineCount,
  });
  factory UellowOrderSummary.fromJson(Map<String, dynamic> j) => UellowOrderSummary(
        id: (j['id'] ?? 0) as int,
        name: (j['name'] ?? '').toString(),
        state: (j['state'] ?? '').toString(),
        stateLabel: UellowText.fromJson(j['state_label']),
        date: j['date'] as String?,
        total: UellowMoney.fromJson(j['total'] as Map<String, dynamic>),
        lineCount: (j['line_count'] ?? 0) as int,
      );
}

class UellowOrderDetail extends UellowOrderSummary {
  final List<UellowCartLine> lines;
  final UellowMoney subtotal;
  final UellowMoney tax;
  final UellowMoney shipping;
  final UellowAddress? deliveryAddress;
  final UellowAddress? invoiceAddress;
  final Map<String, dynamic> payment;
  final String trackingNumber;
  final String carrier;

  UellowOrderDetail({
    required int id, required String name, required String state,
    required UellowText stateLabel, String? date,
    required UellowMoney total, required int lineCount,
    required this.lines, required this.subtotal, required this.tax,
    required this.shipping, this.deliveryAddress, this.invoiceAddress,
    required this.payment, required this.trackingNumber, required this.carrier,
  }) : super(
            id: id, name: name, state: state, stateLabel: stateLabel,
            date: date, total: total, lineCount: lineCount);

  factory UellowOrderDetail.fromJson(Map<String, dynamic> j) => UellowOrderDetail(
        id: (j['id'] ?? 0) as int,
        name: (j['name'] ?? '').toString(),
        state: (j['state'] ?? '').toString(),
        stateLabel: UellowText.fromJson(j['state_label']),
        date: j['date'] as String?,
        total: UellowMoney.fromJson(j['total'] as Map<String, dynamic>),
        lineCount: (j['line_count'] ?? 0) as int,
        lines: ((j['lines'] as List?) ?? const [])
            .map((e) => UellowCartLine.fromJson(e))
            .toList(),
        subtotal: UellowMoney.fromJson(j['subtotal'] as Map<String, dynamic>),
        tax: UellowMoney.fromJson(j['tax'] as Map<String, dynamic>),
        shipping: UellowMoney.fromJson(j['shipping'] as Map<String, dynamic>),
        deliveryAddress: j['delivery_address'] == null ? null
            : UellowAddress.fromJson(j['delivery_address']),
        invoiceAddress: j['invoice_address'] == null ? null
            : UellowAddress.fromJson(j['invoice_address']),
        payment: Map<String, dynamic>.from((j['payment'] as Map?) ?? const {}),
        trackingNumber: (j['tracking_number'] ?? '').toString(),
        carrier: (j['carrier'] ?? '').toString(),
      );
}

class UellowShippingMethod {
  final int id;
  final UellowText name;
  final UellowMoney price;
  final bool isDefault;
  final String? logo;
  const UellowShippingMethod({
    required this.id, required this.name, required this.price,
    required this.isDefault, this.logo,
  });
  factory UellowShippingMethod.fromJson(Map<String, dynamic> j) =>
      UellowShippingMethod(
        id: (j['id'] ?? 0) as int,
        name: UellowText.fromJson(j['name']),
        price: UellowMoney.fromJson(j['price'] as Map<String, dynamic>),
        isDefault: (j['is_default'] ?? false) as bool,
        logo: j['logo'] as String?,
      );
}

class UellowPaymentMethod {
  final int id;
  final String name;
  final String code;
  final String? image;
  final bool isDefault;
  const UellowPaymentMethod({
    required this.id, required this.name, required this.code,
    this.image, required this.isDefault,
  });
  factory UellowPaymentMethod.fromJson(Map<String, dynamic> j) => UellowPaymentMethod(
        id: (j['id'] ?? 0) as int,
        name: (j['name'] ?? '').toString(),
        code: (j['code'] ?? '').toString(),
        image: j['image'] as String?,
        isDefault: (j['is_default'] ?? false) as bool,
      );
}

class UellowCheckoutSummary {
  final UellowCart cart;
  final List<UellowAddress> addresses;
  const UellowCheckoutSummary({required this.cart, required this.addresses});
  factory UellowCheckoutSummary.fromJson(Map<String, dynamic> j) =>
      UellowCheckoutSummary(
        cart: UellowCart.fromJson(j['cart'] as Map<String, dynamic>),
        addresses: ((j['addresses'] as List?) ?? const [])
            .map((e) => UellowAddress.fromJson(e))
            .toList(),
      );
}

class UellowCheckoutConfirm {
  final int orderId;
  final String orderName;
  final bool paymentRequired;
  final String? paymentUrl;
  const UellowCheckoutConfirm({
    required this.orderId, required this.orderName,
    required this.paymentRequired, this.paymentUrl,
  });
  factory UellowCheckoutConfirm.fromJson(Map<String, dynamic> j) =>
      UellowCheckoutConfirm(
        orderId: (j['order_id'] ?? 0) as int,
        orderName: (j['order_name'] ?? '').toString(),
        paymentRequired: (j['payment_required'] ?? false) as bool,
        paymentUrl: j['payment_url'] as String?,
      );
}

// ─── Addresses ───────────────────────────────────────────────────────

class UellowAddress {
  final int id;
  final String name;
  final String phone;
  final String street;
  final String street2;
  final String city;
  final int? stateId;
  final String state;
  final int? countryId;
  final String country;
  final String zip;
  final String type;
  final bool isDefault;
  const UellowAddress({
    required this.id, required this.name, required this.phone,
    required this.street, required this.street2, required this.city,
    this.stateId, required this.state, this.countryId, required this.country,
    required this.zip, required this.type, required this.isDefault,
  });
  factory UellowAddress.fromJson(Map<String, dynamic> j) => UellowAddress(
        id: (j['id'] ?? 0) as int,
        name: (j['name'] ?? '').toString(),
        phone: (j['phone'] ?? '').toString(),
        street: (j['street'] ?? '').toString(),
        street2: (j['street2'] ?? '').toString(),
        city: (j['city'] ?? '').toString(),
        stateId: j['state_id'] as int?,
        state: (j['state'] ?? '').toString(),
        countryId: j['country_id'] as int?,
        country: (j['country'] ?? '').toString(),
        zip: (j['zip'] ?? '').toString(),
        type: (j['type'] ?? 'contact').toString(),
        isDefault: (j['is_default'] ?? false) as bool,
      );
}

// ─── Search ──────────────────────────────────────────────────────────

class UellowSearchResult {
  final List<UellowProductCard> products;
  final List<UellowCategoryRef> categories;
  final List<String> suggestions;
  const UellowSearchResult({
    required this.products, required this.categories, required this.suggestions,
  });
  factory UellowSearchResult.fromJson(Map<String, dynamic> env) {
    final d = env['data'] as Map<String, dynamic>;
    return UellowSearchResult(
      products: ((d['products'] as List?) ?? const [])
          .map((e) => UellowProductCard.fromJson(e))
          .toList(),
      categories: ((d['categories'] as List?) ?? const [])
          .map((e) => UellowCategoryRef.fromJson(e))
          .toList(),
      suggestions: List<String>.from((d['suggestions'] as List?) ?? const []),
    );
  }
}

class UellowPopularQuery {
  final String query;
  final int count;
  const UellowPopularQuery({required this.query, required this.count});
  factory UellowPopularQuery.fromJson(Map<String, dynamic> j) =>
      UellowPopularQuery(
        query: (j['query'] ?? '').toString(),
        count: (j['count'] ?? 0) as int,
      );
}

// ─── Reviews ─────────────────────────────────────────────────────────

class UellowReview {
  final int id;
  final double rating;
  final String title;
  final String body;
  final String author;
  final String? date;
  final bool verifiedPurchase;
  const UellowReview({
    required this.id, required this.rating, required this.title,
    required this.body, required this.author, this.date,
    required this.verifiedPurchase,
  });
  factory UellowReview.fromJson(Map<String, dynamic> j) => UellowReview(
        id: (j['id'] ?? 0) as int,
        rating: (j['rating'] ?? 0).toDouble(),
        title: (j['title'] ?? '').toString(),
        body: (j['body'] ?? '').toString(),
        author: (j['author'] ?? '').toString(),
        date: j['date'] as String?,
        verifiedPurchase: (j['verified_purchase'] ?? false) as bool,
      );
}

class UellowReviewsResult {
  final List<UellowReview> reviews;
  final UellowRating summary;
  const UellowReviewsResult({required this.reviews, required this.summary});
  factory UellowReviewsResult.fromJson(Map<String, dynamic> env) {
    final d = env['data'] as Map<String, dynamic>;
    return UellowReviewsResult(
      reviews: ((d['reviews'] as List?) ?? const [])
          .map((e) => UellowReview.fromJson(e))
          .toList(),
      summary: UellowRating.fromJson(
          (d['summary'] as Map<String, dynamic>?) ?? const {}),
    );
  }
}

class UellowMyReview {
  final int id;
  final int productId;
  final String productName;
  final double rating;
  final String title;
  final String body;
  final bool approved;
  final String? date;
  const UellowMyReview({
    required this.id, required this.productId, required this.productName,
    required this.rating, required this.title, required this.body,
    required this.approved, this.date,
  });
  factory UellowMyReview.fromJson(Map<String, dynamic> j) => UellowMyReview(
        id: (j['id'] ?? 0) as int,
        productId: (j['product_id'] ?? 0) as int,
        productName: (j['product_name'] ?? '').toString(),
        rating: (j['rating'] ?? 0).toDouble(),
        title: (j['title'] ?? '').toString(),
        body: (j['body'] ?? '').toString(),
        approved: (j['approved'] ?? false) as bool,
        date: j['date'] as String?,
      );
}

// ─── Loyalty + Wallet ────────────────────────────────────────────────

class UellowLoyalty {
  final int points;
  final String tier;
  final UellowText tierLabel;
  final String? nextTier;
  final int? nextThreshold;
  final int progressPct;
  final int redeemRate;
  final UellowMoney kdValue;
  const UellowLoyalty({
    required this.points, required this.tier, required this.tierLabel,
    this.nextTier, this.nextThreshold, required this.progressPct,
    required this.redeemRate, required this.kdValue,
  });
  factory UellowLoyalty.fromJson(Map<String, dynamic> j) => UellowLoyalty(
        points: (j['points'] ?? 0) as int,
        tier: (j['tier'] ?? 'bronze').toString(),
        tierLabel: UellowText.fromJson(j['tier_label']),
        nextTier: j['next_tier'] as String?,
        nextThreshold: j['next_threshold'] as int?,
        progressPct: (j['progress_pct'] ?? 0) as int,
        redeemRate: (j['redeem_rate'] ?? 100) as int,
        kdValue: UellowMoney.fromJson(j['kd_value'] as Map<String, dynamic>),
      );
}

class UellowWalletTx {
  final int id;
  final UellowMoney amount;
  final String type;
  final String? date;
  final String description;
  final String status;
  const UellowWalletTx({
    required this.id, required this.amount, required this.type,
    this.date, required this.description, required this.status,
  });
  factory UellowWalletTx.fromJson(Map<String, dynamic> j) => UellowWalletTx(
        id: (j['id'] ?? 0) as int,
        amount: UellowMoney.fromJson(j['amount'] as Map<String, dynamic>),
        type: (j['type'] ?? '').toString(),
        date: j['date'] as String?,
        description: (j['description'] ?? '').toString(),
        status: (j['status'] ?? '').toString(),
      );
}

// ─── Notifications ───────────────────────────────────────────────────

class UellowNotification {
  final int id;
  final String title;
  final String body;
  final String image;
  final Map<String, dynamic> data;
  final bool isRead;
  final String? date;
  const UellowNotification({
    required this.id, required this.title, required this.body,
    required this.image, required this.data, required this.isRead, this.date,
  });
  factory UellowNotification.fromJson(Map<String, dynamic> j) => UellowNotification(
        id: (j['id'] ?? 0) as int,
        title: (j['title'] ?? '').toString(),
        body: (j['body'] ?? '').toString(),
        image: (j['image'] ?? '').toString(),
        data: Map<String, dynamic>.from((j['data'] as Map?) ?? const {}),
        isRead: (j['is_read'] ?? false) as bool,
        date: j['date'] as String?,
      );
}

// ─── App settings + lookups ──────────────────────────────────────────

class UellowAppSettings {
  final String appName;
  final String? logoUrl;
  final String primaryColor;
  final String darkColor;
  final String supportEmail;
  final String supportPhone;
  final String whatsapp;
  final bool forceUpdate;
  final String minVersion;
  final bool maintenance;
  final String maintenanceMessage;
  final Map<String, dynamic> social;
  final Map<String, dynamic> urls;
  final Map<String, dynamic> features;
  final Map<String, dynamic> website;
  const UellowAppSettings({
    required this.appName, this.logoUrl, required this.primaryColor,
    required this.darkColor, required this.supportEmail, required this.supportPhone,
    required this.whatsapp, required this.forceUpdate, required this.minVersion,
    required this.maintenance, required this.maintenanceMessage,
    required this.social, required this.urls,
    required this.features, required this.website,
  });
  factory UellowAppSettings.fromJson(Map<String, dynamic> j) => UellowAppSettings(
        appName: (j['app_name'] ?? '').toString(),
        logoUrl: j['logo_url'] as String?,
        primaryColor: (j['primary_color'] ?? '#F5C320').toString(),
        darkColor: (j['dark_color'] ?? '#412402').toString(),
        supportEmail: (j['support_email'] ?? '').toString(),
        supportPhone: (j['support_phone'] ?? '').toString(),
        whatsapp: (j['whatsapp'] ?? '').toString(),
        forceUpdate: (j['force_update'] ?? false) as bool,
        minVersion: (j['min_version'] ?? '').toString(),
        maintenance: (j['maintenance'] ?? false) as bool,
        maintenanceMessage: (j['maintenance_message'] ?? '').toString(),
        social:   Map<String, dynamic>.from((j['social']   as Map?) ?? const {}),
        urls:     Map<String, dynamic>.from((j['urls']     as Map?) ?? const {}),
        features: Map<String, dynamic>.from((j['features'] as Map?) ?? const {}),
        website:  Map<String, dynamic>.from((j['website']  as Map?) ?? const {}),
      );
}

class UellowCountry {
  final int id;
  final String name;
  final String code;
  final String? phoneCode;
  final String? flag;
  const UellowCountry({
    required this.id, required this.name, required this.code,
    this.phoneCode, this.flag,
  });
  factory UellowCountry.fromJson(Map<String, dynamic> j) => UellowCountry(
        id: (j['id'] ?? 0) as int,
        name: (j['name'] ?? '').toString(),
        code: (j['code'] ?? '').toString(),
        phoneCode: j['phone_code']?.toString(),
        flag: j['flag'] as String?,
      );
}

class UellowState {
  final int id;
  final String name;
  final String code;
  final int countryId;
  const UellowState({
    required this.id, required this.name, required this.code,
    required this.countryId,
  });
  factory UellowState.fromJson(Map<String, dynamic> j) => UellowState(
        id: (j['id'] ?? 0) as int,
        name: (j['name'] ?? '').toString(),
        code: (j['code'] ?? '').toString(),
        countryId: (j['country_id'] ?? 0) as int,
      );
}

class UellowVersionCheck {
  final String currentClientVersion;
  final String minSupportedVersion;
  final String latestVersion;
  final bool forceUpdate;
  final String updateUrl;
  const UellowVersionCheck({
    required this.currentClientVersion, required this.minSupportedVersion,
    required this.latestVersion, required this.forceUpdate, required this.updateUrl,
  });
  factory UellowVersionCheck.fromJson(Map<String, dynamic> j) => UellowVersionCheck(
        currentClientVersion: (j['current_client_version'] ?? '').toString(),
        minSupportedVersion:  (j['min_supported_version'] ?? '').toString(),
        latestVersion:        (j['latest_version'] ?? '').toString(),
        forceUpdate:          (j['force_update'] ?? false) as bool,
        updateUrl:            (j['update_url'] ?? '').toString(),
      );
}
