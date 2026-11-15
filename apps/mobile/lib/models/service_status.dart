class DatabaseStatus {
  final bool enabled;
  final bool? connected;
  final String message;

  DatabaseStatus({
    required this.enabled,
    this.connected,
    required this.message,
  });

  factory DatabaseStatus.fromJson(Map<String, dynamic> json) {
    return DatabaseStatus(
      enabled: json['enabled'] == true,
      connected: json['connected'] is bool ? json['connected'] as bool : null,
      message: json['message']?.toString() ?? '',
    );
  }
}

class ServiceStatus {
  final String status;
  final String service;
  final String version;
  final String targetCrop;
  final bool cnnReady;
  final String device;
  final DatabaseStatus? database;

  ServiceStatus({
    required this.status,
    required this.service,
    required this.version,
    required this.targetCrop,
    required this.cnnReady,
    required this.device,
    this.database,
  });

  factory ServiceStatus.fromJson(Map<String, dynamic> json) {
    return ServiceStatus(
      status: json['status']?.toString() ?? 'unknown',
      service: json['service']?.toString() ?? 'AgriChain AI Backend',
      version: json['version']?.toString() ?? '1.0.0',
      targetCrop: json['target_crop']?.toString() ?? 'guava',
      cnnReady: json['cnn_ready'] == true || json['model_available'] == true,
      device: json['device']?.toString() ?? 'unknown',
      database: json['database'] is Map<String, dynamic>
          ? DatabaseStatus.fromJson(json['database'] as Map<String, dynamic>)
          : null,
    );
  }
}
