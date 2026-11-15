import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../config/app_config.dart';
import '../models/cnn_prediction.dart';
import '../models/facility.dart';
import '../models/geo_waypoint.dart';
import '../models/risk_info.dart';
import '../models/service_status.dart';
import '../models/shipment.dart';
import '../models/telemetry.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final bool isNetworkError;
  final bool isServiceUnavailable;

  ApiException({
    required this.message,
    this.statusCode,
    this.isNetworkError = false,
    this.isServiceUnavailable = false,
  });

  @override
  String toString() => message;
}

class ApiService {
  final http.Client _client;

  ApiService({http.Client? client}) : _client = client ?? http.Client();

  String get baseUrl => AppConfig.activeBaseUrl.value;

  Uri _buildUri(String path) {
    final cleanBase = baseUrl.replaceAll(RegExp(r'/+$'), '');
    final cleanPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$cleanBase$cleanPath');
  }

  /// System health probe: checks backend liveness, active crop, CNN model readiness, and database
  Future<ServiceStatus> getHealth() async {
    final uri = _buildUri('/health');
    try {
      final response = await _client.get(uri).timeout(const Duration(seconds: 8));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ServiceStatus.fromJson(data);
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Cannot reach backend at $uri. Check connection, host address, or firewall.\nDetail: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Backend request timed out after 8 seconds.\nHost: $uri',
        isNetworkError: true,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        message: 'Network transport error: ${e.message}\nHost: $uri',
        isNetworkError: true,
      );
    }
  }

  /// List all active shipments from repository
  Future<List<Shipment>> getShipments() async {
    final uri = _buildUri('/shipments');
    try {
      final response = await _client.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((item) => Shipment.fromJson(item as Map<String, dynamic>)).toList();
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Network failure loading shipments from $uri: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Timeout loading shipments from $uri.',
        isNetworkError: true,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        message: 'Network client error: ${e.message}',
        isNetworkError: true,
      );
    }
  }

  /// Fetch a single shipment by its identifier
  Future<Shipment> getShipment(String shipmentId) async {
    final uri = _buildUri('/shipments/$shipmentId');
    try {
      final response = await _client.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return Shipment.fromJson(data);
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Failed to reach backend: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Request timed out for shipment $shipmentId',
        isNetworkError: true,
      );
    }
  }

  /// Fetch cold-chain risk scoring for a shipment
  Future<ShipmentRiskInfo> getShipmentRisk(String shipmentId) async {
    final uri = _buildUri('/shipments/$shipmentId/risk');
    try {
      final response = await _client.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return ShipmentRiskInfo.fromJson(data);
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Failed to reach risk endpoint: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Request timed out loading risk for $shipmentId',
        isNetworkError: true,
      );
    }
  }

  /// Fetch timestamped sensor telemetry logs for a shipment
  Future<List<TelemetryRecord>> getShipmentTelemetry(String shipmentId, {int limit = 50}) async {
    final uri = _buildUri('/shipments/$shipmentId/telemetry?limit=$limit');
    try {
      final response = await _client.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final List<dynamic> data = json.decode(response.body);
        return data
            .map((item) => TelemetryRecord.fromJson(item as Map<String, dynamic>))
            .toList();
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Failed to fetch telemetry: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Timeout fetching telemetry for $shipmentId',
        isNetworkError: true,
      );
    }
  }

  /// Ingest a new sensor reading into the shipment's cold-chain sequence
  Future<TelemetryRecord> addTelemetryReading({
    required String shipmentId,
    required double temperature,
    required double humidity,
    String sensorId = 'SNS-MOBILE-01',
    String location = 'In-transit Mobile App',
  }) async {
    final uri = _buildUri('/shipments/$shipmentId/telemetry');
    final payload = json.encode({
      'temperature': temperature,
      'humidity': humidity,
      'sensor_id': sensorId,
      'location': location,
    });

    try {
      final response = await _client
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: payload,
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return TelemetryRecord.fromJson(data);
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Network error posting telemetry: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Timeout posting telemetry reading.',
        isNetworkError: true,
      );
    }
  }

  /// Upload Guava image for CNN maturity classification
  /// Reuses existing FastAPI POST /api/v1/cnn/predict endpoint
  Future<CNNPredictionResult> predictGuavaMaturity(
    Uint8List imageBytes,
    String filename,
  ) async {
    final uri = _buildUri('/cnn/predict');

    try {
      final request = http.MultipartRequest('POST', uri);

      // Determine content type
      MediaType mediaType = MediaType('image', 'jpeg');
      if (filename.toLowerCase().endsWith('.png')) {
        mediaType = MediaType('image', 'png');
      } else if (filename.toLowerCase().endsWith('.webp')) {
        mediaType = MediaType('image', 'webp');
      }

      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          imageBytes,
          filename: filename,
          contentType: mediaType,
        ),
      );

      final streamedResponse = await _client.send(request).timeout(const Duration(seconds: 20));
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return CNNPredictionResult.fromJson(data);
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Cannot connect to inference service at $uri: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'CNN inference timed out after 20 seconds.',
        isNetworkError: true,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        message: 'Inference client error: ${e.message}',
        isNetworkError: true,
      );
    }
  }

  /// List storage facilities & godowns with optional filtering
  Future<List<Facility>> getFacilities({
    String? facilityType,
    String? district,
    String? state,
    String? operationalStatus,
  }) async {
    final queryParams = <String, String>{};
    if (facilityType != null && facilityType.isNotEmpty) {
      queryParams['facility_type'] = facilityType;
    }
    if (district != null && district.isNotEmpty) {
      queryParams['district'] = district;
    }
    if (state != null && state.isNotEmpty) {
      queryParams['state'] = state;
    }
    if (operationalStatus != null && operationalStatus.isNotEmpty) {
      queryParams['operational_status'] = operationalStatus;
    }

    final baseUri = _buildUri('/facilities');
    final uri = queryParams.isNotEmpty
        ? baseUri.replace(queryParameters: queryParams)
        : baseUri;

    try {
      final response = await _client.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((item) => Facility.fromJson(item as Map<String, dynamic>)).toList();
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Network error connecting to facilities at $uri: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Timeout loading facilities list from $uri.',
        isNetworkError: true,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        message: 'HTTP client error: ${e.message}',
        isNetworkError: true,
      );
    }
  }

  /// Get details of a single agricultural storage facility
  Future<Facility> getFacility(String facilityId) async {
    final uri = _buildUri('/facilities/$facilityId');
    try {
      final response = await _client.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return Facility.fromJson(data);
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Network error loading facility details: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Timeout fetching facility $facilityId',
        isNetworkError: true,
      );
    }
  }

  /// Fetch geospatial waypoint track for a shipment (PostGIS SRID 4326)
  Future<List<GeoWaypoint>> getShipmentWaypoints(String shipmentId) async {
    final uri = _buildUri('/shipments/$shipmentId/waypoints');
    try {
      final response = await _client.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final List<dynamic> data = json.decode(response.body);
        return data
            .map((item) => GeoWaypoint.fromJson(item as Map<String, dynamic>))
            .toList();
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Network error fetching waypoints: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Timeout fetching waypoints for shipment $shipmentId',
        isNetworkError: true,
      );
    }
  }

  /// Ingest a new geospatial waypoint checkpoint into a shipment's route
  Future<GeoWaypoint> addShipmentWaypoint(
    String shipmentId, {
    required double latitude,
    required double longitude,
    double? altitudeM,
    double? speedKmh,
    double? headingDeg,
    Map<String, dynamic>? locationMetadata,
  }) async {
    final uri = _buildUri('/shipments/$shipmentId/waypoints');
    final payload = json.encode({
      'latitude': latitude,
      'longitude': longitude,
      'altitude_m': altitudeM,
      'speed_kmh': speedKmh,
      'heading_deg': headingDeg,
      'location_metadata': locationMetadata ?? {},
    });

    try {
      final response = await _client
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: payload,
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        return GeoWaypoint.fromJson(data);
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Network error recording waypoint: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Timeout submitting waypoint reading.',
        isNetworkError: true,
      );
    }
  }

  /// Check CNN model status & availability
  Future<Map<String, dynamic>> getCNNStatus() async {
    final uri = _buildUri('/cnn/status');
    try {
      final response = await _client.get(uri).timeout(const Duration(seconds: 8));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Cannot reach CNN status endpoint: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Timeout inspecting CNN status.',
        isNetworkError: true,
      );
    }
  }

  /// Trigger an opt-in simulated transit step on the backend for demo/testing
  Future<Map<String, dynamic>> simulateShipmentStep(String shipmentId) async {
    final uri = _buildUri('/shipments/$shipmentId/simulate-step');
    try {
      final response = await _client
          .post(uri, headers: {'Content-Type': 'application/json'})
          .timeout(const Duration(seconds: 10));
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw _handleError(response);
      }
    } on SocketException catch (e) {
      throw ApiException(
        message: 'Network error calling simulator: ${e.message}',
        isNetworkError: true,
      );
    } on TimeoutException {
      throw ApiException(
        message: 'Timeout calling simulator on $shipmentId',
        isNetworkError: true,
      );
    }
  }

  ApiException _handleError(http.Response response) {
    String detail = 'HTTP error ${response.statusCode}';
    try {
      final body = json.decode(response.body);
      if (body is Map) {
        if (body.containsKey('detail')) {
          final d = body['detail'];
          if (d is List) {
            // Pydantic validation error array
            detail = d.map((err) => err is Map ? '${err['loc']?.join('.')}: ${err['msg']}' : err.toString()).join('\n');
          } else {
            detail = d.toString();
          }
        } else if (body.containsKey('message')) {
          detail = body['message'].toString();
        }
      }
    } catch (_) {
      detail = response.body.isNotEmpty ? response.body : detail;
    }

    final isServiceUnavailable = response.statusCode == 503;

    return ApiException(
      statusCode: response.statusCode,
      message: detail,
      isServiceUnavailable: isServiceUnavailable,
    );
  }
}
