import 'package:flutter_test/flutter_test.dart';
import 'package:agrichain_mobile/models/cnn_prediction.dart';
import 'package:agrichain_mobile/models/risk_info.dart';
import 'package:agrichain_mobile/models/shipment.dart';
import 'package:agrichain_mobile/models/telemetry.dart';

void main() {
  group('Model Serialization & Logic Tests', () {
    test('Shipment.fromJson parses correctly', () {
      final json = {
        'id': 'SHP-2026-001',
        'produce_type': 'Guava',
        'origin': 'Abohar Packhouse',
        'destination': 'Ludhiana Mandi',
        'status': 'in_transit',
        'quantity': 450.0,
        'quantity_crates': 45,
        'temperature_c': 6.2,
        'humidity_pct': 87.0,
        'risk_index': 24.5,
        'created_at': '2026-10-21T08:00:00Z',
        'last_update': '2026-10-21T12:00:00Z',
      };

      final shipment = Shipment.fromJson(json);

      expect(shipment.id, 'SHP-2026-001');
      expect(shipment.produceType, 'Guava');
      expect(shipment.isInTransit, isTrue);
      expect(shipment.isAlert, isFalse);
      expect(shipment.quantity, 450.0);
    });

    test('Shipment alert flag triggers when riskIndex > 50', () {
      final json = {
        'id': 'SHP-2026-002',
        'produce_type': 'Guava',
        'origin': 'Fazilka',
        'destination': 'Delhi Mandi',
        'status': 'delayed',
        'quantity': 300.0,
        'quantity_crates': 30,
        'risk_index': 62.4,
        'created_at': '2026-10-21T08:00:00Z',
        'last_update': '2026-10-21T12:00:00Z',
      };

      final shipment = Shipment.fromJson(json);
      expect(shipment.isAlert, isTrue);
      expect(shipment.isInTransit, isFalse);
    });

    test('TelemetryRecord thermal excursion detection (4°C - 8°C)', () {
      final normalRecord = TelemetryRecord.fromJson({
        'id': 'TEL-1',
        'shipment_id': 'SHP-2026-001',
        'temperature': 6.5,
        'humidity': 85.0,
        'sensor_id': 'SNS-01',
        'location': 'Malout',
        'timestamp': '2026-10-21T10:00:00Z',
      });
      expect(normalRecord.isThermalExcursion, isFalse);

      final warmExcursion = TelemetryRecord.fromJson({
        'id': 'TEL-2',
        'shipment_id': 'SHP-2026-001',
        'temperature': 9.2,
        'humidity': 80.0,
        'sensor_id': 'SNS-01',
        'location': 'Bathinda',
        'timestamp': '2026-10-21T11:00:00Z',
      });
      expect(warmExcursion.isThermalExcursion, isTrue);

      final coldExcursion = TelemetryRecord.fromJson({
        'id': 'TEL-3',
        'shipment_id': 'SHP-2026-001',
        'temperature': 3.1,
        'humidity': 90.0,
        'sensor_id': 'SNS-01',
        'location': 'Barnala',
        'timestamp': '2026-10-21T12:00:00Z',
      });
      expect(coldExcursion.isThermalExcursion, isTrue);
    });

    test('ShipmentRiskInfo parses correctly', () {
      final json = {
        'shipment_id': 'SHP-2026-001',
        'current_risk': 18.5,
        'predicted_arrival_risk': 21.2,
        'alert': false,
        'telemetry_points_evaluated': 12,
        'avg_temperature_c': 6.4,
        'excursion_events': 0,
      };

      final risk = ShipmentRiskInfo.fromJson(json);
      expect(risk.shipmentId, 'SHP-2026-001');
      expect(risk.currentRisk, 18.5);
      expect(risk.alert, isFalse);
      expect(risk.excursionEvents, 0);
    });

    test('CNNPredictionResult parses and handles clear prediction', () {
      final json = {
        'predicted_class': 'Green',
        'class_index': 0,
        'label': 'Green',
        'confidence': 0.9706,
        'probabilities': {
          'Green': 0.9706,
          'Mature Green': 0.0241,
          'Ripe': 0.0053,
        },
        'target_crop': 'guava',
        'model_name': 'resnet18',
        'model_version': '2.0.0',
        'device': 'cuda',
        'inference_ms': 16.5,
      };

      final result = CNNPredictionResult.fromJson(json);
      expect(result.predictedClass, 'Green');
      expect(result.confidence, 0.9706);
      expect(result.device, 'cuda');
      expect(result.isUncertain, isFalse);
      expect(result.uncertaintyReason, isNull);
    });

    test('CNNPredictionResult triggers uncertainty on low score (<60%)', () {
      final json = {
        'predicted_class': 'Mature Green',
        'class_index': 1,
        'label': 'Mature Green',
        'confidence': 0.5072,
        'probabilities': {
          'Green': 0.2500,
          'Mature Green': 0.5072,
          'Ripe': 0.2428,
        },
        'target_crop': 'guava',
        'model_name': 'resnet18',
        'device': 'cuda',
      };

      final result = CNNPredictionResult.fromJson(json);
      expect(result.isUncertain, isTrue);
      expect(result.uncertaintyReason, contains('below the 60% threshold'));
    });

    test('CNNPredictionResult triggers uncertainty on close margin (<15%)', () {
      final json = {
        'predicted_class': 'Mature Green',
        'class_index': 1,
        'label': 'Mature Green',
        'confidence': 0.6500,
        'probabilities': {
          'Green': 0.1000,
          'Mature Green': 0.6500,
          'Ripe': 0.5800, // margin is 0.07 (7%), which is < 15%
        },
        'target_crop': 'guava',
        'model_name': 'resnet18',
        'device': 'cuda',
      };

      final result = CNNPredictionResult.fromJson(json);
      expect(result.isUncertain, isTrue);
      expect(result.uncertaintyReason, contains('Close classification margin'));
    });
  });
}
