import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:agrichain_mobile/config/app_config.dart';
import 'package:agrichain_mobile/models/geo_waypoint.dart';
import 'package:agrichain_mobile/models/shipment.dart';
import 'package:agrichain_mobile/screens/shipment_tracking_screen.dart';
import 'package:agrichain_mobile/services/websocket_service.dart';
import 'package:agrichain_mobile/widgets/interactive_route_map.dart';

void main() {
  setUp(() {
    WebSocketService.enabled = false;
    AppConfig.activeBaseUrl.value = 'http://127.0.0.1:8000/api/v1';
  });

  tearDown(() {
    WebSocketService.enabled = true;
  });

  final testShipment = Shipment(
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

  final testWaypoints = [
    GeoWaypoint(
      id: 'WAY-001-1',
      shipmentId: 'SHP-2026-001',
      latitude: 30.1453,
      longitude: 74.1994,
      altitudeM: 186.0,
      speedKmh: 45.0,
      headingDeg: 85.0,
      locationMetadata: {'hub': 'Abohar Packhouse', 'district': 'Fazilka'},
      recordedAt: '2026-10-18T14:00:00Z',
    ),
    GeoWaypoint(
      id: 'WAY-001-2',
      shipmentId: 'SHP-2026-001',
      latitude: 30.1915,
      longitude: 74.4989,
      altitudeM: 192.0,
      speedKmh: 62.0,
      headingDeg: 78.0,
      locationMetadata: {'corridor': 'Malout Corridor', 'district': 'Muktsar'},
      recordedAt: '2026-10-18T14:30:00Z',
    ),
  ];

  group('InteractiveRouteMap Vector Canvas Tests', () {
    testWidgets('renders map canvas, compass rose, and Live Telemetry badge', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: InteractiveRouteMap(
              shipment: testShipment,
              waypoints: testWaypoints,
              isDemoMode: false,
              currentLat: 30.1915,
              currentLon: 74.4989,
              speedKmh: 62.0,
              headingDeg: 78.0,
            ),
          ),
        ),
      );

      // Verify True North indicator
      expect(find.text('N'), findsOneWidget);
      expect(find.text('WGS84 SRID 4326'), findsOneWidget);

      // Verify Live Telemetry badge
      expect(find.text('LIVE TELEMETRY'), findsOneWidget);

      // Verify schematic corridor disclaimer
      expect(find.textContaining('Schematic transit corridor'), findsOneWidget);

      // Verify reset zoom fab
      expect(find.byType(FloatingActionButton), findsOneWidget);
    });

    testWidgets('renders DEMO / SIMULATED watermark badge when isDemoMode is true', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: InteractiveRouteMap(
              shipment: testShipment,
              waypoints: testWaypoints,
              isDemoMode: true,
              currentLat: 30.1915,
              currentLon: 74.4989,
            ),
          ),
        ),
      );

      expect(find.text('DEMO / SIMULATED'), findsOneWidget);
      expect(find.text('LIVE TELEMETRY'), findsNothing);
    });
  });

  group('ShipmentTrackingScreen Rendering & State Tests', () {
    testWidgets('renders loading state initially while snapshot loads', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ShipmentTrackingScreen(shipmentId: 'SHP-2026-001'),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.textContaining('Connecting to supply chain tracking gateway'), findsOneWidget);
    });

    testWidgets('renders tracking screen with initial shipment fallback and offline badge', (tester) async {
      await tester.binding.setSurfaceSize(const Size(800, 1600));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: ShipmentTrackingScreen(
            shipmentId: 'SHP-2026-001',
            initialShipment: testShipment,
          ),
        ),
      );

      // Flush pump to process the initial state
      await tester.pump(const Duration(milliseconds: 50));

      // Title & Produce
      expect(find.text('Live Tracking: SHP-2026-001'), findsOneWidget);
      expect(find.text('Guava Supply Chain Corridor Radar'), findsOneWidget);

      // Offline connection badge (since test has WebSocket disabled)
      expect(find.text('OFFLINE'), findsOneWidget);

      // Demo Mode toggle switch exists
      expect(find.text('Demo / Simulation Mode'), findsOneWidget);
      expect(find.byType(Switch), findsOneWidget);
    });

    testWidgets('enabling demo mode displays prominent simulation warning banner and controls', (tester) async {
      await tester.binding.setSurfaceSize(const Size(800, 1600));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: ShipmentTrackingScreen(
            shipmentId: 'SHP-2026-001',
            initialShipment: testShipment,
          ),
        ),
      );

      await tester.pump(const Duration(milliseconds: 50));

      // Toggle demo mode switch
      final switchFinder = find.byType(Switch);
      expect(switchFinder, findsOneWidget);
      await tester.tap(switchFinder);
      await tester.pump();

      // Check for Demo warning banner
      expect(find.textContaining('DEMO / SIMULATION MODE ACTIVE'), findsOneWidget);
      expect(find.textContaining('Vehicle coordinates and sensor readings are generated for testing'), findsOneWidget);

      // Check for Demo simulation action buttons
      expect(find.text('Next Step'), findsOneWidget);
      expect(find.text('Play Auto (3s)'), findsOneWidget);

      // Check badge changed to DEMO
      expect(find.text('DEMO'), findsOneWidget);
    });
  });

  group('WebSocket & Event Parsing Edge Case Tests', () {
    test('parses location_update event correctly', () {
      final json = {
        'event': 'location_update',
        'data': {
          'shipment_id': 'SHP-2026-001',
          'latitude': 30.2110,
          'longitude': 74.9455,
          'speed_kmh': 58.0,
          'heading_deg': 110.0,
          'recorded_at': '2026-10-25T10:00:00Z',
        },
        'timestamp': '2026-10-25T10:00:00Z',
      };

      final event = WebSocketEvent.fromJson(json);
      expect(event.event, 'location_update');
      expect(event.data['shipment_id'], 'SHP-2026-001');
      expect(event.data['latitude'], 30.2110);
      expect(event.data['longitude'], 74.9455);
      expect(event.data['speed_kmh'], 58.0);
    });

    test('parses risk_update event correctly', () {
      final json = {
        'event': 'risk_update',
        'data': {
          'shipment_id': 'SHP-2026-001',
          'current_risk': 32.5,
          'predicted_arrival_risk': 37.4,
          'alert': false,
          'telemetry_points_evaluated': 12,
          'avg_temperature_c': 6.8,
          'excursion_events': 1,
        },
        'timestamp': '2026-10-25T10:00:00Z',
      };

      final event = WebSocketEvent.fromJson(json);
      expect(event.event, 'risk_update');
      expect(event.data['current_risk'], 32.5);
      expect(event.data['alert'], isFalse);
    });

    test('gracefully handles malformed or missing event data without throwing', () {
      final emptyEvent = WebSocketEvent.fromJson({'event': 'unknown'});
      expect(emptyEvent.event, 'unknown');
      expect(emptyEvent.data, isEmpty);

      final nullDataEvent = WebSocketEvent.fromJson({'event': 'location_update', 'data': null});
      expect(nullDataEvent.event, 'location_update');
      expect(nullDataEvent.data, isEmpty);
    });
  });
}
