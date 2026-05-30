class Discount {
  String? calculateDiscountFrom;
  DiscountRules? discountRules;

  Discount({this.calculateDiscountFrom, this.discountRules});

  Discount.fromJson(Map<String, dynamic> json) {
    calculateDiscountFrom = json['calculate_discount_from'];
    discountRules = json['discount_rules'] != null
        ? new DiscountRules.fromJson(json['discount_rules'])
        : null;
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['calculate_discount_from'] = this.calculateDiscountFrom;
    if (this.discountRules != null) {
      data['discount_rules'] = this.discountRules!.toJson();
    }
    return data;
  }
}

class DiscountRules {
  String? operator;
  List<dynamic>? ranges;

  DiscountRules({this.operator, this.ranges});

  DiscountRules.fromJson(Map<String, dynamic> json) {
    dynamic _listRange = [];
    operator = json['operator'];
    if (json['ranges'] != null && json['ranges'] != '') {
      json['ranges'].forEach((k, v) => _listRange.add(Range.fromJson(v)));
    }
    ranges = _listRange;
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['operator'] = this.operator;
    if (this.ranges != null) {
      data['ranges'] = this.ranges;
    }
    return data;
  }
}

class Range {
  String? from;
  String? to;
  String? type;
  String? value;
  String? label;

  Range({this.from, this.to, this.type, this.value, this.label});

  Range.fromJson(Map<String, dynamic> json) {
    from = json['from'];
    to = json['to'];
    type = json['type'];
    value = json['value'];
    label = json['label'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['from'] = this.from;
    data['to'] = this.to;
    data['type'] = this.type;
    data['value'] = this.value;
    data['label'] = this.label;
    return data;
  }
}
