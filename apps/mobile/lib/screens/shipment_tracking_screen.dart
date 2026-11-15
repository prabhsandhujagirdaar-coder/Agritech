import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../models/geo_waypoint.dart';
import '../models/risk_info.dart';
import '../models/shipment.dart';
import '../models/telemetry.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../widgets/empty_view.dart';
import '../widgets/error_view.dart';
import '../widgets/interactive_route_map.dart';
import '../widgets/status_chip.dart';

/// Live Shipment Tracking & Corridor Radar Screen for AgriChain AI.
/// Provides real-time geospatial tracking, cold-chain telemetry HUD,
/// PostGIS waypoint sequence visualization, and an opt-in demo simulation mode.
class ShipmentTrackingScreen extends StatefulWidget {
  final String shipmentId;
  final Shipment? initialShipment;
  final ApiService? apiService;

  const ShipmentTrackingScreen({
    super.key,
    required this.shipmentId,
    this.initialShipment,
    this.apiService,
  });

  @override
  State<ShipmentTrackingScreen> createState() => _ShipmentTrackingScreenState();
}

class _ShipmentTrackingScreenState extends State<ShipmentTrackingScreen> {
  late final ApiService _apiService;
  final WebSocketService _wsService = WebSocketService();

  bool _isLoading = true;
  String? _errorMessage;
  bool _isNetworkError = false;
  bool _isServiceUnavailable = false;

  Shipment? _shipment;
  ShipmentRiskInfo? _riskInfo;
  List<GeoWaypoint> _waypoints = [];
  List<TelemetryRecord> _telemetryList = [];

  // Live WebSocket state
  StreamSubscription<WebSocketEvent>? _wsSubscription;
  WebSocketStatus _currentWsStatus = WebSocketStatus.disconnected;

  // Opt-in Demo / Simulation state
  bool _isDemoMode = false;
  bool _isAutoSimulating = false;
  Timer? _simulationTimer;
  int _simulationStepCounter = 0;

  // Real-time animated coordinates
  double? _liveLat;
  double? _liveLon;
  double? _liveSpeed;
  double? _liveHeading;
  String? _lastFixTimestamp;

  @override
  void initState() {
    super.initState();
    _apiService = widget.apiService ?? ApiService();
    if (widget.initialShipment != null) {
      _shipment = widget.initialShipment;
      _liveLat = widget.initialShipment!.latitude;
      _liveLon = widget.initialShipment!.longitude;
      _isLoading = false;
    }
    _loadInitialSnapshot();
    _subscribeToLiveGateway();
  }

  @override
  void dispose() {
    _wsSubscription?.cancel();
    _simulationTimer?.cancel();
    _wsService.status.removeListener(_onWsStatusChanged);
    super.dispose();
  }

  void _onWsStatusChanged() {
    if (!mounted) return;
    setState(() {
      _currentWsStatus = _wsService.status.value;
    });
  }

