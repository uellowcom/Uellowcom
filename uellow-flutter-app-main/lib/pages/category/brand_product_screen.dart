import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:nyoba/models/categories_model.dart';
import 'package:nyoba/models/filter_data_model.dart';
import 'package:nyoba/pages/home/home_screen.dart';
import 'package:nyoba/pages/order/cart_screen.dart';
import 'package:nyoba/provider/category_provider.dart';
import 'package:nyoba/provider/order_provider.dart';
import 'package:nyoba/provider/product_provider.dart';
import 'package:nyoba/utils/utility.dart';
import 'package:nyoba/widgets/home/grid_item.dart';
import 'package:nyoba/widgets/product/grid_item_shimmer.dart';
import 'package:nyoba/widgets/product/product_list_item.dart';
import 'package:provider/provider.dart';

import '../../app_localizations.dart';

class BrandProducts extends StatefulWidget {
  final String? categoryId;
  final String? brandName;
  final int? sortIndex;
  final bool? withFilter;
  final int? countSub;
  String? slug;
  bool? isNeedSub = false;
  final bool? isFromSplashScreen;
  BrandProducts(
      {Key? key,
      this.categoryId,
      this.brandName,
      this.sortIndex,
      this.withFilter = false,
      this.slug = "",
      this.isNeedSub = false,
      this.isFromSplashScreen = false,
      this.countSub = 0})
      : super(key: key);

  @override
  _BrandProductsState createState() => _BrandProductsState();
}

class _BrandProductsState extends State<BrandProducts> {
  int? currentIndex = 0;

  int page = 1;
  String order = 'desc';
  String orderBy = 'latest';
  int cartCount = 0;
  String _selectedPopItem = 'latest';

  int? clickIndex = 0;

  bool isGridView = true;

  ScrollController _scrollController = new ScrollController();
  ScrollController _scrollControllerList = new ScrollController();

