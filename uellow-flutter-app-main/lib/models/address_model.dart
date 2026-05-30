class AddressModel {
  int? userId;
  String? firstName;
  String? lastName;
  String? company;
  String? country;
  String? state;
  String? city;
  String? address1;
  String? address2;
  String? postcode;
  String? phone;
  String? email;
  String? addressKey;
  String? defaultAddress;
  String? billingHeading;
  String? stateName;
  String? countryName;
  String? code;

  AddressModel(
      {this.firstName,
      this.lastName,
      this.company,
      this.country,
      this.state,
      this.city,
      this.address1,
      this.address2,
      this.postcode,
      this.phone,
      this.email,
      this.addressKey,
      this.defaultAddress,
      this.billingHeading,
      this.userId,
      this.countryName,
      this.stateName,
      this.code});

  Map toJson() => {
        'billing_first_name': firstName,
        'billing_last_name': lastName,
        'billing_company': company,
        'billing_country': country,
        'billing_state': state,
        'billing_city': city,
        'billing_address_1': address1,
        'billing_address_2': address2,
        'billing_postcode': postcode,
        'billing_phone': phone,
        'billing_email': email,
        'address_key': addressKey,
        'user_id': userId,
        'code': code
      };

  AddressModel.fromJson(Map json) {
    firstName = json['billing_first_name'];
    lastName = json['billing_last_name'];
    company = json['billing_company'];
    country = json['billing_country'];
    state = json['billing_state'];
    city = json['billing_city'];
    address1 = json['billing_address_1'];
    address2 = json['billing_address_2'];
    postcode = json['billing_postcode'];
    phone = json['billing_phone'];
    email = json['billing_email'];
    addressKey = json['address_key'];
    defaultAddress = json['default_address'];
    billingHeading = json['billing_heading'];
    stateName = json['billing_state_name'];
    countryName = json['billing_country_name'];
    code = json['code'];
  }
}
