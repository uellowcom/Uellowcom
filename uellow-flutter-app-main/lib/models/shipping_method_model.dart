class ShippingMethodModel {
  String? serviceName;
  String? company;
  String? time;
  bool? tracking;
  double? price;
  double? formatedPrice;
  String? formatedDeliveryTime;
  String? label;

  ShippingMethodModel(
      {this.serviceName,
      this.company,
      this.time,
      this.tracking,
      this.price,
      this.formatedPrice,
      this.formatedDeliveryTime,
      this.label});

  Map toJson() => {
        'serviceName': serviceName,
        'company': company,
        'time': time,
        'tracking': tracking,
        'price': price,
        'formated_price': formatedPrice,
        'formated_delivery_time': formatedDeliveryTime,
        'label ': label
      };

  ShippingMethodModel.fromJson(Map json) {
    serviceName = json['serviceName'];
    company = json['company'];
    time = json['time'];
    tracking = json['tracking'];
    price = json['price'];
    formatedPrice = json['formated_price'];
    formatedDeliveryTime = json['formated_delivery_time'];
    label = json['label '];
  }
}
