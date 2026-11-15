// AgriChain AI — Storage Facility & Godown Model
// Represents cold stores, packhouses, godowns, warehouses, and mandis.

class Facility {
  final String id;
  final String name;
  final String facilityType;
  final String address;
  final String villageOrCity;
  final String district;
  final String state;
  final String? postalCode;
  final double latitude;
  final double longitude;
  final Map<String, double> coordinates;
  final double? capacity;
  final String capacityUnit;
  final double? currentUtilization;
  final double? storageTemperatureMinC;
  final double? storageTemperatureMaxC;
  final String operationalStatus;
  final String locationVerificationStatus;
  final String createdAt;
  final String updatedAt;

  Facility({
    required this.id,
    required this.name,
    required this.facilityType,
    required this.address,
    required this.villageOrCity,
    required this.district,
    this.state = 'Punjab',
    this.postalCode,
    required this.latitude,
    required this.longitude,
    required this.coordinates,
    this.capacity,
    this.capacityUnit = 'MT',
    this.currentUtilization,
    this.storageTemperatureMinC = 4.0,
    this.storageTemperatureMaxC = 8.0,
    this.operationalStatus = 'active',
    this.locationVerificationStatus = 'demo_simulated',
    required this.createdAt,
    required this.updatedAt,
  });

  factory Facility.fromJson(Map<String, dynamic> json) {
    final lat = (json['latitude'] as num?)?.toDouble() ??
        (json['coordinates'] is Map ? (json['coordinates']['latitude'] as num?)?.toDouble() : null) ??
        0.0;
    final lon = (json['longitude'] as num?)?.toDouble() ??
        (json['coordinates'] is Map ? (json['coordinates']['longitude'] as num?)?.toDouble() : null) ??
        0.0;

    return Facility(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Unnamed Facility',
      facilityType: json['facility_type']?.toString().toLowerCase() ?? 'godown',
      address: json['address']?.toString() ?? '',
      villageOrCity: json['village_or_city']?.toString() ?? '',
      district: json['district']?.toString() ?? '',
      state: json['state']?.toString() ?? 'Punjab',
      postalCode: json['postal_code']?.toString(),
      latitude: lat,
      longitude: lon,
      coordinates: {
        'latitude': lat,
        'longitude': lon,
      },
      capacity: (json['capacity'] as num?)?.toDouble(),
      capacityUnit: json['capacity_unit']?.toString() ?? 'MT',
      currentUtilization: (json['current_utilization'] as num?)?.toDouble(),
      storageTemperatureMinC: (json['storage_temperature_min_c'] as num?)?.toDouble() ?? 4.0,
      storageTemperatureMaxC: (json['storage_temperature_max_c'] as num?)?.toDouble() ?? 8.0,
      operationalStatus: json['operational_status']?.toString().toLowerCase() ?? 'active',
      locationVerificationStatus:
          json['location_verification_status']?.toString().toLowerCase() ?? 'demo_simulated',
      createdAt: json['created_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'facility_type': facilityType,
        'address': address,
        'village_or_city': villageOrCity,
        'district': district,
        'state': state,
        'postal_code': postalCode,
        'latitude': latitude,
        'longitude': longitude,
        'coordinates': coordinates,
        'capacity': capacity,
        'capacity_unit': capacityUnit,
        'current_utilization': currentUtilization,
        'storage_temperature_min_c': storageTemperatureMinC,
        'storage_temperature_max_c': storageTemperatureMaxC,
        'operational_status': operationalStatus,
        'location_verification_status': locationVerificationStatus,
        'created_at': createdAt,
        'updated_at': updatedAt,
      };

  bool get isDemoSimulated => locationVerificationStatus == 'demo_simulated';
  bool get isVerified => locationVerificationStatus == 'verified';

  String get formattedType {
    switch (facilityType) {
      case 'cold_storage':
        return 'Cold Storage';
      case 'packhouse':
        return 'Packhouse';
      case 'godown':
        return 'Godown';
      case 'warehouse':
        return 'Warehouse';
      case 'mandi':
        return 'Mandi Terminal';
      default:
        return facilityType.toUpperCase();
    }
  }

  String get formattedTempRange {
    final min = storageTemperatureMinC?.toStringAsFixed(1) ?? '4.0';
    final max = storageTemperatureMaxC?.toStringAsFixed(1) ?? '8.0';
    return '$min°C – $max°C';
  }
}
