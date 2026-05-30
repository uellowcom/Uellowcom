import 'package:nyoba/models/product_attribute_option.dart';
import 'package:nyoba/models/product_available_variation.dart';
import 'package:nyoba/services/session.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:slugify/slugify.dart';

class ProductModel {
  int? id, productStock, ratingCount, cartQuantity = 1, variantId, totalSold;
  int aliSold = 0;
  double? discProduct;
  num? priceTotal;
  String? productName,
      productSlug,
      productDescription,
      productShortDesc,
      productSku,
      formattedPrice,
      formattedSalesPrice,
      avgRating,
      link,
      stockStatus,
      type,
      image;
  var productRegPrice, productSalePrice, totalSales;
  bool? isSelected = false;
  bool isProductWholeSale = false;
  bool? manageStock = false;
  bool? codPayment;
  List<ProductImageModel>? images;
  List<ProductCategoryModel>? categories;
  List<ProductAttributeModel>? attributes = [];
  List<ProductAttributeModel>? specifications;
  List<ProductMetaData>? metaData;
  List<ProductVideo>? videos;
  List<ProductVariation>? selectedVariation = [];
  String? variationName = '';
  List<num>? variationPrices = [];
  List<num>? variationPricesDisc = [];
  List<dynamic>? tags;
  List<AvailableVariation>? availableVariations;
  List<String>? variationLabel;
  List<AttributeOpt>? attributeOpt;
  List<CustomVariationModel>? customVariation = [];
  List<CustomVariationModel>? tempCustomVariation = [];
  num? productPriceDisc, cartPrice, productPrice, shippingPrice;
  bool? isDiscRuleValid = false;
  int? qtyTotal;
  bool? onSale;
  String? idAliProduct, countryTo, countryFrom, brand;
  YithModel? yith;
  String? a2wShippingMethod;
  List<dynamic>? a2wShippingCheckoutData;
  List<BadgesModel>? badges;

  ProductModel(
      {this.id,
      this.totalSales,
      this.productStock,
      this.productName,
      this.productSlug,
      this.productDescription,
      this.productShortDesc,
      this.productSku,
      this.productPrice,
      this.productRegPrice,
      this.productSalePrice,
      this.productPriceDisc,
      this.codPayment,
      this.images,
      this.categories,
      this.ratingCount,
      this.avgRating,
      this.discProduct,
      this.attributes,
      this.cartQuantity,
      this.isSelected,
      this.priceTotal,
      this.variantId,
      this.link,
      this.metaData,
      this.videos,
      this.stockStatus,
      this.type,
      this.selectedVariation,
      this.variationName,
      this.variationPrices,
      this.tags,
      this.customVariation,
      this.cartPrice,
      this.isDiscRuleValid,
      this.qtyTotal,
      this.onSale,
      this.image,
      this.yith,
      this.brand,
      this.a2wShippingMethod,
      this.a2wShippingCheckoutData,
      this.badges});

  Map toJson() => {
        'id': id,
        'total_sales': totalSales,
        'stock_quantity': productStock,
        'name': productName,
        'slug': productSlug,
        'description': productDescription,
        'cod_payment': codPayment,
        'short_description': productShortDesc,
        'formated_price': formattedPrice,
        'formated_sales_price': formattedSalesPrice,
        'sku': productSku,
        'price': productPrice,
        'regular_price': productRegPrice,
        'sale_price': productSalePrice,
        'disc_price': productPriceDisc,
        'images': images,
        'categories': categories,
        'average_rating': avgRating,
        'rating_count': ratingCount,
        'attributes': attributes,
        'disc': discProduct,
        'cart_quantity': cartQuantity,
        'is_selected': isSelected,
        'price_total': priceTotal,
        'variant_id': variantId,
        'permalink': link,
        'meta_data': metaData,
        'videos': videos,
        'manage_stock': manageStock,
        'stock_status': stockStatus,
        'type': type,
        'selected_variation': selectedVariation,
        'variation_name': variationName,
        'variation_prices': variationPrices,
        'tags': tags,
        'custom_variation': customVariation,
        'availableVariations': availableVariations,
        'cart_price': cartPrice,
        'is_disc_rule_valid': isDiscRuleValid,
        'qty_total': qtyTotal,
        'on_sale': onSale,
        'id_ali_product': idAliProduct,
        'country_to': countryTo,
        'country_from': countryFrom,
        'image': image,
        'yith_badge': yith,
        'brand': brand,
        'a2w_shipping_method': a2wShippingMethod,
        'a2w_shipping_method_checkout_data': a2wShippingCheckoutData,
        'badges': badges
      };