  final _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  void initState() {
    final category = Provider.of<CategoryProvider>(context, listen: false);
    category.subAllCategories.clear();
    super.initState();
    if (widget.categoryId != null && widget.categoryId != "") {
      printLog("${widget.categoryId} category id");
      clickIndex = int.parse(widget.categoryId!);
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.countSub != 0) loadSubCategories(widget.countSub!);
      // } else {
      //   resetSubAllCategories();
      // }
      final product = Provider.of<ProductProvider>(context, listen: false);
      context.read<CategoryProvider>().reset();
      context.read<ProductProvider>().reset();

      _scrollController.addListener(() {
        if (_scrollController.position.pixels ==
            _scrollController.position.maxScrollExtent) {
          printLog("max");
          if (widget.slug != "") {
            setState(() {
              page++;
            });
            loadProductBySlug();
          } else if (product.listBrandProduct.length % 8 == 0) {
            setState(() {
              page++;
            });
            loadProductByBrand();
          }
        }
      });
      if (widget.sortIndex != null) {
        currentIndex = widget.sortIndex;
        // _tabController!.animateTo(currentIndex!);
        _selectedPopItem = 'latest';
        _onSortChange('latest');
        if (widget.slug != "") {
          loadProductBySlug();
        } else {
          loadProductByBrand();
        }
      } else {
        if (widget.slug != "") {
          loadProductBySlug();
        } else {
          loadProductByBrand();
          loadDataFilter();
        }
      }
      // if (widget.sortIndex != null) {
      //   currentIndex = widget.sortIndex;
      //   _selectedPopItem = 'latest';
      //   _onSortChange('latest');
      // } else {
      //   loadDataFilter();
      //   loadProductByBrand();
      // }
    });
  }

  resetSubAllCategories() async {
    await Provider.of<CategoryProvider>(context, listen: false)
        .resetSubAllCategories();
  }

  loadSubCategories(int count) async {
    printLog("masuk load sub categories");
    await Provider.of<CategoryProvider>(context, listen: false)
        .fetchAllCategories(context, widget.isFromSplashScreen!,
            count: int.parse(widget.categoryId!), isFromSub: true);
  }

  loadDataFilter() async {
    await Provider.of<CategoryProvider>(context, listen: false)
        .fetchFilterData(widget.categoryId.toString(), context);
  }

  loadProductBySlug() async {
    printLog("masuk load product by slug");
    printLog("${widget.slug}", name: "SLUG");

    await Provider.of<ProductProvider>(context, listen: false)
        .fetchBrandProductBySlug(slug: widget.slug, context: context);
    loadCartCount();
  }

  loadProductByBrand() async {
    final category = Provider.of<CategoryProvider>(context, listen: false);
    if (widget.isNeedSub == true) {
      if (clickIndex == 0 && category.subCategories.isNotEmpty) {
        clickIndex = category.subCategories[0].id;
      }
    }
    printLog("${widget.isNeedSub}", name: "isneedsub");
    printLog("$clickIndex", name: "ClickIndex");
    await Provider.of<ProductProvider>(context, listen: false)
        .fetchBrandProduct(
            context: context,
            page: page,
            order: order,
            category: widget.isNeedSub == true
                ? clickIndex.toString()
                : widget.categoryId.toString(),
            orderBy: orderBy);
    loadCartCount();
  }

  Future loadCartCount() async {
    await Provider.of<OrderProvider>(context, listen: false)
        .loadCartCount()
        .then((value) => setState(() {
              cartCount = value;
            }));
  }

  _onSortChange(result) {
    setState(() {
      _selectedPopItem = result;
      page = 1;
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
    loadProductByBrand();
  }

  @override
  Widget build(BuildContext context) {
    Widget buildItems =
        Consumer<ProductProvider>(builder: (context, value, child) {
      Widget tabCategory(AllCategoriesModel model, int i, int count) {
        return Container(
            padding: EdgeInsets.symmetric(horizontal: 14, vertical: 5),
            decoration: BoxDecoration(
              color: clickIndex == model.id
                  ? primaryColor.withOpacity(0.5)
                  : Colors.white,
              border: Border.all(
                  color: clickIndex == model.id
                      ? secondaryColor
                      : HexColor("B0b0b0")),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              children: [
                Image.network(
                  model.image!,
                  width: 50.w,
                ),
                Text(
                  convertHtmlUnescape(model.title!),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      fontSize: 13,
                      color: clickIndex == model.id
                          ? Colors.black
                          : HexColor("B0b0b0")),
                ),
              ],
            ));
      }

      if (value.loadingBrand && page == 1) {
        return Expanded(
            child: ListView(
          children: [
            customLoading(),
            MasonryGridView.count(
              crossAxisCount: 2,
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              shrinkWrap: true,
              itemCount: 6,
              physics: ScrollPhysics(),
              itemBuilder: (context, i) {
                return GridItemShimmer();
              },
            ),
          ],
        ));
      }

      return Expanded(
        child: ListView(
          controller: _scrollController,
          children: [
            widget.isNeedSub!
                ? Consumer<CategoryProvider>(builder: (context, value, child) {
                    printLog("${value.subAllCategories}",
                        name: "Sub All Categories");
                    printLog("${widget.isNeedSub}", name: "Is Need Sub");
                    if (value.loading) {
                      return Container();
                    } else if (value.subAllCategories.isEmpty) {
                      return Container();
                    } else {
                      return Container(
                        height: MediaQuery.of(context).size.height / 9,
                        child: ListView.separated(
                            itemCount: value.subAllCategories.length,
                            scrollDirection: Axis.horizontal,
                            itemBuilder: (context, i) {
                              return GestureDetector(
                                  onTap: () {
                                    setState(() {
                                      page = 1;
                                      clickIndex = value.subAllCategories[i].id;
                                    });
                                    printLog("sini sini");

                                    // loadNewProduct(true);

                                    // loadProducts();
                                    loadProductByBrand();
                                    // loadSubCategories(
                                    //     value.allCategories[i].id!);
                                    setState(() {});
                                  },
                                  child: tabCategory(value.subAllCategories[i],
                                      i, value.subAllCategories.length));
                            },
                            separatorBuilder:
                                (BuildContext context, int index) {
                              return SizedBox(
                                width: 8,
                              );
                            }),
                      );
                    }
                  })
                : Container(),
            SizedBox(
              height: 15.h,
            ),
            value.listBrandProduct.isEmpty
                ? buildSearchEmpty(context,
                    "${AppLocalizations.of(context)!.translate('cant_find_prod')}")
                : MasonryGridView.count(
                    crossAxisCount: 2,
                    // controller: _scrollController,
                    mainAxisSpacing: 10,
                    crossAxisSpacing: 10,
                    shrinkWrap: true,
                    itemCount: value.listBrandProduct.length,
                    physics: ScrollPhysics(),
                    itemBuilder: (context, i) {
                      return GridItem(
                        i: i,
                        itemCount: value.listBrandProduct.length,
                        product: value.listBrandProduct[i],
                      );
                    },
                  ),
          ],
        ),
      );
    });

    Widget buildListItems =
        Consumer<ProductProvider>(builder: (context, value, child) {
      Widget tabCategory(AllCategoriesModel model, int i, int count) {
        return Container(
            padding: EdgeInsets.symmetric(horizontal: 14, vertical: 5),
            decoration: BoxDecoration(
              color: clickIndex == model.id
                  ? primaryColor.withOpacity(0.5)
                  : Colors.white,
              border: Border.all(
                  color: clickIndex == model.id
                      ? secondaryColor
                      : HexColor("B0b0b0")),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              children: [
                Image.network(
                  model.image!,
                  width: 50.w,
                ),
                Text(
                  convertHtmlUnescape(model.title!),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      fontSize: 13,
                      color: clickIndex == model.id
                          ? Colors.black
                          : HexColor("B0b0b0")),
                ),
              ],
            ));
      }

      if (value.loadingBrand && page == 1) {
        return Expanded(
            child: ListView(
          children: [
            customLoading(),
            ListView.builder(
                shrinkWrap: true,
                itemCount: 8,
                itemBuilder: (context, i) {
                  return GridItemShimmer();
                }),
          ],
        ));
      }
      return Expanded(
        child: ListView(
          controller: _scrollController,
          children: [
            widget.isNeedSub!
                ? Consumer<CategoryProvider>(builder: (context, value, child) {
                    if (value.loading) {
                      return Container();
                    } else if (value.subAllCategories.isEmpty) {
                      return SizedBox();
                    } else {
                      return Container(
                        height: MediaQuery.of(context).size.height / 9,
                        child: ListView.separated(
                            itemCount: value.subAllCategories.length,
                            scrollDirection: Axis.horizontal,
                            itemBuilder: (context, i) {
                              return GestureDetector(
                                  onTap: () {
                                    setState(() {
                                      page = 1;
                                      clickIndex = value.subAllCategories[i].id;
                                    });

                                    // loadNewProduct(true);

                                    // loadProducts();
                                    loadProductByBrand();
                                    setState(() {});
                                  },
                                  child: tabCategory(value.subAllCategories[i],
                                      i, value.subAllCategories.length));
                            },
                            separatorBuilder:
                                (BuildContext context, int index) {
                              return SizedBox(
                                width: 8,
                              );
                            }),
                      );
                    }
                  })
                : Container(),
            SizedBox(
              height: 15.h,
            ),
            value.listBrandProduct.isEmpty
                ? buildSearchEmpty(context,
                    "${AppLocalizations.of(context)!.translate('cant_find_prod')}")
                : ListView.builder(
                    controller: _scrollControllerList,
                    shrinkWrap: true,
                    itemCount: value.listBrandProduct.length,
                    itemBuilder: (context, i) {
                      return ProductListItem(
                        i: i,
                        itemCount: value.listBrandProduct.length,
                        product: value.listBrandProduct[i],
                      );
                    }),
          ],
        ),
      );
    });

    // Widget tabCategory(ProductCategoryModel model, int i, int count) {
    //   return Container(
    //       padding: EdgeInsets.symmetric(horizontal: 14, vertical: 5),
    //       decoration: BoxDecoration(
    //         color: clickIndex == model.id
    //             ? primaryColor.withOpacity(0.5)
    //             : Colors.white,
    //         border: Border.all(
    //             color: clickIndex == model.id
    //                 ? secondaryColor
    //                 : HexColor("B0b0b0")),
    //         borderRadius: BorderRadius.circular(8),
    //       ),
    //       child: Column(
    //         children: [
    //           Image.network(
    //             model.image,
    //             width: 50.w,
    //           ),
    //           Text(
    //             convertHtmlUnescape(model.name!),
    //             maxLines: 1,
    //             overflow: TextOverflow.ellipsis,
    //             style: TextStyle(
    //                 fontSize: 13,
    //                 color: clickIndex == model.id
    //                     ? Colors.black
    //                     : HexColor("B0b0b0")),
    //           ),
    //         ],
    //       ));
    // }

    return WillPopScope(
      onWillPop: () async {
        if (widget.isFromSplashScreen == true) {
          Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) {
            return HomeScreen();
          }));
        } else {
          Navigator.pop(context);
        }
        return true;
      },
      child: Scaffold(
        key: _scaffoldKey,
        backgroundColor: HexColor('EBEBEB'),
        drawer: _buildSideFilter(),
        appBar: AppBar(
          elevation: 0,
          surfaceTintColor: Colors.transparent,
          leading: IconButton(
            onPressed: () {
              if (widget.isFromSplashScreen == true) {
                Navigator.of(context)
                    .pushReplacement(MaterialPageRoute(builder: (_) {
                  return HomeScreen();
                }));
              } else {
                Navigator.pop(context);
              }
            },
            icon: Icon(Icons.arrow_back, color: Colors.black),
          ),
          title: Container(
            height: 38,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  convertHtmlUnescape(widget.brandName!),
                  style: TextStyle(
                      color: Colors.black,
                      fontSize: responsiveFont(16),
                      fontWeight: FontWeight.w500),
                ),
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
                    SizedBox(
                      height: 65,
                      child: Icon(
                        Icons.shopping_cart,
                        color: Colors.black,
                      ),
                    ),
                    Positioned(
                      right: 0,
                      top: 7,
                      child: Container(
                        padding:
                            EdgeInsets.symmetric(horizontal: 6, vertical: 2),
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
            child: Consumer<ProductProvider>(
              builder: (context, value, child) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      height: 5,
                    ),
                    Container(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          widget.withFilter!
                              ? InkWell(
                                  onTap: () =>
                                      _scaffoldKey.currentState?.openDrawer(),
                                  child: Container(
                                    child: Row(
                                      children: [
                                        Icon(Icons.filter_list_alt),
                                        // SizedBox(
                                        //   width: 5,
                                        // ),
                                        Text(
                                            "${AppLocalizations.of(context)!.translate('filters')}",
                                            style: TextStyle(
                                                fontSize: responsiveFont(12),
                                                fontWeight: FontWeight.w500)),
                                      ],
                                    ),
                                  ),
                                )
                              : InkWell(
                                  onTap: () {},
                                  child: Container(
                                    child: Row(
                                      children: [
                                        Text(
                                            AppLocalizations.of(context)!
                                                .translate('sort')!,
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
                                        // border: Border.all(color: secondaryColor),
                                        borderRadius: BorderRadius.circular(6),
                                        color: Colors.white),
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
                                        // border: Border.all(color: secondaryColor),
                                        borderRadius: BorderRadius.circular(6),
                                        color: Colors.white),
                                    child: Icon(Icons.list),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Container(
                            child: PopupMenuButton<String>(
                              color: HexColor("#FFFFFF"),
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
                                        fontWeight:
                                            _selectedPopItem == 'popularity'
                                                ? FontWeight.w500
                                                : FontWeight.normal),
                                  ),
                                ),
                                PopupMenuItem<String>(
                                  value: 'latest',
                                  child: Text(
                                    AppLocalizations.of(context)!
                                        .translate('latest')!,
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
                                        color:
                                            _selectedPopItem == 'highest_price'
                                                ? Colors.black
                                                : Colors.black,
                                        fontSize: responsiveFont(12),
                                        fontWeight:
                                            _selectedPopItem == 'highest_price'
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
                                        color:
                                            _selectedPopItem == 'lowest_price'
                                                ? Colors.black
                                                : Colors.black,
                                        fontSize: responsiveFont(12),
                                        fontWeight:
                                            _selectedPopItem == 'lowest_price'
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
                      height: 10,
                    ),
                    // widget.isNeedSub!
                    //     ? Consumer<CategoryProvider>(
                    //         builder: (context, value, child) {
                    //         if (value.loading) {
                    //           return Container();
                    //         } else {
                    //           return Container(
                    //             height: MediaQuery.of(context).size.height / 9,
                    //             child: ListView.separated(
                    //                 itemCount: value.subCategories.length,
                    //                 scrollDirection: Axis.horizontal,
                    //                 itemBuilder: (context, i) {
                    //                   return GestureDetector(
                    //                       onTap: () {
                    //                         setState(() {
                    //                           page = 1;
                    //                           clickIndex = value.subCategories[i].id;
                    //                         });

                    //                         // loadNewProduct(true);

                    //                         // loadProducts();
                    //                         loadProductByBrand();
                    //                         setState(() {});
                    //                       },
                    //                       child: tabCategory(value.subCategories[i],
                    //                           i, value.subCategories.length));
                    //                 },
                    //                 separatorBuilder:
                    //                     (BuildContext context, int index) {
                    //                   return SizedBox(
                    //                     width: 8,
                    //                   );
                    //                 }),
                    //           );
                    //         }
                    //       })
                    //     : Container(),
                    SizedBox(
                      height: 10.h,
                    ),
                    isGridView ? buildItems : buildListItems,
                    if (value.loadingBrand && page != 1) customLoading()
                  ],
                );
              },
            )),
      ),
    );
  }

  Widget _buildSideFilter() {
    final filter =
        Provider.of<CategoryProvider>(context, listen: false).filterDataModel;

    return SafeArea(
        bottom: false,
        top: false,
        child: Container(
          color: Colors.white,
          width: MediaQuery.of(context).size.width * 0.6,
          child: Drawer(
            backgroundColor: Colors.white,
            child: Column(
              children: <Widget>[
                filter == null
                    ? Expanded(
                        child: Center(
                            child: Text(
                                "${AppLocalizations.of(context)!.translate('no_filter')}")),
                      )
                    : Expanded(
                        child: ListView.builder(
                            shrinkWrap: true,
                            itemCount: filter.dataFilter!.length,
                            physics: ScrollPhysics(),
                            itemBuilder: (context, i) {
                              return Container(
                                padding: EdgeInsets.all(15),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      filter.dataFilter![i].termFilter.first
                                          .attributeName,
                                      style: TextStyle(
                                          fontWeight: FontWeight.w500,
                                          fontSize: responsiveFont(14)),
                                    ),
                                    Row(
                                      children: [
                                        Expanded(
                                            child: Wrap(
                                          children: [
                                            for (int j = 0;
                                                j <
                                                    filter.dataFilter![i]
                                                        .termFilter.length;
                                                j++)
                                              _buildBtnFilter(filter, i, j)
                                          ],
                                        ))
                                      ],
                                    )
                                  ],
                                ),
                              );
                            }),
                      ),
                Container(
                  margin: EdgeInsets.symmetric(horizontal: 10),
                  child: Row(
                    children: [
                      Expanded(
                        child: Container(
                          child: TextButton(
                            style: TextButton.styleFrom(
                              padding: EdgeInsets.zero,
                              // side: BorderSide(
                              // color: secondaryColor,
                              // ),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(5),
                              ),
                              backgroundColor: Colors.black,
                            ),
                            onPressed: () {
                              setState(() {
                                page = 1;
                              });
                              context
                                  .read<CategoryProvider>()
                                  .resetFilter(filter!);
                              context.read<CategoryProvider>().reset();
                              context.read<ProductProvider>().reset();

                              Navigator.pop(context);
                              loadProductByBrand();
                            },
                            child: Text(
                              "${AppLocalizations.of(context)!.translate('reset')}"
                                  .toUpperCase(),
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: responsiveFont(10),
                              ),
                            ),
                          ),
                        ),
                      ),
                      SizedBox(
                        width: 10.w,
                      ),
                      Expanded(
                        child: Container(
                          child: TextButton(
                            style: TextButton.styleFrom(
                              padding: EdgeInsets.zero,
                              backgroundColor: secondaryColor,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(5),
                              ),
                            ),
                            onPressed: () {
                              setState(() {
                                page = 1;
                              });
                              context
                                  .read<ProductProvider>()
                                  .setAttributeFilter(filter!);
                              Navigator.pop(context);
                              loadProductByBrand();
                            },
                            child: Text(
                              "${AppLocalizations.of(context)!.translate('apply')}"
                                  .toUpperCase(),
                              style: TextStyle(
                                color: Colors.black,
                                fontSize: responsiveFont(10),
                              ),
                            ),
                          ),
                        ),
                      )
                    ],
                  ),
                ),
                SizedBox(
                  height: 13.h,
                )
              ],
            ),
          ),
        ));
  }

  Widget _buildBtnFilter(FilterDataModel _filter, int i, int j) {
    TermFilter term = _filter.dataFilter![i].termFilter[j];
    return GestureDetector(
      onTap: () {
        setState(() {
          term.isSelected = !term.isSelected!;
        });
        context.read<CategoryProvider>().checkFilter(_filter);
        printLog(
            "message ${int.parse(term.metaColor!.replaceAll('#', "0xFF"))}.");
      },
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        margin: EdgeInsets.only(top: 5, bottom: 5, right: 10),
        decoration: BoxDecoration(
            // border: Border.all(color: primaryColor),
            borderRadius: BorderRadius.circular(6),
            color: term.isSelected! ? secondaryColor : Colors.grey[200]),
        child: Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.start,
            children: [
              term.metaColor != ""
                  ? Container(
                      width: 12,
                      height: 12,
                      decoration: BoxDecoration(
                          color: term.metaColor!.contains(',')
                              ? Color(int.parse(term.metaColor!
                                  .split(',')[0]
                                  .replaceAll('#', "0xFF")))
                              : Color(int.parse(
                                  term.metaColor!.replaceAll('#', "0xFF"))),
                          borderRadius: BorderRadius.circular(10)),
                    )
                  : SizedBox(),
              term.metaColor != ""
                  ? SizedBox(
                      width: 3.w,
                    )
                  : SizedBox(),
              Text("${term.name}")
            ]),
      ),
    );
  }
}
