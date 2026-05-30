import 'package:flutter/material.dart';
import 'package:flutter/src/widgets/framework.dart';

class ContainerCard extends StatefulWidget {
  final Widget child;
  ContainerCard({Key? key, required this.child}) : super(key: key);

  @override
  State<ContainerCard> createState() => _ContainerCardState();
}

class _ContainerCardState extends State<ContainerCard> {
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: EdgeInsets.fromLTRB(10, 10, 10, 0),
      padding: EdgeInsets.all(10),
      width: double.infinity,
      decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10), color: Colors.white),
      child: widget.child,
    );
  }
}