  ProductModel.fromJson(Map json) {
    id = json['id'];
    totalSales = json['total_sales'] ?? 0;
    productStock = json['manage_stock'] == false
        ? 999
        : json['stock_quantity'] == null && json['stock_status'] == 'instock'
            ? 999
            : json['stock_quantity'] ?? 0;
    stockStatus = json['stock_status'];
    productName = convertHtmlUnescape(json['name']);
    productSlug = json['slug'];
    productDescription = json['description'];
    codPayment = json['cod_payment'];
    productShortDesc = json['short_description'];
    formattedPrice = json['formated_price'];
    formattedSalesPrice = json['formated_sales_price'];
    productSku = json['sku'];
    link = json['permalink'];
    manageStock = json['manage_stock'];
    if (json['a2w_shipping_method_checkout_data'] != null) {
      a2wShippingCheckoutData = json['a2w_shipping_method_checkout_data'] ?? [];
    }
    type = json['type'];
    yith = json['yith_badge'] != null
        ? YithModel.fromJson(json['yith_badge'])
        : YithModel();
    if (json['badges'] != null) {
      badges = [];
      json['badges'].forEach((v) {
        badges!.add(new BadgesModel.fromJson(v));
      });
    }
    a2wShippingMethod = json['a2w_shipping_method'] ?? "";
    brand = json['brand'];
    productPrice =
        json['price'] != null && json['price'] != '' ? json['price'] : 0;
    productRegPrice =
        json['regular_price'] != null && json['regular_price'] != ''
            ? json['regular_price'].toString()
            : '0';
    productSalePrice = json['sale_price'] != null && json['sale_price'] != ''
        ? json['sale_price'].toString()
        : '';
    productPriceDisc = json['disc_price'];
    avgRating = json['average_rating'];
    ratingCount = json['rating_count'];
    if (json['images'] != null) {
      images = [];
      json['images'].forEach((v) {
        images!.add(new ProductImageModel.fromJson(v));
      });
    }
    if (json['categories'] != null && json['categories'] != false) {
      categories = [];
      json['categories'].forEach((v) {
        categories!.add(new ProductCategoryModel.fromJson(v));
      });
    }
    if (json['attributes'] != null) {
      attributes = [];
      specifications = [];
      json['attributes'].forEach((v) {
        if (v['variation'] == false) {
          specifications!.add(new ProductAttributeModel.fromJson(v));
        } else {
          attributes!.add(new ProductAttributeModel.fromJson(v));
        }
      });
      if (attributes!.length != 0) {
        variationLabel = [];
        attributes!.forEach((element) {
          variationLabel!.add("${element.options!.length} ${element.name}");
        });
      }
    }
    image = json['image'] ?? "";
    cartQuantity = json['cart_quantity'];
    discProduct = json['disc'] != null
        ? json['disc']
        : productSalePrice.isNotEmpty && productSalePrice != "0"
            ? discProduct = ((double.parse(productRegPrice) -
                        double.parse(productSalePrice)) /
                    double.parse(productRegPrice)) *
                100
            : discProduct = 0;
    isSelected = json['is_selected'];
    priceTotal = json['price_total'];
    variantId = json['variant_id'];
    if (json['meta_data'] != null) {
      metaData = [];
      videos = [];
      json['meta_data'].forEach((v) {
        metaData!.add(new ProductMetaData.fromJson(v));
        if (v['key'] == 'wholesale_customer_have_wholesale_price' &&
            v['value'] == 'yes') {
          isProductWholeSale = true;
        }
        if (v['key'] == '_ywcfav_video') {
          v['value'].forEach((valVideo) {
            videos!.add(new ProductVideo.fromJson(valVideo));
          });
        }
        if (v['key'] == '_a2w_orders_count') {
          if (v['value'] != '') {
            aliSold = int.parse(v['value']);
          }
        }
        if (v['key'] == '_a2w_shipping_data') {
          if (v['value']['cost'] != '') {
            shippingPrice = v['value']['cost'];
          }
          if (v['value']['country_to'] != '') {
            countryTo = v['value']['country_to'];
          }
          if (v['value']['country_from'] != '') {
            countryFrom = v['value']['country_from'];
          }
        }
        if (v['key'] == '_a2w_external_id') {
          if (v['value'] != '') {
            idAliProduct = v['value'];
          }
        }
      });
    }
    if (isProductWholeSale &&
        Session.data.getString('role') == 'wholesale_customer') {
      metaData!.forEach((element) {
        if (element.key == 'wholesale_customer_wholesale_price' &&
            element.value.toString().isNotEmpty) {
          discProduct = 0;
          productSalePrice = "0";
          productRegPrice = "0";
          productPriceDisc = 0;
          productPrice = element.value;
        }
      });
    }
    if (json['selected_variation'] != null) {
      selectedVariation = [];
      json['selected_variation'].forEach((v) {
        selectedVariation!.add(new ProductVariation.fromJson(v));
      });
    }
    if (json['variation_name'] != null) {
      variationName = json['variation_name'];
    }
    if (json['availableVariations'] != null) {
      availableVariations = [];
      json['availableVariations'].forEach((v) {
        variationPrices!.add(v['display_price']);
        availableVariations!.add(new AvailableVariation.fromJson(v));
      });
      variationPrices!.sort((a, b) => a.compareTo(b));
    }
    if (isProductWholeSale &&
        Session.data.getString('role') == 'wholesale_customer') {
      if (json['wholesales'] != null) {
        if (type == 'simple') {
          variationPrices!.clear();
          json['wholesales'].forEach((v) {
            variationPrices!.add(double.parse(v['price']));
          });
          variationPrices!.sort((a, b) => a.compareTo(b));
        }
      }
    }
    if (json['tags'] != null) {
      tags = [];
      json['tags'].forEach((v) {
        tags!.add(v.toString());
      });
    }
    totalSold = (aliSold + totalSales) as int?;
    if (attributes!.isNotEmpty && type != 'simple') {
      attributes!.forEach((element) {
        List<OptionVariation>? _optVariation = [];
        List<OptionVariation>? _tempOptVariation = [];
        if (element.optionsTranslate!.isNotEmpty) {
          element.optionsTranslate!.forEach((op) {
            _optVariation.add(new OptionVariation(
                value: element.id == 0 ? op : slugify(op).replaceAll('--', '-'),
                name: op));
          });
        }
        if (element.options!.isNotEmpty) {
          element.options!.forEach((op) {
            _tempOptVariation.add(new OptionVariation(
                value: element.id == 0 ? op : slugify(op).replaceAll('--', '-'),
                name: op));
          });
        }
        tempCustomVariation!.add(CustomVariationModel(
            id: element.id,
            slug: element.id == 0
                ? slugify(element.name!)
                : 'pa_${slugify(element.name!)}',
            name: element.name,
            selectedValue: _tempOptVariation.isNotEmpty
                ? _tempOptVariation.first.value
                : '',
            selectedName: _tempOptVariation.isNotEmpty
                ? _tempOptVariation.first.name
                : '',
            optionVariation: _tempOptVariation));

        customVariation!.add(new CustomVariationModel(
            id: element.id,
            slug: element.id == 0
                ? slugify(element.nameTranslate!)
                : 'pa_${slugify(element.nameTranslate!)}',
            name: element.nameTranslate,
            selectedValue:
                _optVariation.isNotEmpty ? _optVariation.first.value : '',
            selectedName:
                _optVariation.isNotEmpty ? _optVariation.first.name : '',
            optionVariation: _optVariation));
      });
      if (availableVariations!.isNotEmpty) {
        availableVariations!.forEach((element) {
          customVariation!.first.optionVariation!.forEach((op) {
            if (element
                    .attributes['attribute_${customVariation!.first.slug}'] ==
                op.value) {
              op.image = element.image!.src;
            }
          });
        });
      }
      isDiscRuleValid = json['is_disc_rule_valid'];
      qtyTotal = json['qty_total'];
    }
    cartPrice = json['cart_price'];
  }

