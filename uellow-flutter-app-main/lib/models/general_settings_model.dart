class GeneralSettingsModel {
  String? slug, title, image;
  dynamic description, position;
  RedirectModel? redirect;

  GeneralSettingsModel(
      {this.slug,
      this.title,
      this.image,
      this.description,
      this.position,
      this.redirect});

  Map toJson() => {
        'slug': slug,
        'title': title,
        'image': image,
        'description': description,
        'position': position,
        'redirect': redirect,
      };

  GeneralSettingsModel.fromJson(Map json) {
    slug = json['slug'].toString();
    title = json['title'];
    image = json['image'];
    description = json['description'];
    if (json['position'] != null) {
      position = json['position'];
    }
    if (json['redirect'] != null) {
      redirect = RedirectModel.fromJson(json['redirect']);
    }
  }

  @override
  String toString() {
    return 'GeneralSettingsModel{slug: $slug, title: $title, image: $image, description: $description, position: $position, redirect: $redirect}';
  }
}

class RedirectModel {
  String? to;
  String? objectId;

  RedirectModel({this.to, this.objectId});

  RedirectModel.fromJson(Map<String, dynamic> json) {
    to = json['to'];
    objectId = json['object_id'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['to'] = this.to;
    data['object_id'] = this.objectId;
    return data;
  }
}
