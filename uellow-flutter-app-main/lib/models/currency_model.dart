class CurrencyModel {
  String? name, symbol, position, ratePlus, separators, description, flag;
  double? rate;
  int? isEtalon, hideCents, hideOnFront, decimals;

  CurrencyModel(
      {this.name,
      this.symbol,
      this.position,
      this.rate,
      this.ratePlus,
      this.separators,
      this.description,
      this.flag,
      this.isEtalon,
      this.hideCents,
      this.hideOnFront,
      this.decimals});

  Map toJson() => {
        'name': name,
        'rate': rate,
        'symbol': symbol,
        'position': position,
        'is_etalon': isEtalon,
        'hide_cents': hideCents,
        'hide_on_front': hideOnFront,
        'rate_plus': ratePlus,
        'decimals': decimals,
        'separators': separators,
        'description': description,
        'flag': flag
      };

  CurrencyModel.fromJson(Map json) {
    name = json['name'] ?? "";
    rate = json['rate'].toDouble() ?? 0;
    symbol = json['symbol'] ?? "";
    position = json['position'] ?? "right";
    isEtalon = json['is_etalon'] ?? 0;
    hideCents = json['hide_cents'] ?? 0;
    hideOnFront = json['hide_on_front'] ?? 0;
    ratePlus = json['rate_plus'] ?? "";
    decimals = json['decimals'] ?? 0;
    separators = json['separators'] ?? "";
    description = json['description'] ?? "";
    flag = json['flag'] ?? "";
  }
}