  @override
  String toString() {
    return 'ProductModel{id: $id, totalSales: $totalSales, productStock: $productStock, cod payment: $codPayment, ratingCount: $ratingCount, cartQuantity: $cartQuantity, priceTotal: $priceTotal, variantId: $variantId, discProduct: $discProduct, productName: $productName, productSlug: $productSlug, productDescription: $productDescription, productShortDesc: $productShortDesc, productSku: $productSku, productPrice: $productPrice, productRegPrice: $productRegPrice, productSalePrice: $productSalePrice, avgRating: $avgRating, link: $link, isSelected: $isSelected, images: $images, categories: $categories, attributes: $attributes}';
  }
}

class BadgesModel {
  int? id;
  String? position;
  String? image;

  BadgesModel({this.id, this.position, this.image});

  BadgesModel.fromJson(Map<String, dynamic> json) {
    id = json['id'];
    position = json['position'];
    image = json['image'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['id'] = this.id;
    data['position'] = this.position;
    data['image'] = this.image;
    return data;
  }
}

class YithModel {
  String? text;
  String? video;

  YithModel({this.text, this.video});

  YithModel.fromJson(Map<String, dynamic> json) {
    text = json['text'];
    video = json['video'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['text'] = this.text;
    data['video'] = this.video;
    return data;
  }
}

class ProductImageModel {
  int? id;
  String? dateCreated, dateModified, src, name, alt;

  ProductImageModel(
      {this.dateCreated,
      this.dateModified,
      this.src,
      this.name,
      this.alt,
      this.id});

  Map toJson() => {
        'id': id,
        'date_created': dateCreated,
        'date_modified': dateModified,
        'src': src,
        'name': name,
        'alt': alt,
      };