  void _subscribeToLiveGateway() {
    _currentWsStatus = _wsService.status.value;
    _wsService.status.addListener(_onWsStatusChanged);

    _wsSubscription = _wsService.eventStream.listen((event) {
      if (!mounted) return;

      if (event.event == 'waypoint_update') {
        try {
          final wp = GeoWaypoint.fromJson(event.data);
          if (wp.shipmentId == widget.shipmentId) {
            setState(() {
              _waypoints.add(wp);
              _liveLat = wp.latitude;
              _liveLon = wp.longitude;
              _liveSpeed = wp.speedKmh ?? _liveSpeed;
              _liveHeading = wp.headingDeg ?? _liveHeading;
              _lastFixTimestamp = wp.recordedAt;
            });
          }
        } catch (_) {}
      } else if (event.event == 'location_update') {
        try {
          final data = event.data;
          if (data['shipment_id']?.toString() == widget.shipmentId) {
            setState(() {
              _liveLat = (data['latitude'] as num?)?.toDouble() ?? _liveLat;
              _liveLon = (data['longitude'] as num?)?.toDouble() ?? _liveLon;
              _liveSpeed = (data['speed_kmh'] as num?)?.toDouble() ?? _liveSpeed;
              _liveHeading = (data['heading_deg'] as num?)?.toDouble() ?? _liveHeading;
              _lastFixTimestamp = data['recorded_at']?.toString() ?? _lastFixTimestamp;
            });
          }
        } catch (_) {}
      } else if (event.event == 'telemetry_update') {
        try {
          final tel = TelemetryRecord.fromJson(event.data);
          if (tel.shipmentId == widget.shipmentId) {
            setState(() {
              _telemetryList.insert(0, tel);
              if (_shipment != null) {
                _shipment = Shipment(
                  id: _shipment!.id,
                  produceType: _shipment!.produceType,
                  origin: _shipment!.origin,
                  destination: _shipment!.destination,
                  status: _shipment!.status,
                  quantity: _shipment!.quantity,
                  quantityCrates: _shipment!.quantityCrates,
                  temperatureC: tel.temperature,
                  humidityPct: tel.humidity,
                  riskIndex: _shipment!.riskIndex,
                  createdAt: _shipment!.createdAt,
                  lastUpdate: tel.timestamp,
                  currentCoordinates: _shipment!.currentCoordinates,
                  latestWaypoint: _shipment!.latestWaypoint,
                  originFacilityId: _shipment!.originFacilityId,
                  destinationFacilityId: _shipment!.destinationFacilityId,
                  originFacility: _shipment!.originFacility,
                  destinationFacility: _shipment!.destinationFacility,
                );
              }
            });
          }
        } catch (_) {}
      } else if (event.event == 'risk_update') {
        try {
          final data = event.data;
          if (data['shipment_id']?.toString() == widget.shipmentId) {
            setState(() {
              _riskInfo = ShipmentRiskInfo(
                shipmentId: widget.shipmentId,
                currentRisk: (data['current_risk'] as num?)?.toDouble() ?? 0.0,
                predictedArrivalRisk: (data['predicted_arrival_risk'] as num?)?.toDouble() ?? 0.0,
                alert: data['alert'] == true,
                telemetryPointsEvaluated: (data['telemetry_points_evaluated'] as num?)?.toInt() ?? 0,
                avgTemperatureC: (data['avg_temperature_c'] as num?)?.toDouble() ?? 6.5,
                excursionEvents: (data['excursion_events'] as num?)?.toInt() ?? 0,
              );
            });
          }
        } catch (_) {}
      } else if (event.event == 'shipment_update') {
        try {
          final updated = Shipment.fromJson(event.data);
          if (updated.id == widget.shipmentId) {
            setState(() {
              _shipment = updated;
            });
          }
        } catch (_) {}
      }
    });
  }

