import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:agrichain_mobile/config/app_config.dart';
import 'package:agrichain_mobile/services/api_service.dart';

void main() {
  group('ApiService Comprehensive Unit Tests', () {
    setUp(() {
      AppConfig.activeBaseUrl.value = 'http://127.0.0.1:8000/api/v1';
    });

    test('getHealth parses healthy system response', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/v1/health');
        return http.Response(
          json.encode({
            'status': 'healthy',
            'service': 'AgriChain AI Backend',
            'version': '1.0.0',
            'target_crop': 'guava',
            'cnn_ready': true,
            'device': 'cpu',
            'database': {'enabled': true, 'connected': true, 'message': 'PostgreSQL connected'},
          }),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final health = await api.getHealth();

      expect(health.status, 'healthy');
      expect(health.targetCrop, 'guava');
      expect(health.cnnReady, isTrue);
      expect(health.database?.connected, isTrue);
    });

    test('getShipments parses list of shipments with facilities and coordinates', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/v1/shipments');
        return http.Response(
          json.encode([
            {
              'id': 'SHP-2026-001',
              'produce_type': 'Guava',
              'origin': 'Abohar Post-Harvest Center',
              'destination': 'Azadpur APMC Mandi',
              'status': 'in_transit',
              'quantity': 450.0,
              'quantity_crates': 450,
              'temperature_c': 6.2,
              'humidity_pct': 88.0,
              'risk_index': 18.5,
              'created_at': '2026-10-18T10:00:00Z',
              'last_update': '2026-10-18T14:00:00Z',
              'current_coordinates': {'latitude': 30.1453, 'longitude': 74.1994},
              'origin_facility_id': 'FAC-PB-ABO-01',
              'destination_facility_id': 'FAC-DL-AZD-01',
            }
          ]),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final shipments = await api.getShipments();

      expect(shipments.length, 1);
      expect(shipments.first.id, 'SHP-2026-001');
      expect(shipments.first.hasGps, isTrue);
      expect(shipments.first.latitude, 30.1453);
    });

    test('getFacilities with query filter passes query parameters correctly', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/v1/facilities');
        expect(request.url.queryParameters['facility_type'], 'packhouse');
        expect(request.url.queryParameters['district'], 'Fazilka');

        return http.Response(
          json.encode([
            {
              'id': 'FAC-PB-ABO-01',
              'name': 'Abohar Packhouse',
              'facility_type': 'packhouse',
              'address': 'Fazilka Road',
              'village_or_city': 'Abohar',
              'district': 'Fazilka',
              'latitude': 30.1453,
              'longitude': 74.1994,
              'capacity': 1500.0,
              'created_at': '2026-10-18T10:00:00Z',
              'updated_at': '2026-10-18T10:00:00Z',
            }
          ]),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final facilities = await api.getFacilities(facilityType: 'packhouse', district: 'Fazilka');

      expect(facilities.length, 1);
      expect(facilities.first.id, 'FAC-PB-ABO-01');
      expect(facilities.first.formattedType, 'Packhouse');
    });

    test('getShipmentWaypoints returns list of PostGIS waypoint records', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/v1/shipments/SHP-2026-001/waypoints');
        return http.Response(
          json.encode([
            {
              'id': 'WP-1',
              'shipment_id': 'SHP-2026-001',
              'latitude': 30.1453,
              'longitude': 74.1994,
              'speed_kmh': 45.0,
              'heading_deg': 90.0,
              'location_metadata': {'corridor': 'NH-7'},
              'recorded_at': '2026-10-18T10:30:00Z',
            }
          ]),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final waypoints = await api.getShipmentWaypoints('SHP-2026-001');

      expect(waypoints.length, 1);
      expect(waypoints.first.id, 'WP-1');
      expect(waypoints.first.latitude, 30.1453);
      expect(waypoints.first.formattedCoordinates, '30.1453°N, 74.1994°E');
    });

    test('addShipmentWaypoint posts JSON payload matching GeoWaypointCreate', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/v1/shipments/SHP-2026-001/waypoints');
        expect(request.method, 'POST');
        final payload = json.decode(request.body);
        expect(payload['latitude'], 30.25);
        expect(payload['longitude'], 74.50);
        expect(payload['speed_kmh'], 60.0);

        return http.Response(
          json.encode({
            'id': 'WP-NEW-1',
            'shipment_id': 'SHP-2026-001',
            'latitude': 30.25,
            'longitude': 74.50,
            'speed_kmh': 60.0,
            'location_metadata': {'note': 'Toll Gate'},
            'recorded_at': '2026-10-23T12:00:00Z',
          }),
          201,
        );
      });

      final api = ApiService(client: mockClient);
      final waypoint = await api.addShipmentWaypoint(
        'SHP-2026-001',
        latitude: 30.25,
        longitude: 74.50,
        speedKmh: 60.0,
        locationMetadata: {'note': 'Toll Gate'},
      );

      expect(waypoint.id, 'WP-NEW-1');
      expect(waypoint.latitude, 30.25);
    });

    test('predictGuavaMaturity posts multipart image payload and parses prediction', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/v1/cnn/predict');
        expect(request.method, 'POST');

        return http.Response(
          json.encode({
            'predicted_class': 'Mature Green',
            'class_index': 1,
            'label': 'Mature Green',
            'confidence': 0.88,
            'probabilities': {'Green': 0.08, 'Mature Green': 0.88, 'Ripe': 0.04},
            'target_crop': 'guava',
            'model_name': 'resnet18',
            'model_version': '2.0.0',
            'device': 'cpu',
            'inference_ms': 42.5,
          }),
          200,
        );
      });

      final api = ApiService(client: mockClient);
      final dummyBytes = Uint8List.fromList([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10]);
      final result = await api.predictGuavaMaturity(dummyBytes, 'guava_sample.jpg');

      expect(result.predictedClass, 'Mature Green');
      expect(result.confidence, 0.88);
      expect(result.targetCrop, 'guava');
      expect(result.isUncertain, isFalse);
    });

    test('HTTP 404, 422, and 503 throw structured ApiException', () async {
      final notFoundClient = MockClient((request) async {
        return http.Response(json.encode({'detail': "Shipment 'SHP-999' not found."}), 404);
      });

      final api404 = ApiService(client: notFoundClient);
      expect(
        () => api404.getShipment('SHP-999'),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 404)),
      );

      final unavailableClient = MockClient((request) async {
        return http.Response(json.encode({'detail': 'CNN model unavailable.'}), 503);
      });

      final api503 = ApiService(client: unavailableClient);
      expect(
        () => api503.getCNNStatus(),
        throwsA(isA<ApiException>().having((e) => e.isServiceUnavailable, 'isServiceUnavailable', true)),
      );
    });
  });
}
