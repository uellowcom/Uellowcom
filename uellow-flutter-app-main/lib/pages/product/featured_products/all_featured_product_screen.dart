import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/app_localizations.dart';
import 'package:nyoba/pages/order/cart_screen.dart';
import 'package:nyoba/provider/order_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/widgets/home/grid_item.dart';
import 'package:nyoba/widgets/product/grid_item_shimmer.dart';
import 'package:nyoba/widgets/product/product_list_item.dart';
import 'package:provider/provider.dart';
import 'package:nyoba/utils/utility.dart';

class AllFeaturedProducts extends StatefulWidget {
  AllFeaturedProducts({Key? key}) : super(key: key);

  @override
  _AllFeaturedProductsState createState() => _AllFeaturedProductsState();
}

class _AllFeaturedProductsState extends State<AllFeaturedProducts> {
  int cartCount = 0;
  int page = 1;
  String order = 'desc';
  String orderBy = 'latest';
  String _selectedPopItem = 'latest';
  ScrollController _scrollController = new ScrollController();
  bool isGridView = true;

  @override
  void initState() {
    super.initState();
    final product = Provider.of<ProductProvider>(context, listen: false);
    _scrollController.addListener(() {
      if (_scrollController.position.pixels ==
          _scrollController.position.maxScrollExtent) {
        if (product.listMoreFeaturedProduct.length % 8 == 0) {
          setState(() {
            page++;
          });
          loadProduct();
        }
      }
    });
    loadProduct();
  }

  Future loadCartCount() async {
    await Provider.of<OrderProvider>(context, listen: false)
        .loadCartCount()
        .then((value) => setState(() {
              cartCount = value;
            }));
  }

  loadProduct() async {
    await Provider.of<ProductProvider>(context, listen: false)
        .fetchFeaturedProducts(
            context: context, page: page, order: order, orderBy: orderBy);
    loadCartCount();
  }

  _onSortChange(result) {
    setState(() {
      _selectedPopItem = result;
    });
    switch (result) {
      case 'popularity':
        setState(() {
          order = 'desc';
          orderBy = 'popularity';
        });
        break;
      case 'latest':
        setState(() {
          order = 'desc';
          orderBy = 'date';
        });
        break;
      case 'highest_price':
        setState(() {
          order = 'desc';
          orderBy = 'price';
        });
        break;
      case 'lowest_price':
        setState(() {
          order = 'asc';
          orderBy = 'price';
        });
        break;
      default:
    }
    loadProduct();
  }

