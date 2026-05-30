class BannerModel {
  // Model
  final int? product;
  final String? titleSlider;
  final String? image;
  final String? linkTo;
  final String? name;

  BannerModel(
      {this.product, this.titleSlider, this.image, this.linkTo, this.name});

  Map toJson() => {
        'product': product,
        'title_slider': titleSlider,
        'image': image,
        'link_to': linkTo,
        'name': name
      };

  BannerModel.fromJson(Map json)
      : product = json['product'],
        titleSlider = json['title_slider'],
        image = json['image'],
        linkTo = json['link_to'],
        name = json['name'];
}