  ProductImageModel.fromJson(Map json)
      : id = json['id'],
        dateCreated = json['date_created'],
        dateModified = json['date_modified'],
        src = json['src'],
        name = json['name'],
        alt = json['alt'];
}

class ProductCategoryModel {
  int? id, count;
  String? name, slug;
  var image;

  ProductCategoryModel({this.slug, this.name, this.id, this.image, this.count});

  Map toJson() =>
      {'id': id, 'name': name, 'slug': slug, 'image': image, 'count': count};

  ProductCategoryModel.fromJson(Map json) {
    id = json['id'] ?? json['term_id'];
    name = json['name'] ?? json['title'];
    slug = json['slug'];
    count = json['count'];
    if (json['image'] != null && json['image'] != '') {
      if (json['image'] != false) {
        image = json['image'];
      }
    }
  }
}

class ProductAttributeModel {
  int? id, position;
  String? selectedVariant;
  bool? visible, variation;
  List<dynamic>? options, optionsTranslate;
  dynamic name, nameTranslate;

  ProductAttributeModel(
      {this.id,
      this.position,
      this.name,
      this.visible,
      this.variation,
      this.options,
      this.selectedVariant,
      this.nameTranslate,
      this.optionsTranslate});

  Map toJson() => {
        'id': id,
        'position': position,
        'name': name,
        'visible': visible,
        'variation': variation,
        'options': options,
        'selected_variant': selectedVariant,
        'name_translate': nameTranslate,
        'options_translate': optionsTranslate
      };

  ProductAttributeModel.fromJson(Map json)
      : id = json['id'],
        name = json['name'],
        position = json['position'],
        visible = json['visible'],
        variation = json['variation'],
        options = json['options'],
        selectedVariant = json['selected_variant'],
        nameTranslate = json['name_translate'],
        optionsTranslate = json['options_translate'];
}

class ProductVariation {
  int? id;
  String? columnName;
  String? value;

  ProductVariation({this.id, this.value, this.columnName});

  Map toJson() => {
        'id': id,
        'column_name': columnName,
        'value': value,
      };

  ProductVariation.fromJson(Map json)
      : id = json['id'],
        columnName = json['column_name'],
        value = json['value'];

  @override
  String toString() {
    return 'ProductVariation{columnName: $columnName, value: $value}';
  }
}

class ProductMetaData {
  int? id;
  String? key;
  var value;

  ProductMetaData({this.id, this.key, this.value});

  Map toJson() => {
        'id': id,
        'key': key,
        'value': value,
      };

  ProductMetaData.fromJson(Map json)
      : id = json['id'],
        key = json['key'],
        value = json['value'];
}

class ProductVideo {
  String? thumbnail, id, type, featured, name, host, content;

  ProductVideo(
      {this.thumbnail,
      this.id,
      this.type,
      this.featured,
      this.name,
      this.host,
      this.content});

  Map toJson() => {
        'thumbnail': thumbnail,
        'id': id,
        'type': type,
        'featured': featured,
        'name': name,
        'host': host,
        'content': content,
      };

  ProductVideo.fromJson(Map json)
      : thumbnail = json['thumbn'],
        id = json['id'],
        type = json['type'],
        featured = json['featured'],
        name = json['name'],
        host = json['host'],
        content = json['content'];
}

class CustomVariationModel {
  int? id;
  String? slug, name;
  String? selectedValue;
  String? selectedName;
  List<OptionVariation>? optionVariation;

  CustomVariationModel(
      {this.id,
      this.slug,
      this.name,
      this.selectedValue,
      this.optionVariation,
      this.selectedName});

  CustomVariationModel.fromJson(Map<String, dynamic> json) {
    id = json['id'];
    slug = json['slug'];
    name = json['name'];
    selectedValue = json['selected_value'];
    selectedName = json['selected_name'];
    if (json['option_variation'] != null) {
      optionVariation = <OptionVariation>[];
      json['option_variation'].forEach((v) {
        optionVariation!.add(new OptionVariation.fromJson(v));
      });
    }
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['id'] = this.id;
    data['slug'] = this.slug;
    data['name'] = this.name;
    data['selected_value'] = this.selectedValue;
    data['selected_name'] = this.selectedName;
    if (this.optionVariation != null) {
      data['option_variation'] =
          this.optionVariation!.map((v) => v.toJson()).toList();
    }
    return data;
  }
}

class OptionVariation {
  String? value;
  String? image;
  String? name;

  OptionVariation({this.value, this.image, this.name});

  OptionVariation.fromJson(Map<String, dynamic> json) {
    value = json['value'];
    image = json['image'];
    name = json['name'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['value'] = this.value;
    data['image'] = this.image;
    data['name'] = this.name;
    return data;
  }
}
