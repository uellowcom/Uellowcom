class FilterDataModel {
  List<dynamic>? dataFilter;

  FilterDataModel({this.dataFilter});

  FilterDataModel.fromJson(Map<String, dynamic> json) {
    dynamic _dataFilter = [];

    if (json['data_filter'] != null &&
        json['data_filter'] != '' &&
        json['data_filter'].isNotEmpty) {
      json['data_filter'].forEach((k, v) {
        List<TermFilter>? _termFilter = [];
        v.forEach((element) {
          _termFilter.add(TermFilter.fromJson(element));
        });

        _dataFilter.add(TaxonomyFilter(k, _termFilter));
      });
    }
    dataFilter = _dataFilter;
  }
}

class TaxonomyFilter {
  String? taxonomy;
  List<TermFilter>? termFilter;
  TaxonomyFilter(this.taxonomy, this.termFilter);
}

class TermFilter {
  int? termId;
  String? name, nameTranslate;
  String? attributeName, attributeNameTranslate;
  int? productCount;
  bool? isSelected = false;
  String? metaColor;

  TermFilter(
      {this.termId,
      this.name,
      this.productCount,
      this.attributeName,
      this.isSelected,
      this.metaColor,
      this.attributeNameTranslate,
      this.nameTranslate});

  TermFilter.fromJson(Map<String, dynamic> json) {
    termId = json['term_id'];
    name = json['name'];
    attributeName = json['attribute_name'];
    productCount = json['product_count'];
    attributeNameTranslate = json['attribute_name_translate'];
    nameTranslate = json['name_translate'];
    if (json['meta_color'] != null) {
      metaColor = json['meta_color'];
    }
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['attribute_name'] = this.attributeName;
    data['term_id'] = this.termId;
    data['name'] = this.name;
    data['product_count'] = this.productCount;
    data['meta_color'] = this.metaColor;
    return data;
  }
}
