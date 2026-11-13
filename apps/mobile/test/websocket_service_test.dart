import 'package:flutter_test/flutter_test.dart';
import 'package:agrichain_mobile/config/app_config.dart';
import 'package:agrichain_mobile/services/websocket_service.dart';

void main() {
  group('WebSocket Service & URL Derivation Tests', () {
    test('AppConfig.getWsUrl derives WebSocket URL from http host', () {
      AppConfig.activeBaseUrl.value = 'http://10.0.2.2:8000/api/v1';
      expect(AppConfig.getWsUrl('/ws/shipments'), 'ws://10.0.2.2:8000/ws/shipments');

      AppConfig.activeBaseUrl.value = 'http://127.0.0.1:8000/api/v1';
      expect(AppConfig.getWsUrl('/ws'), 'ws://127.0.0.1:8000/ws');

      AppConfig.activeBaseUrl.value = 'https://prod.agrichain.in/api/v1';
      expect(AppConfig.getWsUrl('/ws/shipments'), 'wss://prod.agrichain.in/ws/shipments');
    });

    test('WebSocketEvent.fromJson parses telemetry_update and shipment_created', () {
      final telemetryEventJson = {
        'event': 'telemetry_update',
        'data': {
          'id': 'TEL-202',
          'shipment_id': 'SHP-2026-001',
          'temperature': 6.8,
          'humidity': 86.2,
          'sensor_id': 'SNS-01',
          'location': 'Toll Plaza',
          'timestamp': '2026-10-23T10:00:00Z',
        },
        'timestamp': '2026-10-23T10:00:00Z',
      };

      final telemEvent = WebSocketEvent.fromJson(telemetryEventJson);
      expect(telemEvent.event, 'telemetry_update');
      expect(telemEvent.data['shipment_id'], 'SHP-2026-001');
      expect(telemEvent.data['temperature'], 6.8);

      final shipmentEventJson = {
        'event': 'shipment_created',
        'data': {
          'id': 'SHP-2026-999',
          'produce_type': 'Guava',
          'origin': 'Fazilka',
          'destination': 'Ludhiana',
          'status': 'created',
          'quantity': 500.0,
          'quantity_crates': 50,
          'risk_index': 0.0,
          'created_at': '2026-10-23T10:00:00Z',
          'last_update': '2026-10-23T10:00:00Z',
        },
        'timestamp': '2026-10-23T10:00:00Z',
      };

      final shpEvent = WebSocketEvent.fromJson(shipmentEventJson);
      expect(shpEvent.event, 'shipment_created');
      expect(shpEvent.data['id'], 'SHP-2026-999');
      expect(shpEvent.data['status'], 'created');
    });
  });
}
