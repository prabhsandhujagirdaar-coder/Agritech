import 'package:flutter/material.dart';

class StatusChip extends StatelessWidget {
  final String status;

  const StatusChip({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color fg;
    final normalized = status.toLowerCase();

    switch (normalized) {
      case 'in_transit':
        bg = Colors.blue.shade100;
        fg = Colors.blue.shade900;
        break;
      case 'delivered':
        bg = Colors.green.shade100;
        fg = Colors.green.shade900;
        break;
      case 'delayed':
        bg = Colors.amber.shade100;
        fg = Colors.amber.shade900;
        break;
      case 'quarantined':
        bg = Colors.red.shade100;
        fg = Colors.red.shade900;
        break;
      case 'created':
      default:
        bg = Colors.grey.shade200;
        fg = Colors.grey.shade800;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        status.replaceAll('_', ' ').toUpperCase(),
        style: TextStyle(
          color: fg,
          fontSize: 11,
          fontWeight: FontWeight.bold,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
