class AttributeOpt {
  int? id;
  String? name;
  String? taxonomy;
  List<Opt>? opt;

  AttributeOpt({this.id, this.name, this.taxonomy, this.opt});

  AttributeOpt.fromJson(Map<String, dynamic> json) {
    id = json['id'];
    name = json['name'];
    taxonomy = json['taxonomy'];
    if (json['opt'] != null) {
      opt = <Opt>[];
      json['opt'].forEach((v) {
        opt!.add(new Opt.fromJson(v));
      });
    }
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['id'] = this.id;
    data['name'] = this.name;
    data['taxonomy'] = this.taxonomy;
    if (this.opt != null) {
      data['opt'] = this.opt!.map((v) => v.toJson()).toList();
    }
    return data;
  }
}

class Opt {
  String? image;
  String? variationOption;
  bool? isSelected;

  Opt({this.image, this.variationOption, this.isSelected});

  Opt.fromJson(Map<String, dynamic> json) {
    image = json['image'];
    variationOption = json['variation_option'];
    isSelected = json['is_selected'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['image'] = this.image;
    data['variation_option'] = this.variationOption;
    data['is_selected'] = this.isSelected;
    return data;
  }
}
