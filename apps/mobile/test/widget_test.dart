import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:agrichain_mobile/main.dart';
import 'package:agrichain_mobile/services/websocket_service.dart';
import 'package:agrichain_mobile/widgets/scientific_disclaimer_card.dart';
import 'package:agrichain_mobile/widgets/status_chip.dart';

void main() {
  group('Widget Tests', () {
    setUp(() {
      WebSocketService.enabled = false;
    });
    tearDown(() {
      WebSocketService.enabled = true;
      WebSocketService().disconnect();
    });
    testWidgets('ScientificDisclaimerCard renders disclaimers accurately',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ScientificDisclaimerCard(),
          ),
        ),
      );

      expect(find.text('Academic & Regulatory Notice'), findsOneWidget);
      expect(
        find.textContaining('Uncalibrated Softmax', findRichText: true),
        findsOneWidget,
      );
      expect(
        find.textContaining('Maturity Scope', findRichText: true),
        findsOneWidget,
      );
      expect(
        find.textContaining('Lot-Level Scope', findRichText: true),
        findsOneWidget,
      );
    });

    testWidgets('StatusChip renders formatted status string',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                StatusChip(status: 'in_transit'),
                StatusChip(status: 'delivered'),
                StatusChip(status: 'quarantined'),
              ],
            ),
          ),
        ),
      );

      expect(find.text('IN TRANSIT'), findsOneWidget);
      expect(find.text('DELIVERED'), findsOneWidget);
      expect(find.text('QUARANTINED'), findsOneWidget);
    });

    testWidgets('Main Navigation Shell renders tabs',
        (WidgetTester tester) async {
      await tester.pumpWidget(const AgriChainMobileApp());
      await tester.pump();

      expect(find.text('Dashboard'), findsOneWidget);
      expect(find.text('Shipments'), findsOneWidget);
      expect(find.text('Facilities'), findsOneWidget);
      expect(find.text('Guava AI'), findsOneWidget);

      WebSocketService().disconnect();
      await tester.pumpWidget(const SizedBox.shrink());
    });
  });
}
