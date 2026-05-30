class CustomizeBannerModel {
  String? sectionType;
  String? sectionPosition;
  String? image;
  String? redirectType;
  String? redirectTo;

  CustomizeBannerModel(
      {this.sectionType,
      this.sectionPosition,
      this.image,
      this.redirectType,
      this.redirectTo});

  CustomizeBannerModel.fromJson(Map<String, dynamic> json) {
    sectionType = json['section_type'];
    sectionPosition = json['section_position'];
    image = json['image'];
    redirectType = json['redirect_type'];
    redirectTo = json['redirect_to'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['section_type'] = this.sectionType;
    data['section_position'] = this.sectionPosition;
    data['image'] = this.image;
    data['redirect_type'] = this.redirectType;
    data['redirect_to'] = this.redirectTo;
    return data;
  }
}
