class ShipmentRiskInfo {
  final String shipmentId;
  final double currentRisk;
  final double predictedArrivalRisk;
  final bool alert;
  final int telemetryPointsEvaluated;
  final double avgTemperatureC;
  final int excursionEvents;

  ShipmentRiskInfo({
    required this.shipmentId,
    required this.currentRisk,
    required this.predictedArrivalRisk,
    required this.alert,
    required this.telemetryPointsEvaluated,
    required this.avgTemperatureC,
    required this.excursionEvents,
  });

  factory ShipmentRiskInfo.fromJson(Map<String, dynamic> json) {
    return ShipmentRiskInfo(
      shipmentId: json['shipment_id']?.toString() ?? '',
      currentRisk: (json['current_risk'] as num?)?.toDouble() ?? 0.0,
      predictedArrivalRisk:
          (json['predicted_arrival_risk'] as num?)?.toDouble() ?? 0.0,
      alert: json['alert'] == true,
      telemetryPointsEvaluated:
          (json['telemetry_points_evaluated'] as num?)?.toInt() ?? 0,
      avgTemperatureC: (json['avg_temperature_c'] as num?)?.toDouble() ?? 0.0,
      excursionEvents: (json['excursion_events'] as num?)?.toInt() ?? 0,
    );
  }
}
