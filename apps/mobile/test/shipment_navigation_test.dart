import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:agrichain_mobile/models/shipment.dart';
import 'package:agrichain_mobile/screens/shipment_detail_screen.dart';
import 'package:agrichain_mobile/screens/shipment_list_screen.dart';
import 'package:agrichain_mobile/screens/shipment_tracking_screen.dart';
import 'package:agrichain_mobile/services/websocket_service.dart';

void main() {
  setUp(() {
    WebSocketService.enabled = false;
  });

  tearDown(() {
    WebSocketService.enabled = true;
  });

  final testShipment1 = Shipment(
    id: 'SHP-2026-001',
    produceType: 'Guava',
    origin: 'Abohar Post-Harvest Center, Punjab',
    destination: 'Azadpur APMC Mandi, Delhi',
    status: 'in_transit',
    quantity: 450.0,
    quantityCrates: 450,
    temperatureC: 6.2,
    humidityPct: 88.0,
    riskIndex: 18.5,
    createdAt: '2026-10-18T10:00:00Z',
    lastUpdate: '2026-10-18T14:00:00Z',
    currentCoordinates: {'latitude': 30.1453, 'longitude': 74.1994},
  );

  final testShipment2 = Shipment(
    id: 'SHP-2026-002',
    produceType: 'Guava',
    origin: 'Fazilka CA Cold Store, Punjab',
    destination: 'Ludhiana Agro Cold Chain Warehouse',
    status: 'in_transit',
    quantity: 600.0,
    quantityCrates: 600,
    temperatureC: 5.8,
    humidityPct: 86.0,
    riskIndex: 22.0,
    createdAt: '2026-10-19T09:00:00Z',
    lastUpdate: '2026-10-19T12:00:00Z',
    currentCoordinates: {'latitude': 30.4035, 'longitude': 74.0255},
  );

  group('ShipmentListScreen Live Track Navigation Tests', () {
    testWidgets('renders clearly visible Live Track and Details buttons on every shipment card even on narrow screen', (tester) async {
      await tester.binding.setSurfaceSize(const Size(360, 800)); // Narrow Android screen test
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: ShipmentListScreen(
            initialShipments: [testShipment1, testShipment2],
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));

      // Check for both shipment cards
      expect(find.text('SHP-2026-001'), findsOneWidget);
      expect(find.text('SHP-2026-002'), findsOneWidget);

      // Check for visible "Live Track" and "Details" buttons for each card
      expect(find.byKey(const Key('live_track_btn_SHP-2026-001')), findsOneWidget);
      expect(find.byKey(const Key('live_track_btn_SHP-2026-002')), findsOneWidget);
      expect(find.byKey(const Key('details_btn_SHP-2026-001')), findsOneWidget);
      expect(find.byKey(const Key('details_btn_SHP-2026-002')), findsOneWidget);

      expect(find.text('Live Track'), findsNWidgets(2));
      expect(find.text('Details'), findsNWidgets(2));
    });

    testWidgets('tapping Live Track navigates to ShipmentTrackingScreen with correct ID', (tester) async {
      await tester.binding.setSurfaceSize(const Size(800, 1600));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: ShipmentListScreen(
            initialShipments: [testShipment1],
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));

      // Tap Live Track button
      final liveTrackBtn = find.byKey(const Key('live_track_btn_SHP-2026-001'));
      expect(liveTrackBtn, findsOneWidget);
      await tester.tap(liveTrackBtn);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // Verify ShipmentTrackingScreen is pushed
      expect(find.byType(ShipmentTrackingScreen), findsOneWidget);
      expect(find.text('Live Tracking: SHP-2026-001'), findsOneWidget);
    });

    testWidgets('tapping Details navigates to ShipmentDetailScreen with correct ID', (tester) async {
      await tester.binding.setSurfaceSize(const Size(800, 1600));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: ShipmentListScreen(
            initialShipments: [testShipment1],
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));

      // Tap Details button
      final detailsBtn = find.byKey(const Key('details_btn_SHP-2026-001'));
      expect(detailsBtn, findsOneWidget);
      await tester.tap(detailsBtn);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // Verify ShipmentDetailScreen is pushed
      expect(find.byType(ShipmentDetailScreen), findsOneWidget);
    });
  });

  group('ShipmentDetailScreen Live Track Navigation Tests', () {
    testWidgets('renders prominent Open Live Tracking button near the top', (tester) async {
      await tester.binding.setSurfaceSize(const Size(800, 1600));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: ShipmentDetailScreen(
            shipmentId: 'SHP-2026-001',
            initialShipment: testShipment1,
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));

      // Verify the prominent Open Live Tracking button exists near top of screen
      final openLiveTrackingBtn = find.byKey(const Key('open_live_tracking_button'));
      expect(openLiveTrackingBtn, findsOneWidget);
      expect(find.text('Open Live Tracking'), findsOneWidget);

      // Verify secondary tracking button and appbar action also exist
      expect(find.byKey(const Key('secondary_live_tracking_button')), findsOneWidget);
      expect(find.byKey(const Key('appbar_live_tracking_button')), findsOneWidget);

      // Verify existing detail screen components remain intact
      expect(find.text('Terminal Facilities'), findsOneWidget);
      expect(find.text('Geospatial Transit Corridor'), findsOneWidget);
      expect(find.text('Add GPS Fix'), findsWidgets);
      expect(find.text('Add Telemetry'), findsWidgets);
    });

    testWidgets('tapping Open Live Tracking navigates to ShipmentTrackingScreen', (tester) async {
      await tester.binding.setSurfaceSize(const Size(800, 1600));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: ShipmentDetailScreen(
            shipmentId: 'SHP-2026-001',
            initialShipment: testShipment1,
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));

      final openLiveTrackingBtn = find.byKey(const Key('open_live_tracking_button'));
      await tester.tap(openLiveTrackingBtn);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // Verify tracking screen opened
      expect(find.byType(ShipmentTrackingScreen), findsOneWidget);
      expect(find.text('Live Tracking: SHP-2026-001'), findsOneWidget);
    });

    testWidgets('existing Add GPS Fix and Add Telemetry modals continue working', (tester) async {
      await tester.binding.setSurfaceSize(const Size(800, 1600));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: ShipmentDetailScreen(
            shipmentId: 'SHP-2026-001',
            initialShipment: testShipment1,
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));

      // Tap bottom bar Add Telemetry button
      final addTelemetryBtn = find.widgetWithText(ElevatedButton, 'Add Telemetry');
      expect(addTelemetryBtn, findsOneWidget);
      await tester.tap(addTelemetryBtn);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // Verify telemetry modal opened
      expect(find.text('Record Telemetry Reading'), findsOneWidget);
      expect(find.text('Record to Cold Chain'), findsOneWidget);

      // Dismiss modal
      final BuildContext modalContext = tester.element(find.text('Record Telemetry Reading'));
      Navigator.of(modalContext).pop();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.text('Record Telemetry Reading'), findsNothing);

      // Tap bottom bar Add GPS Fix button
      final addGpsBtn = find.widgetWithText(OutlinedButton, 'Add GPS Fix');
      expect(addGpsBtn, findsOneWidget);
      await tester.tap(addGpsBtn);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // Verify GPS fix modal opened
      expect(find.text('Record GPS Waypoint Fix'), findsOneWidget);
      expect(find.text('Commit PostGIS Waypoint'), findsOneWidget);
    });
  });
}
