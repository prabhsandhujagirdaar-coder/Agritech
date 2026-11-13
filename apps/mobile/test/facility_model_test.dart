import 'package:flutter_test/flutter_test.dart';
import 'package:agrichain_mobile/models/facility.dart';

void main() {
  group('Facility Model Serialization & Logic Tests', () {
    test('Facility.fromJson parses packhouse fixture correctly', () {
      final json = {
        'id': 'FAC-PB-ABO-01',
        'name': 'Abohar Guava & Citrus Post-Harvest Center',
        'facility_type': 'packhouse',
        'address': 'Fazilka Road, Abohar Industrial Area',
        'village_or_city': 'Abohar',
        'district': 'Fazilka',
        'state': 'Punjab',
        'postal_code': '152116',
        'latitude': 30.1453,
        'longitude': 74.1994,
        'coordinates': {'latitude': 30.1453, 'longitude': 74.1994},
        'capacity': 1500.0,
        'capacity_unit': 'MT',
        'current_utilization': 62.0,
        'storage_temperature_min_c': 4.0,
        'storage_temperature_max_c': 8.0,
        'operational_status': 'active',
        'location_verification_status': 'demo_simulated',
        'created_at': '2026-10-18T10:00:00Z',
        'updated_at': '2026-10-18T10:00:00Z',
      };

      final facility = Facility.fromJson(json);

      expect(facility.id, 'FAC-PB-ABO-01');
      expect(facility.name, 'Abohar Guava & Citrus Post-Harvest Center');
      expect(facility.facilityType, 'packhouse');
      expect(facility.formattedType, 'Packhouse');
      expect(facility.latitude, 30.1453);
      expect(facility.longitude, 74.1994);
      expect(facility.isDemoSimulated, isTrue);
      expect(facility.isVerified, isFalse);
      expect(facility.formattedTempRange, '4.0°C – 8.0°C');
    });

    test('Facility.fromJson formats cold_storage and mandi classifications', () {
      final coldStorage = Facility.fromJson({
        'id': 'FAC-PB-FAZ-01',
        'name': 'Fazilka CA Cold Store',
        'facility_type': 'cold_storage',
        'address': 'Bypass',
        'village_or_city': 'Fazilka',
        'district': 'Fazilka',
        'latitude': 30.4037,
        'longitude': 74.0254,
        'location_verification_status': 'verified',
        'created_at': '2026-10-18T10:00:00Z',
        'updated_at': '2026-10-18T10:00:00Z',
      });

      expect(coldStorage.formattedType, 'Cold Storage');
      expect(coldStorage.isVerified, isTrue);
      expect(coldStorage.isDemoSimulated, isFalse);

      final mandi = Facility.fromJson({
        'id': 'FAC-PB-ASR-01',
        'name': 'Amritsar Fruit Mandi',
        'facility_type': 'mandi',
        'address': 'Mandi Complex',
        'village_or_city': 'Amritsar',
        'district': 'Amritsar',
        'latitude': 31.6340,
        'longitude': 74.8723,
        'created_at': '2026-10-18T10:00:00Z',
        'updated_at': '2026-10-18T10:00:00Z',
      });

      expect(mandi.formattedType, 'Mandi Terminal');
    });
  });
}
