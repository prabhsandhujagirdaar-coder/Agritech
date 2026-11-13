import 'package:flutter_test/flutter_test.dart';
import 'package:agrichain_mobile/models/geo_waypoint.dart';
import 'package:agrichain_mobile/models/shipment.dart';

void main() {
  group('GeoWaypoint & Shipment Geospatial Tests', () {
    test('GeoWaypoint.fromJson parses PostGIS coordinates', () {
      final json = {
        'id': 'WP-101',
        'shipment_id': 'SHP-2026-001',
        'latitude': 30.2110,
        'longitude': 74.9455,
        'speed_kmh': 62.5,
        'heading_deg': 110.0,
        'location_metadata': {'corridor': 'NH-7', 'toll': 'Malout'},
        'recorded_at': '2026-10-18T12:00:00Z',
      };

      final wp = GeoWaypoint.fromJson(json);

      expect(wp.id, 'WP-101');
      expect(wp.shipmentId, 'SHP-2026-001');
      expect(wp.latitude, 30.2110);
      expect(wp.longitude, 74.9455);
      expect(wp.speedKmh, 62.5);
      expect(wp.headingDeg, 110.0);
      expect(wp.locationMetadata['corridor'], 'NH-7');
      expect(wp.formattedCoordinates, '30.2110°N, 74.9455°E');
    });

    test('Shipment parses currentCoordinates and latestWaypoint correctly', () {
      final json = {
        'id': 'SHP-2026-001',
        'produce_type': 'Guava',
        'origin': 'Abohar Post-Harvest Center',
        'destination': 'Azadpur APMC Mandi, Delhi',
        'status': 'in_transit',
        'quantity': 450.0,
        'quantity_crates': 450,
        'risk_index': 18.5,
        'created_at': '2026-10-18T10:00:00Z',
        'last_update': '2026-10-18T14:00:00Z',
        'current_coordinates': {'latitude': 30.1453, 'longitude': 74.1994},
        'latest_waypoint': {
          'id': 'WP-1',
          'shipment_id': 'SHP-2026-001',
          'latitude': 30.1453,
          'longitude': 74.1994,
          'speed_kmh': 50.0,
          'recorded_at': '2026-10-18T14:00:00Z',
        },
      };

      final shipment = Shipment.fromJson(json);

      expect(shipment.hasGps, isTrue);
      expect(shipment.latitude, 30.1453);
      expect(shipment.longitude, 74.1994);
      expect(shipment.latestWaypoint?.id, 'WP-1');
      expect(shipment.formattedGps, '30.1453°N, 74.1994°E');
    });

    test('Shipment handles missing GPS gracefully', () {
      final json = {
        'id': 'SHP-2026-004',
        'produce_type': 'Guava',
        'origin': 'Abohar',
        'destination': 'Bathinda',
        'status': 'created',
        'quantity': 300.0,
        'quantity_crates': 300,
        'risk_index': 5.0,
        'created_at': '2026-10-18T10:00:00Z',
        'last_update': '2026-10-18T10:00:00Z',
        'current_coordinates': null,
        'latest_waypoint': null,
      };

      final shipment = Shipment.fromJson(json);

      expect(shipment.hasGps, isFalse);
      expect(shipment.latitude, isNull);
      expect(shipment.longitude, isNull);
      expect(shipment.formattedGps, 'Location Unavailable');
    });
  });
}