  @override
  Widget build(BuildContext context) {
    final product = Provider.of<ProductProvider>(context, listen: false);
    Widget buildItems = ListenableProvider.value(
      value: product,
      child: Consumer<ProductProvider>(builder: (context, value, child) {
        if (value.loadingFeatured && page == 1) {
          return Expanded(
              child: MasonryGridView.count(
            crossAxisCount: 2,
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            shrinkWrap: true,
            itemCount: 6,
            physics: ScrollPhysics(),
            itemBuilder: (context, i) {
              return GridItemShimmer();
            },
          ));
        }
        if (value.listMoreFeaturedProduct.isEmpty) {
          return buildSearchEmpty(context,
              "${AppLocalizations.of(context)!.translate('cant_find_prod')}");
        }
        return Expanded(
            child: MasonryGridView.count(
          crossAxisCount: 2,
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          shrinkWrap: true,
          controller: _scrollController,
          itemCount: value.listMoreFeaturedProduct.length,
          physics: ScrollPhysics(),
          itemBuilder: (context, i) {
            return GridItem(
              i: i,
              itemCount: value.listMoreFeaturedProduct.length,
              product: value.listMoreFeaturedProduct[i],
            );
          },
        ));
      }),
    );

    Widget buildListItems = ListenableProvider.value(
      value: product,
      child: Consumer<ProductProvider>(builder: (context, value, child) {
        if (value.loadingMore && page == 1) {
          return Expanded(
            child: ListView.builder(
                shrinkWrap: true,
                itemCount: 8,
                itemBuilder: (context, i) {
                  return GridItemShimmer();
                }),
          );
        }
        if (value.listMoreFeaturedProduct.isEmpty) {
          return buildSearchEmpty(context,
              "${AppLocalizations.of(context)!.translate('cant_find_prod')}");
        }
        return Expanded(
          child: ListView.builder(
              controller: _scrollController,
              shrinkWrap: true,
              itemCount: value.listMoreFeaturedProduct.length,
              itemBuilder: (context, i) {
                return ProductListItem(
                  i: i,
                  itemCount: value.listMoreFeaturedProduct.length,
                  product: value.listMoreFeaturedProduct[i],
                );
              }),
        );
      }),
    );

    return Scaffold(
      backgroundColor: HexColor('EBEBEB'),
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.white,
        leading: IconButton(
          onPressed: () {
            Navigator.pop(context);
          },
          icon: Icon(Icons.arrow_back, color: Colors.black),
        ),
        title: Container(
          height: 38,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  AppLocalizations.of(context)!.translate('featured_products')!,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      color: Colors.black,
                      fontSize: responsiveFont(16),
                      fontWeight: FontWeight.w500),
                ),
              )
            ],
          ),
        ),
        actions: [
          InkWell(
            onTap: () {
              Navigator.push(
                  context,
                  MaterialPageRoute(
                      builder: (context) => CartScreen(
                            isFromHome: false,
                          )));
            },
            child: Container(
              width: 65,
              padding: EdgeInsets.symmetric(horizontal: 8),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Icon(
                    Icons.shopping_cart,
                    color: Colors.black,
                  ),
                  Positioned(
                    right: 0,
                    top: 7,
                    child: Container(
                      padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                          shape: BoxShape.circle, color: primaryColor),
                      alignment: Alignment.center,
                      child: Text(
                        cartCount.toString(),
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.black,
                          fontSize: responsiveFont(9),
                        ),
                      ),
                    ),
                  )
                ],
              ),
            ),
          ),
        ],
      ),
      body: Container(
        margin: EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 5,
            ),
            Container(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  InkWell(
                    onTap: () {},
                    child: Container(
                      child: Row(
                        children: [
                          Text(AppLocalizations.of(context)!.translate('sort')!,
                              style: TextStyle(
                                  color: Colors.transparent,
                                  fontSize: responsiveFont(12),
                                  fontWeight: FontWeight.w500)),
                          SizedBox(
                            width: 5,
                          ),
                          Icon(
                            Icons.filter_list,
                            color: Colors.transparent,
                          )
                        ],
                      ),
                    ),
                  ),
                  Container(
                    child: Row(
                      children: [
                        InkWell(
                          onTap: () {
                            setState(() {
                              isGridView = true;
                            });
                          },
                          child: Container(
                            decoration: BoxDecoration(
                                border: Border.all(color: secondaryColor),
                                borderRadius: BorderRadius.circular(6),
                                color:
                                    isGridView ? secondaryColor : Colors.white),
                            child: Icon(Icons.grid_view),
                          ),
                        ),
                        SizedBox(
                          width: 5.w,
                        ),
                        InkWell(
                          onTap: () {
                            setState(() {
                              isGridView = false;
                            });
                          },
                          child: Container(
                            decoration: BoxDecoration(
                                border: Border.all(color: secondaryColor),
                                borderRadius: BorderRadius.circular(6),
                                color:
                                    isGridView ? Colors.white : secondaryColor),
                            child: Icon(Icons.list),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    child: PopupMenuButton<String>(
                      child: Container(
                        child: Row(
                          children: [
                            Text(
                                AppLocalizations.of(context)!
                                    .translate('sort')!,
                                style: TextStyle(
                                    fontSize: responsiveFont(12),
                                    fontWeight: FontWeight.w500)),
                            SizedBox(
                              width: 5,
                            ),
                            Icon(Icons.filter_list)
                          ],
                        ),
                      ),
                      onSelected: (String result) {
                        _onSortChange(result);
                      },
                      itemBuilder: (BuildContext context) =>
                          <PopupMenuEntry<String>>[
                        PopupMenuItem<String>(
                          value: 'popularity',
                          child: Text(
                            AppLocalizations.of(context)!
                                .translate('popularity')!,
                            style: TextStyle(
                                color: _selectedPopItem == 'popularity'
                                    ? Colors.black
                                    : Colors.black,
                                fontSize: responsiveFont(12),
                                fontWeight: _selectedPopItem == 'popularity'
                                    ? FontWeight.w500
                                    : FontWeight.normal),
                          ),
                        ),
                        PopupMenuItem<String>(
                          value: 'latest',
                          child: Text(
                            AppLocalizations.of(context)!.translate('latest')!,
                            style: TextStyle(
                                color: _selectedPopItem == 'latest'
                                    ? Colors.black
                                    : Colors.black,
                                fontSize: responsiveFont(12),
                                fontWeight: _selectedPopItem == 'latest'
                                    ? FontWeight.w500
                                    : FontWeight.normal),
                          ),
                        ),
                        PopupMenuItem<String>(
                          value: 'highest_price',
                          child: Text(
                            AppLocalizations.of(context)!
                                .translate('highest_price')!,
                            style: TextStyle(
                                color: _selectedPopItem == 'highest_price'
                                    ? Colors.black
                                    : Colors.black,
                                fontSize: responsiveFont(12),
                                fontWeight: _selectedPopItem == 'highest_price'
                                    ? FontWeight.w500
                                    : FontWeight.normal),
                          ),
                        ),
                        PopupMenuItem<String>(
                          value: 'lowest_price',
                          child: Text(
                            AppLocalizations.of(context)!
                                .translate('lowest_price')!,
                            style: TextStyle(
                                color: _selectedPopItem == 'lowest_price'
                                    ? Colors.black
                                    : Colors.black,
                                fontSize: responsiveFont(12),
                                fontWeight: _selectedPopItem == 'lowest_price'
                                    ? FontWeight.w500
                                    : FontWeight.normal),
                          ),
                        ),
                      ],
                    ),
                  )
                ],
              ),
            ),
            SizedBox(
              height: 5,
            ),
            isGridView ? buildItems : buildListItems,
            if (product.loadingMore && page != 1) customLoading()
          ],
        ),
      ),
    );
  }
}
