import 'facility.dart';
import 'geo_waypoint.dart';

class Shipment {
  final String id;
  final String produceType;
  final String origin;
  final String destination;
  final String status;
  final double quantity;
  final int quantityCrates;
  final double? temperatureC;
  final double? humidityPct;
  final double riskIndex;
  final String createdAt;
  final String lastUpdate;
  final Map<String, double>? currentCoordinates;
  final GeoWaypoint? latestWaypoint;
  final String? originFacilityId;
  final String? destinationFacilityId;
  final Facility? originFacility;
  final Facility? destinationFacility;

  Shipment({
    required this.id,
    required this.produceType,
    required this.origin,
    required this.destination,
    required this.status,
    required this.quantity,
    required this.quantityCrates,
    this.temperatureC,
    this.humidityPct,
    required this.riskIndex,
    required this.createdAt,
    required this.lastUpdate,
    this.currentCoordinates,
    this.latestWaypoint,
    this.originFacilityId,
    this.destinationFacilityId,
    this.originFacility,
    this.destinationFacility,
  });

  factory Shipment.fromJson(Map<String, dynamic> json) {
    Map<String, double>? coords;
    if (json['current_coordinates'] is Map) {
      final m = json['current_coordinates'] as Map;
      final lat = (m['latitude'] as num?)?.toDouble();
      final lon = (m['longitude'] as num?)?.toDouble();
      if (lat != null && lon != null) {
        coords = {'latitude': lat, 'longitude': lon};
      }
    }

    GeoWaypoint? waypoint;
    if (json['latest_waypoint'] is Map<String, dynamic>) {
      waypoint = GeoWaypoint.fromJson(json['latest_waypoint'] as Map<String, dynamic>);
    }

    Facility? oFac;
    if (json['origin_facility'] is Map<String, dynamic>) {
      oFac = Facility.fromJson(json['origin_facility'] as Map<String, dynamic>);
    }

    Facility? dFac;
    if (json['destination_facility'] is Map<String, dynamic>) {
      dFac = Facility.fromJson(json['destination_facility'] as Map<String, dynamic>);
    }

    return Shipment(
      id: json['id']?.toString() ?? '',
      produceType: json['produce_type']?.toString() ??
          json['produce']?.toString() ??
          'Guava',
      origin: json['origin']?.toString() ?? 'Unknown Origin',
      destination: json['destination']?.toString() ?? 'Unknown Destination',
      status: json['status']?.toString() ?? 'created',
      quantity: (json['quantity'] as num?)?.toDouble() ?? 0.0,
      quantityCrates: (json['quantity_crates'] as num?)?.toInt() ?? 0,
      temperatureC: (json['temperature_c'] as num?)?.toDouble(),
      humidityPct: (json['humidity_pct'] as num?)?.toDouble(),
      riskIndex: (json['risk_index'] as num?)?.toDouble() ?? 0.0,
      createdAt: json['created_at']?.toString() ?? '',
      lastUpdate: json['last_update']?.toString() ?? '',
      currentCoordinates: coords,
      latestWaypoint: waypoint,
      originFacilityId: json['origin_facility_id']?.toString(),
      destinationFacilityId: json['destination_facility_id']?.toString(),
      originFacility: oFac,
      destinationFacility: dFac,
    );
  }

  bool get isAlert => riskIndex > 50.0;
  bool get isInTransit => status.toLowerCase() == 'in_transit';
  bool get isDelivered => status.toLowerCase() == 'delivered';

  /// Whether valid GPS coordinates are available for this shipment
  bool get hasGps =>
      currentCoordinates != null &&
      currentCoordinates!['latitude'] != null &&
      currentCoordinates!['longitude'] != null;

  double? get latitude => currentCoordinates?['latitude'];
  double? get longitude => currentCoordinates?['longitude'];

  String get formattedGps => hasGps
      ? '${latitude!.toStringAsFixed(4)}°N, ${longitude!.toStringAsFixed(4)}°E'
      : 'Location Unavailable';
}

