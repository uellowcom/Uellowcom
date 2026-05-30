class AdditionalMenusModel {
  String? id;
  String? title;
  String? link;
  String? iconUrl;

  AdditionalMenusModel({this.id, this.title, this.link, this.iconUrl});

  Map toJson() => {'id': id, 'title': title, 'link': link, 'icon_url': iconUrl};

  AdditionalMenusModel.fromJson(Map json) {
    id = json['id'] ?? "";
    title = json['title'] ?? "";
    link = json['link'] ?? "";
    iconUrl = json['icon_url'] ?? "";
  }
}
