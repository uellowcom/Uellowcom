import 'package:flutter/material.dart';
import 'package:nyoba/constant/constants.dart';
import 'package:nyoba/constant/global_url.dart';
import 'package:nyoba/provider/urlProvider.dart';
import 'package:nyoba/services/session.dart';
import 'package:provider/provider.dart';

class BlogAPI {
  fetchBlog(search, page, BuildContext context) async {
    final url = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await url.getAsync(
        '$blog?search=$search&page=$page&per_page=6&_embed',
        version: 2);
    return response;
  }

  postCommentBlog(String postId, String? comment, BuildContext context) async {
    final url = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    Map data = {
      'cookie': Session.data.getString('cookie'),
      'post': postId,
      'comment': comment
    };
    var response = await url.postAsync(
      '$postComment',
      data,
      isCustom: true,
    );
    return response;
  }

  fetchBlogComment(postId, BuildContext context) async {
    final url = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await url.getAsync('$listComment?post=$postId', version: 2);
    return response;
  }

  fetchBlogDetailById(postId, BuildContext context) async {
    final url = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await url.getAsync('$blog/$postId?_embed', version: 2);
    return response;
  }

  fetchBlogDetailBySlug(slug, BuildContext context) async {
    final url = Provider.of<UrlProvider>(context, listen: false).baseAPI;

    var response = await url.getAsync('$blog/?_embed&slug=$slug', version: 2);
    return response;
  }
}
