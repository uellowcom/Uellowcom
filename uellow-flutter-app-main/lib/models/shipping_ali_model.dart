class ShippingAli {
  String? state;
  List<Items>? items;

  ShippingAli({this.state, this.items});

  ShippingAli.fromJson(Map<String, dynamic> json) {
    state = json['state'];
    if (json['items'] != null) {
      items = <Items>[];
      json['items'].forEach((v) {
        items!.add(new Items.fromJson(v));
      });
    }
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['state'] = this.state;
    if (this.items != null) {
      data['items'] = this.items!.map((v) => v.toJson()).toList();
    }
    return data;
  }
}

class Items {
  BizShowMind? bizShowMind;
  String? commitDay;
  String? company;
  String? currency;
  String? deliveryDate;
  String? deliveryDateCopy;
  String? deliveryDateFormat;
  int? discount;
  dynamic features;
  FreightAmount? freightAmount;
  FreightLayout? freightLayout;
  bool? fullMailLine;
  bool? hbaService;
  String? notification;
  String? sendGoodsCountry;
  String? sendGoodsCountryFullName;
  String? serviceName;
  FreightAmount? standardFreightAmount;
  String? time;
  bool? tracking;
  String? priceFormatStr;
  String? localPriceFormatStr;

  Items(
      {this.bizShowMind,
      this.commitDay,
      this.company,
      this.currency,
      this.deliveryDate,
      this.deliveryDateCopy,
      this.deliveryDateFormat,
      this.discount,
      this.features,
      this.freightAmount,
      this.freightLayout,
      this.fullMailLine,
      this.hbaService,
      this.notification,
      this.sendGoodsCountry,
      this.sendGoodsCountryFullName,
      this.serviceName,
      this.standardFreightAmount,
      this.time,
      this.tracking,
      this.priceFormatStr,
      this.localPriceFormatStr});

  Items.fromJson(Map<String, dynamic> json) {
    bizShowMind = json['bizShowMind'] != null
        ? new BizShowMind.fromJson(json['bizShowMind'])
        : null;
    commitDay = json['commitDay'];
    company = json['company'];
    currency = json['currency'];
    deliveryDate = json['deliveryDate'];
    deliveryDateCopy = json['deliveryDateCopy'];
    deliveryDateFormat = json['deliveryDateFormat'];
    discount = json['discount'];
    if (json['features'] != null) {
      features = json['features'];
    }
    freightAmount = json['freightAmount'] != null
        ? new FreightAmount.fromJson(json['freightAmount'])
        : null;
    freightLayout = json['freightLayout'] != null
        ? new FreightLayout.fromJson(json['freightLayout'])
        : null;
    fullMailLine = json['fullMailLine'];
    hbaService = json['hbaService'];
    notification = json['notification'];
    sendGoodsCountry = json['sendGoodsCountry'];
    sendGoodsCountryFullName = json['sendGoodsCountryFullName'];
    serviceName = json['serviceName'];
    standardFreightAmount = json['standardFreightAmount'] != null
        ? new FreightAmount.fromJson(json['standardFreightAmount'])
        : null;
    time = json['time'];
    tracking = json['tracking'];
    priceFormatStr = json['priceFormatStr'];
    localPriceFormatStr = json['localPriceFormatStr'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    if (this.bizShowMind != null) {
      data['bizShowMind'] = this.bizShowMind!.toJson();
    }
    data['commitDay'] = this.commitDay;
    data['company'] = this.company;
    data['currency'] = this.currency;
    data['deliveryDate'] = this.deliveryDate;
    data['deliveryDateCopy'] = this.deliveryDateCopy;
    data['deliveryDateFormat'] = this.deliveryDateFormat;
    data['discount'] = this.discount;
    if (this.features != null) {
      data['features'] = this.features;
    }
    if (this.freightAmount != null) {
      data['freightAmount'] = this.freightAmount!.toJson();
    }
    if (this.freightLayout != null) {
      data['freightLayout'] = this.freightLayout!.toJson();
    }
    data['fullMailLine'] = this.fullMailLine;
    data['hbaService'] = this.hbaService;
    data['notification'] = this.notification;
    data['sendGoodsCountry'] = this.sendGoodsCountry;
    data['sendGoodsCountryFullName'] = this.sendGoodsCountryFullName;
    data['serviceName'] = this.serviceName;
    if (this.standardFreightAmount != null) {
      data['standardFreightAmount'] = this.standardFreightAmount!.toJson();
    }
    data['time'] = this.time;
    data['tracking'] = this.tracking;
    data['priceFormatStr'] = this.priceFormatStr;
    data['localPriceFormatStr'] = this.localPriceFormatStr;
    return data;
  }
}

class BizShowMind {
  List<dynamic>? layout;

  BizShowMind({this.layout});

  BizShowMind.fromJson(Map<String, dynamic> json) {
    if (json['layout'] != null) {
      layout = [];
      json['layout'].forEach((v) {
        layout!.add(v);
      });
    }
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    if (this.layout != null) {
      data['layout'] = this.layout!.map((v) => v.toJson()).toList();
    }
    return data;
  }
}

class FreightAmount {
  String? currency;
  num? value;

  FreightAmount({this.currency, this.value});

  FreightAmount.fromJson(Map<String, dynamic> json) {
    currency = json['currency'];
    value = json['value'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['currency'] = this.currency;
    data['value'] = this.value;
    return data;
  }
}

class FreightLayout {
  String? displayType;
  List<Layout>? layout;
  String? openShippingPanel;
  List<String>? displayShipping;

  FreightLayout(
      {this.displayType,
      this.layout,
      this.openShippingPanel,
      this.displayShipping});

  FreightLayout.fromJson(Map<String, dynamic> json) {
    displayType = json['displayType'];
    if (json['layout'] != null) {
      layout = <Layout>[];
      displayShipping = [];
      json['layout'].forEach((v) {
        layout!.add(new Layout.fromJson(v));
        displayShipping!
            .add(v['text'].toString().replaceAll('AliExpress', 'YellowStores'));
      });
    }
    openShippingPanel = json['openShippingPanel'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['displayType'] = this.displayType;
    if (this.layout != null) {
      data['layout'] = this.layout!.map((v) => v).toList();
    }
    data['openShippingPanel'] = this.openShippingPanel;
    return data;
  }
}

class Layout {
  String? text;
  String? type;

  Layout({this.text, this.type});

  Layout.fromJson(Map<String, dynamic> json) {
    text = json['text'];
    type = json['type'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['text'] = this.text;
    data['type'] = this.type;
    return data;
  }
}