  Future<void> _loadInitialSnapshot() async {
    if (_shipment == null) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
        _isNetworkError = false;
        _isServiceUnavailable = false;
      });
    }

    try {
      final results = await Future.wait([
        _apiService.getShipment(widget.shipmentId),
        _apiService.getShipmentRisk(widget.shipmentId),
        _apiService.getShipmentWaypoints(widget.shipmentId),
        _apiService.getShipmentTelemetry(widget.shipmentId),
      ]);

      if (!mounted) return;

      final shp = results[0] as Shipment;
      final wps = results[2] as List<GeoWaypoint>;
      final latestWp = wps.isNotEmpty ? wps.last : shp.latestWaypoint;

      setState(() {
        _shipment = shp;
        _riskInfo = results[1] as ShipmentRiskInfo;
        _waypoints = wps;
        _telemetryList = results[3] as List<TelemetryRecord>;
        _liveLat = latestWp?.latitude ?? shp.latitude;
        _liveLon = latestWp?.longitude ?? shp.longitude;
        _liveSpeed = latestWp?.speedKmh;
        _liveHeading = latestWp?.headingDeg;
        _lastFixTimestamp = latestWp?.recordedAt ?? shp.lastUpdate;
        _isLoading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        if (_shipment == null) {
          _errorMessage = e.message;
          _isNetworkError = e.isNetworkError;
          _isServiceUnavailable = e.isServiceUnavailable;
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        if (_shipment == null) {
          _errorMessage = 'Error loading tracking snapshot: $e';
        }
      });
    }
  }

  /// Calculates straight-line corridor distance to destination in kilometers
  double? _calculateRemainingDistanceKm() {
    if (_liveLat == null || _liveLon == null) return null;

    double destLat;
    double destLon;
    if (_shipment?.destinationFacility != null) {
      destLat = _shipment!.destinationFacility!.latitude;
      destLon = _shipment!.destinationFacility!.longitude;
    } else {
      final d = _shipment?.destination.toLowerCase() ?? '';
      if (d.contains('delhi') || d.contains('azadpur')) {
        destLat = 28.7161;
        destLon = 77.1772;
      } else if (d.contains('amritsar')) {
        destLat = 31.6340;
        destLon = 74.8723;
      } else if (d.contains('ludhiana')) {
        destLat = 30.9010;
        destLon = 75.8573;
      } else if (d.contains('bathinda')) {
        destLat = 30.2110;
        destLon = 74.9455;
      } else {
        destLat = 28.7161;
        destLon = 77.1772;
      }
    }

    const double earthRadiusKm = 6371.0;
    final dLat = (destLat - _liveLat!) * math.pi / 180.0;
    final dLon = (destLon - _liveLon!) * math.pi / 180.0;
    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(_liveLat! * math.pi / 180.0) *
            math.cos(destLat * math.pi / 180.0) *
            math.sin(dLon / 2) *
            math.sin(dLon / 2);
    final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
    return earthRadiusKm * c;
  }

  // ---------------------------------------------------------------------------
  // Opt-in Demo / Simulation Handler
  // ---------------------------------------------------------------------------
  void _toggleDemoMode(bool value) {
    setState(() {
      _isDemoMode = value;
      if (!value) {
        _isAutoSimulating = false;
        _simulationTimer?.cancel();
        _simulationTimer = null;
      }
    });

    if (value) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Opt-in DEMO Mode enabled. Simulation coordinates are clearly distinguished from physical vehicle GPS.'),
          backgroundColor: Color(0xFF6B21A8), // Deep purple
          duration: Duration(seconds: 4),
        ),
      );
    }
  }

  Future<void> _advanceSimulationStep() async {
    _simulationStepCounter++;

    try {
      // 1. Attempt backend simulation step endpoint first
      final res = await _apiService.simulateShipmentStep(widget.shipmentId);
      final wpData = res['waypoint'] as Map<String, dynamic>?;
      if (wpData != null) {
        final wp = GeoWaypoint.fromJson(wpData);
        setState(() {
          _waypoints.add(wp);
          _liveLat = wp.latitude;
          _liveLon = wp.longitude;
          _liveSpeed = wp.speedKmh ?? 55.0;
          _liveHeading = wp.headingDeg ?? 85.0;
          _lastFixTimestamp = wp.recordedAt;
        });
      }
      final telData = res['telemetry'] as Map<String, dynamic>?;
      if (telData != null) {
        final tel = TelemetryRecord.fromJson(telData);
        setState(() {
          _telemetryList.insert(0, tel);
        });
      }
    } catch (_) {
      // 2. Offline simulation fallback: interpolate corridor locally
      _advanceLocalSimulationStep();
    }
  }

  void _advanceLocalSimulationStep() {
    final oLat = _shipment?.originFacility?.latitude ?? 30.1453;
    final oLon = _shipment?.originFacility?.longitude ?? 74.1994;
    final dLat = _shipment?.destinationFacility?.latitude ?? 28.7161;
    final dLon = _shipment?.destinationFacility?.longitude ?? 77.1772;

    final progress = math.min(1.0, (_simulationStepCounter * 0.12) % 1.05);
    final simLat = oLat + (dLat - oLat) * progress;
    final simLon = oLon + (dLon - oLon) * progress;

    final nowIso = DateTime.now().toUtc().toIsoformatString();
    final simWaypoint = GeoWaypoint(
      id: 'SIM-WAY-${DateTime.now().millisecondsSinceEpoch}',
      shipmentId: widget.shipmentId,
      latitude: simLat,
      longitude: simLon,
      altitudeM: 194.0,
      speedKmh: progress < 1.0 ? 58.0 : 0.0,
      headingDeg: 82.0,
      locationMetadata: {
        'source': 'demo_simulated',
        'simulated': true,
        'checkpoint': 'Corridor Fix #$_simulationStepCounter',
      },
      recordedAt: nowIso,
    );

    final simTelemetry = TelemetryRecord(
      id: 'SIM-TEL-${DateTime.now().millisecondsSinceEpoch}',
      shipmentId: widget.shipmentId,
      temperature: 6.2 + (math.Random().nextDouble() * 0.8 - 0.4),
      humidity: 87.0 + (math.Random().nextDouble() * 2.0 - 1.0),
      sensorId: 'SNS-SIM-DEMO',
      location: 'Simulated Corridor Step #$_simulationStepCounter',
      timestamp: nowIso,
    );

    setState(() {
      _waypoints.add(simWaypoint);
      _telemetryList.insert(0, simTelemetry);
      _liveLat = simLat;
      _liveLon = simLon;
      _liveSpeed = simWaypoint.speedKmh;
      _liveHeading = simWaypoint.headingDeg;
      _lastFixTimestamp = nowIso;
    });
  }

  void _toggleAutoSimulation() {
    setState(() {
      _isAutoSimulating = !_isAutoSimulating;
      if (_isAutoSimulating) {
        _simulationTimer = Timer.periodic(const Duration(seconds: 3), (_) {
          _advanceSimulationStep();
        });
      } else {
        _simulationTimer?.cancel();
        _simulationTimer = null;
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Build Methods
  // ---------------------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Live Tracking: ${widget.shipmentId}',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const Text(
              'Guava Supply Chain Corridor Radar',
              style: TextStyle(fontSize: 11, color: Color(0xFFE2E8F0)),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF1B5E20),
        foregroundColor: Colors.white,
        actions: [
          _buildConnectionBadge(),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Reload Snapshot',
            onPressed: _loadInitialSnapshot,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildConnectionBadge() {
    Color bg;
    Color border;
    IconData icon;
    String label;

    if (_isDemoMode) {
      bg = const Color(0xFF7E22CE); // Purple
      border = const Color(0xFFD8B4FE);
      icon = Icons.science_outlined;
      label = 'DEMO';
    } else {
      switch (_currentWsStatus) {
        case WebSocketStatus.connected:
          bg = const Color(0xFF15803D); // Emerald
          border = const Color(0xFF86EFAC);
          icon = Icons.wifi;
          label = 'LIVE';
          break;
        case WebSocketStatus.reconnecting:
        case WebSocketStatus.connecting:
          bg = const Color(0xFFD97706); // Amber
          border = const Color(0xFFFDE68A);
          icon = Icons.sync;
          label = 'RECONNECTING';
          break;
        case WebSocketStatus.disconnected:
          bg = const Color(0xFF475569); // Slate
          border = const Color(0xFF94A3B8);
          icon = Icons.wifi_off;
          label = 'OFFLINE';
          break;
      }
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 11, color: Colors.white),
          const SizedBox(width: 4),
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 10,
              fontWeight: FontWeight.bold,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: Color(0xFF1B5E20)),
            SizedBox(height: 16),
            Text(
              'Connecting to supply chain tracking gateway...',
              style: TextStyle(color: Color(0xFF64748B), fontSize: 13),
            ),
          ],
        ),
      );
    }

    if (_errorMessage != null && _shipment == null) {
      return ErrorView(
        title: _isServiceUnavailable
            ? 'Tracking Gateway Unavailable'
            : (_isNetworkError ? 'Network Connection Error' : 'Could Not Load Tracking Data'),
        message: _errorMessage!,
        isNetworkError: _isNetworkError,
        isServiceUnavailable: _isServiceUnavailable,
        onRetry: _loadInitialSnapshot,
      );
    }

    final shipment = _shipment;
    if (shipment == null) {
      return const EmptyView(
        icon: Icons.search_off,
        title: 'Shipment Not Found',
        message: 'No tracking records exist for this shipment ID in the ledger.',
      );
    }

    final remainingDistKm = _calculateRemainingDistanceKm();

    return RefreshIndicator(
      onRefresh: _loadInitialSnapshot,
      color: const Color(0xFF1B5E20),
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // 1. Demo Mode Warning Banner (if active)
          if (_isDemoMode) _buildDemoWarningBanner(),

          // 2. Interactive Route Map Canvas
          InteractiveRouteMap(
            shipment: shipment,
            waypoints: _waypoints,
            isDemoMode: _isDemoMode,
            currentLat: _liveLat,
            currentLon: _liveLon,
            speedKmh: _liveSpeed,
            headingDeg: _liveHeading,
            lastUpdate: _lastFixTimestamp,
          ),
          const SizedBox(height: 14),

          // 3. Telemetry & Transit Metrics HUD (Temperature, Humidity, Speed, Distance)
          _buildMetricsHud(shipment, remainingDistKm),
          const SizedBox(height: 14),

          // 4. Cold-Chain Risk & Spoilage Alert Card
          _buildRiskSection(),
          const SizedBox(height: 14),

          // 5. Origin / Destination Route Terminals Card
          _buildRouteHeaderCard(shipment),
          const SizedBox(height: 14),

          // 6. Demo Simulation Controls (Opt-in toggle)
          _buildDemoControlsCard(),
          const SizedBox(height: 14),

          // 7. Recorded GPS Waypoint Breadcrumbs
          _buildWaypointsListCard(),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildDemoWarningBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFF3E8FF), // Light purple
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFC084FC), width: 1.5),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.warning_amber_rounded, size: 20, color: Color(0xFF7E22CE)),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'DEMO / SIMULATION MODE ACTIVE — Vehicle coordinates and sensor readings are generated for testing and demonstration. No physical vehicle transponder is connected.',
              style: TextStyle(
                color: Color(0xFF581C87),
                fontSize: 11,
                fontWeight: FontWeight.w600,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricsHud(Shipment shipment, double? remainingKm) {
    final temp = shipment.temperatureC ?? (_telemetryList.isNotEmpty ? _telemetryList.first.temperature : 6.2);
    final hum = shipment.humidityPct ?? (_telemetryList.isNotEmpty ? _telemetryList.first.humidity : 86.5);
    final speed = _liveSpeed ?? 55.0;

    final isTempSafe = temp >= 4.0 && temp <= 8.0;

    return Row(
      children: [
        // Temperature
        Expanded(
          child: _buildMetricTile(
            title: 'TEMPERATURE',
            value: '${temp.toStringAsFixed(1)}°C',
            subtext: isTempSafe ? 'Optimal (4-8°C)' : 'EXCURSION',
            icon: Icons.thermostat,
            color: isTempSafe ? const Color(0xFF16A34A) : const Color(0xFFDC2626),
            isAlert: !isTempSafe,
          ),
        ),
        const SizedBox(width: 8),

        // Humidity
        Expanded(
          child: _buildMetricTile(
            title: 'HUMIDITY',
            value: '${hum.toStringAsFixed(0)}%',
            subtext: '85-90% Target',
            icon: Icons.water_drop_outlined,
            color: const Color(0xFF0284C7),
          ),
        ),
        const SizedBox(width: 8),

        // Ground Speed
        Expanded(
          child: _buildMetricTile(
            title: 'SPEED',
            value: '${speed.toStringAsFixed(0)} km/h',
            subtext: _liveHeading != null ? '${_liveHeading!.toStringAsFixed(0)}° Bearing' : 'In Transit',
            icon: Icons.speed,
            color: const Color(0xFF475569),
          ),
        ),
        const SizedBox(width: 8),

        // Remaining Distance
        Expanded(
          child: _buildMetricTile(
            title: 'REMAINING',
            value: remainingKm != null ? '${remainingKm.toStringAsFixed(0)} km' : '—',
            subtext: 'To Dest Hub',
            icon: Icons.straighten,
            color: const Color(0xFF7C3AED),
          ),
        ),
      ],
    );
  }

  Widget _buildMetricTile({
    required String title,
    required String value,
    required String subtext,
    required IconData icon,
    required Color color,
    bool isAlert = false,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
      decoration: BoxDecoration(
        color: isAlert ? const Color(0xFFFEF2F2) : Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isAlert ? const Color(0xFFFCA5A5) : const Color(0xFFE2E8F0),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 12, color: color),
              const SizedBox(width: 3),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontSize: 8,
                    fontWeight: FontWeight.bold,
                    color: color,
                    letterSpacing: 0.5,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: isAlert ? const Color(0xFFDC2626) : const Color(0xFF1E293B),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            subtext,
            style: TextStyle(
              fontSize: 9,
              color: isAlert ? const Color(0xFFDC2626) : const Color(0xFF64748B),
              fontWeight: isAlert ? FontWeight.bold : FontWeight.normal,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildRiskSection() {
    final risk = _riskInfo;
    final currentRisk = risk?.currentRisk ?? _shipment?.riskIndex ?? 15.0;
    final arrivalRisk = risk?.predictedArrivalRisk ?? (currentRisk * 1.15);
    final isAlert = risk?.alert ?? (arrivalRisk > 50.0);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isAlert ? const Color(0xFFFFF1F2) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isAlert ? const Color(0xFFFECDD3) : const Color(0xFFE2E8F0),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(
                    isAlert ? Icons.warning_rounded : Icons.shield_outlined,
                    size: 18,
                    color: isAlert ? const Color(0xFFE11D48) : const Color(0xFF15803D),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Cold-Chain Spoilage Risk (LSTM)',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: isAlert ? const Color(0xFFFFE4E6) : const Color(0xFFDCFCE7),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  isAlert ? 'HIGH RISK ALERT' : 'NORMAL RISK',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: isAlert ? const Color(0xFFBE123C) : const Color(0xFF15803D),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Current In-Transit Risk', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                    const SizedBox(height: 2),
                    Text(
                      '${currentRisk.toStringAsFixed(1)}%',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: isAlert ? const Color(0xFFE11D48) : const Color(0xFF15803D),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Predicted Arrival Risk', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                    const SizedBox(height: 2),
                    Text(
                      '${arrivalRisk.toStringAsFixed(1)}%',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: isAlert ? const Color(0xFFE11D48) : const Color(0xFF0284C7),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: (currentRisk / 100.0).clamp(0.0, 1.0),
              minHeight: 6,
              backgroundColor: const Color(0xFFE2E8F0),
              valueColor: AlwaysStoppedAnimation<Color>(
                isAlert ? const Color(0xFFE11D48) : const Color(0xFF16A34A),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRouteHeaderCard(Shipment shipment) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Produce: ${shipment.produceType} (${shipment.quantity.toStringAsFixed(0)} kg)',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF334155)),
              ),
              StatusChip(status: shipment.status),
            ],
          ),
          const Divider(height: 18),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('DEPARTURE (ORIGIN)', style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Color(0xFF64748B))),
                    const SizedBox(height: 2),
                    Text(
                      shipment.origin,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF1E293B)),
                    ),
                  ],
                ),
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 8.0),
                child: Icon(Icons.arrow_forward_rounded, size: 16, color: Color(0xFF94A3B8)),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('DESTINATION MANDI', style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Color(0xFF64748B))),
                    const SizedBox(height: 2),
                    Text(
                      shipment.destination,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF1E293B)),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (_lastFixTimestamp != null) ...[
            const SizedBox(height: 8),
            Text(
              'Last GPS telemetry update: $_lastFixTimestamp',
              style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDemoControlsCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _isDemoMode ? const Color(0xFFFAF5FF) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _isDemoMode ? const Color(0xFFD8B4FE) : const Color(0xFFE2E8F0),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.science,
                    size: 18,
                    color: _isDemoMode ? const Color(0xFF7E22CE) : const Color(0xFF64748B),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Demo / Simulation Mode',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                ],
              ),
              Switch(
                value: _isDemoMode,
                activeThumbColor: const Color(0xFF7E22CE),
                activeTrackColor: const Color(0xFFE9D5FF),
                onChanged: _toggleDemoMode,
              ),
            ],
          ),
          const Text(
            'Generates simulated movement and cold-chain sensor updates for testing and verification.',
            style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
          ),
          if (_isDemoMode) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _advanceSimulationStep,
                    icon: const Icon(Icons.skip_next, size: 16),
                    label: const Text('Next Step', style: TextStyle(fontSize: 12)),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF7E22CE),
                      side: const BorderSide(color: Color(0xFF7E22CE)),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _toggleAutoSimulation,
                    icon: Icon(_isAutoSimulating ? Icons.pause : Icons.play_arrow, size: 16),
                    label: Text(_isAutoSimulating ? 'Pause Auto' : 'Play Auto (3s)', style: const TextStyle(fontSize: 12)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _isAutoSimulating ? const Color(0xFFDC2626) : const Color(0xFF7E22CE),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildWaypointsListCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Corridor Waypoints (${_waypoints.length})',
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              const Text(
                'WGS84 SRID 4326',
                style: TextStyle(fontSize: 10, color: Color(0xFF64748B)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (_waypoints.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12.0),
              child: Center(
                child: Text(
                  'No waypoints logged yet. Enable Demo Mode or log a checkpoint fix.',
                  style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                ),
              ),
            )
          else
            ..._waypoints.reversed.take(5).map((wp) {
              final isSimulated = wp.locationMetadata['source'] == 'demo_simulated' ||
                  wp.locationMetadata['simulated'] == true;
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: isSimulated ? const Color(0xFFFAF5FF) : const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: isSimulated ? const Color(0xFFE9D5FF) : const Color(0xFFE2E8F0),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      isSimulated ? Icons.science_outlined : Icons.navigation_outlined,
                      size: 16,
                      color: isSimulated ? const Color(0xFF7E22CE) : const Color(0xFF0284C7),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                '${wp.latitude.toStringAsFixed(4)}°N, ${wp.longitude.toStringAsFixed(4)}°E',
                                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
                              ),
                              if (isSimulated) ...[
                                const SizedBox(width: 6),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFEDE9FE),
                                    borderRadius: BorderRadius.circular(3),
                                  ),
                                  child: const Text('SIMULATED', style: TextStyle(fontSize: 8, fontWeight: FontWeight.bold, color: Color(0xFF6D28D9))),
                                ),
                              ],
                            ],
                          ),
                          Text(
                            '${wp.recordedAt}${wp.speedKmh != null ? ' • ${wp.speedKmh!.toStringAsFixed(0)} km/h' : ''}',
                            style: const TextStyle(fontSize: 10, color: Color(0xFF64748B)),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }
}

extension _IsoFormat on DateTime {
  String toIsoformatString() {
    return '${year.toString().padLeft(4, '0')}-'
        '${month.toString().padLeft(2, '0')}-'
        '${day.toString().padLeft(2, '0')}T'
        '${hour.toString().padLeft(2, '0')}:'
        '${minute.toString().padLeft(2, '0')}:'
        '${second.toString().padLeft(2, '0')}Z';
  }
}
