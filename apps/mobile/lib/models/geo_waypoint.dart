// AgriChain AI — Geospatial Waypoint Model (PostGIS SRID 4326)
// Represents timestamped GPS telemetry and corridor tracking coordinates.

class GeoWaypoint {
  final String id;
  final String shipmentId;
  final double latitude;
  final double longitude;
  final double? altitudeM;
  final double? speedKmh;
  final double? headingDeg;
  final Map<String, dynamic> locationMetadata;
  final String recordedAt;

  GeoWaypoint({
    required this.id,
    required this.shipmentId,
    required this.latitude,
    required this.longitude,
    this.altitudeM,
    this.speedKmh,
    this.headingDeg,
    this.locationMetadata = const {},
    required this.recordedAt,
  });

  factory GeoWaypoint.fromJson(Map<String, dynamic> json) {
    return GeoWaypoint(
      id: json['id']?.toString() ?? '',
      shipmentId: json['shipment_id']?.toString() ?? '',
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0.0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0.0,
      altitudeM: (json['altitude_m'] as num?)?.toDouble(),
      speedKmh: (json['speed_kmh'] as num?)?.toDouble(),
      headingDeg: (json['heading_deg'] as num?)?.toDouble(),
      locationMetadata: json['location_metadata'] is Map<String, dynamic>
          ? Map<String, dynamic>.from(json['location_metadata'] as Map)
          : {},
      recordedAt: json['recorded_at']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'shipment_id': shipmentId,
        'latitude': latitude,
        'longitude': longitude,
        'altitude_m': altitudeM,
        'speed_kmh': speedKmh,
        'heading_deg': headingDeg,
        'location_metadata': locationMetadata,
        'recorded_at': recordedAt,
      };

  String get formattedCoordinates =>
      '${latitude.toStringAsFixed(4)}°N, ${longitude.toStringAsFixed(4)}°E';
}
