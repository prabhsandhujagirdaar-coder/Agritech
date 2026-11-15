class TelemetryRecord {
  final String id;
  final String shipmentId;
  final double temperature;
  final double humidity;
  final String sensorId;
  final String location;
  final String timestamp;

  TelemetryRecord({
    required this.id,
    required this.shipmentId,
    required this.temperature,
    required this.humidity,
    required this.sensorId,
    required this.location,
    required this.timestamp,
  });

  factory TelemetryRecord.fromJson(Map<String, dynamic> json) {
    return TelemetryRecord(
      id: json['id']?.toString() ?? '',
      shipmentId: json['shipment_id']?.toString() ?? '',
      temperature: (json['temperature'] as num?)?.toDouble() ?? 0.0,
      humidity: (json['humidity'] as num?)?.toDouble() ?? 0.0,
      sensorId: json['sensor_id']?.toString() ?? '',
      location: json['location']?.toString() ?? '',
      timestamp: json['timestamp']?.toString() ?? '',
    );
  }

  /// Cold-chain optimal window is 4.0°C to 8.0°C for Guava / citrus produce
  bool get isThermalExcursion => temperature < 4.0 || temperature > 8.0;
}
