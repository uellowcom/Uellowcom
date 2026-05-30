class ReviewModel {
  int? id, rating;
  String? dateCreated, status, reviewer, review, avatar;

  ReviewModel(
      {this.id,
      this.dateCreated,
      this.status,
      this.reviewer,
      this.review,
      this.rating,
      this.avatar});

  Map toJson() => {
        'id': id,
        'date_created': dateCreated,
        'status': status,
        'reviewer': reviewer,
        'review': review,
        'rating': rating,
        'avatar': avatar
      };

  ReviewModel.fromJson(Map json) {
    id = json['id'];
    dateCreated = json['date_created'];
    status = json['status'];
    reviewer = json['reviewer'];
    review = json['review'];
    rating = json['rating'];
    avatar = json['reviewer_avatar_urls']['48'];
  }
}

class ReviewHistoryModel {
  String? commentDate,
      productId,
      titleProduct,
      imageProduct,
      content,
      star,
      author;

  ReviewHistoryModel(
      {this.commentDate,
      this.productId,
      this.titleProduct,
      this.imageProduct,
      this.content,
      this.star,
      this.author});

  Map toJson() => {
        'product_id': productId,
        'title_product': titleProduct,
        'image_product': imageProduct,
        'content': content,
        'star': star,
        'comment_date': commentDate,
        'comment_author': author
      };

  ReviewHistoryModel.fromJson(Map json) {
    productId = json['product_id'];
    titleProduct = json['title_product'];
    imageProduct = json['image_product'];
    content = json['content'];
    star = json['star'] != '' ? json['star'] : '0';
    commentDate = json['comment_date'];
    author = json['comment_author'];
  }
}

class NewReviewModel {
  String? commentId;
  String? content;
  String? star;
  String? productId;
  String? titleProduct;
  String? imageProduct;
  String? userId;
  List<String>? commentImages;
  String? commentAuthor;
  String? authorAvatar;
  String? commentDate;

  NewReviewModel(
      {this.commentId,
      this.content,
      this.star,
      this.productId,
      this.titleProduct,
      this.imageProduct,
      this.userId,
      this.commentImages,
      this.commentAuthor,
      this.authorAvatar,
      this.commentDate});

  NewReviewModel.fromJson(Map<dynamic, dynamic> json) {
    commentId = json['comment_id'];
    content = json['content'];
    star = json['star'];
    productId = json['product_id'];
    titleProduct = json['title_product'];
    imageProduct = json['image_product'];
    userId = json['user_id'];
    commentImages = json['comment_images'].cast<String>();
    commentAuthor = json['comment_author'];
    authorAvatar = json['author_avatar'];
    commentDate = json['comment_date'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['comment_id'] = this.commentId;
    data['content'] = this.content;
    data['star'] = this.star;
    data['product_id'] = this.productId;
    data['title_product'] = this.titleProduct;
    data['image_product'] = this.imageProduct;
    data['user_id'] = this.userId;
    data['comment_images'] = this.commentImages;
    data['comment_author'] = this.commentAuthor;
    data['author_avatar'] = this.authorAvatar;
    data['comment_date'] = this.commentDate;
    return data;
  }
}

class NewReviewImage {
  String? commentId;
  String? image;
  String? content;

  NewReviewImage({this.commentId, this.image, this.content});

  NewReviewImage.fromJson(Map<dynamic, dynamic> json) {
    commentId = json['comment_id'];
    image = json['image'];
    content = json['content'];
  }

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = new Map<String, dynamic>();
    data['comment_id'] = this.commentId;
    data['image'] = this.image;
    data['content'] = this.content;
    return data;
  }
}
