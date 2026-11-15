import 'dart:async';
import 'package:flutter/material.dart';

import '../models/geo_waypoint.dart';
import '../models/risk_info.dart';
import '../models/shipment.dart';
import '../models/telemetry.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../widgets/empty_view.dart';
import '../widgets/error_view.dart';
import '../widgets/geospatial_route_card.dart';
import '../widgets/status_chip.dart';
import 'shipment_tracking_screen.dart';

class ShipmentDetailScreen extends StatefulWidget {
  final String shipmentId;
  final ApiService? apiService;
  final Shipment? initialShipment;

  const ShipmentDetailScreen({
    super.key,
    required this.shipmentId,
    this.apiService,
    this.initialShipment,
  });

  @override
  State<ShipmentDetailScreen> createState() => _ShipmentDetailScreenState();
}

class _ShipmentDetailScreenState extends State<ShipmentDetailScreen> {
  late final ApiService _apiService;
  final WebSocketService _wsService = WebSocketService();

  bool _isLoading = true;
  String? _errorMessage;
  bool _isNetworkError = false;
  bool _isServiceUnavailable = false;

  Shipment? _shipment;
  ShipmentRiskInfo? _riskInfo;
  List<TelemetryRecord> _telemetryList = [];
  List<GeoWaypoint> _waypointsList = [];

  StreamSubscription<WebSocketEvent>? _wsSubscription;

  @override
  void initState() {
    super.initState();
    _apiService = widget.apiService ?? ApiService();
    if (widget.initialShipment != null) {
      _shipment = widget.initialShipment;
      _isLoading = false;
    } else {
      _loadShipmentData();
    }
    _subscribeToLiveEvents();
  }

  @override
  void dispose() {
    _wsSubscription?.cancel();
    super.dispose();
  }

  void _subscribeToLiveEvents() {
    _wsSubscription = _wsService.eventStream.listen((event) {
      if (!mounted) return;

      if (event.event == 'telemetry_update') {
        try {
          final rec = TelemetryRecord.fromJson(event.data);
          if (rec.shipmentId == widget.shipmentId) {
            setState(() {
              _telemetryList.insert(0, rec);
            });
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Live Telemetry Received: ${rec.temperature.toStringAsFixed(1)}°C, ${rec.humidity.toStringAsFixed(1)}% RH'),
                duration: const Duration(seconds: 3),
                backgroundColor: const Color(0xFF1B5E20),
              ),
            );
          }
        } catch (_) {}
      } else if (event.event == 'waypoint_update') {
        try {
          final wp = GeoWaypoint.fromJson(event.data);
          if (wp.shipmentId == widget.shipmentId) {
            setState(() {
              _waypointsList.add(wp);
            });
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Live Waypoint Received: ${wp.formattedCoordinates}'),
                duration: const Duration(seconds: 3),
                backgroundColor: Colors.blue.shade800,
              ),
            );
          }
        } catch (_) {}
      } else if (event.event == 'shipment_update') {
        if (event.data['id']?.toString() == widget.shipmentId) {
          try {
            final updated = Shipment.fromJson(event.data);
            setState(() {
              _shipment = updated;
            });
          } catch (_) {}
        }
      }
    });
  }

  Future<void> _loadShipmentData() async {
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
        _apiService.getShipmentTelemetry(widget.shipmentId),
        _apiService.getShipmentWaypoints(widget.shipmentId),
      ]);

      if (!mounted) return;

      setState(() {
        _shipment = results[0] as Shipment;
        _riskInfo = results[1] as ShipmentRiskInfo;
        _telemetryList = results[2] as List<TelemetryRecord>;
        _waypointsList = results[3] as List<GeoWaypoint>;
        _isLoading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.message;
        _isNetworkError = e.isNetworkError;
        _isServiceUnavailable = e.isServiceUnavailable;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to load shipment details: $e';
      });
    }
  }

  void _showAddTelemetryModal() {
    final tempController = TextEditingController(text: '6.5');
    final humController = TextEditingController(text: '85.0');
    final locController = TextEditingController(text: 'Punjab Highway Transit');
    final sensorController = TextEditingController(text: 'SNS-MOBILE-01');
    bool isSubmitting = false;
    String? modalError;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) => Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom + 20,
            left: 20,
            right: 20,
            top: 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Record Telemetry Reading',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (modalError != null) ...[
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    modalError!,
                    style: TextStyle(color: Colors.red.shade800, fontSize: 12),
                  ),
                ),
                const SizedBox(height: 12),
              ],
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: tempController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Temperature (°C)',
                        hintText: '4.0 - 8.0 optimal',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: humController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Humidity (%)',
                        hintText: '80.0 - 90.0',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: locController,
                decoration: const InputDecoration(
                  labelText: 'Checkpoint / Location',
                  hintText: 'e.g. Malout Corridor Toll',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: sensorController,
                decoration: const InputDecoration(
                  labelText: 'Sensor ID',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: isSubmitting
                      ? null
                      : () async {
                          final temp = double.tryParse(tempController.text.trim());
                          final hum = double.tryParse(humController.text.trim());

                          if (temp == null || hum == null) {
                            setModalState(() {
                              modalError = 'Please enter valid numerical values.';
                            });
                            return;
                          }

                          setModalState(() {
                            isSubmitting = true;
                            modalError = null;
                          });

                          try {
                            await _apiService.addTelemetryReading(
                              shipmentId: widget.shipmentId,
                              temperature: temp,
                              humidity: hum,
                              location: locController.text.trim(),
                              sensorId: sensorController.text.trim(),
                            );
                            if (ctx.mounted) {
                              Navigator.pop(ctx);
                            }
                            if (mounted) {
                              _loadShipmentData();
                            }
                          } catch (e) {
                            setModalState(() {
                              isSubmitting = false;
                              modalError = 'Failed to submit telemetry: $e';
                            });
                          }
                        },
                  icon: isSubmitting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.send),
                  label: Text(isSubmitting ? 'Transmitting...' : 'Record to Cold Chain'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF1B5E20),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 13),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showAddWaypointModal() {
    final latController = TextEditingController(text: '30.3165');
    final lonController = TextEditingController(text: '74.5218');
    final speedController = TextEditingController(text: '55.0');
    final headingController = TextEditingController(text: '92.0');
    final noteController = TextEditingController(text: 'NH-7 Corridor Transit');
    bool isSubmitting = false;
    String? modalError;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) => Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom + 20,
            left: 20,
            right: 20,
            top: 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Record GPS Waypoint Fix',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (modalError != null) ...[
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    modalError!,
                    style: TextStyle(color: Colors.red.shade800, fontSize: 12),
                  ),
                ),
                const SizedBox(height: 12),
              ],
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: latController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Latitude (°N)',
                        hintText: '8.0 – 37.5',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: lonController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Longitude (°E)',
                        hintText: '68.0 – 97.5',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: speedController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Speed (km/h)',
                        hintText: '0 - 120',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: headingController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Heading (0-360°)',
                        hintText: 'e.g. 90',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: noteController,
                decoration: const InputDecoration(
                  labelText: 'Checkpoint Note / Corridor Landmark',
                  hintText: 'e.g. Muktsar bypass toll plaza',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: isSubmitting
                      ? null
                      : () async {
                          final lat = double.tryParse(latController.text.trim());
                          final lon = double.tryParse(lonController.text.trim());
                          final speed = double.tryParse(speedController.text.trim());
                          final heading = double.tryParse(headingController.text.trim());

                          if (lat == null || lon == null) {
                            setModalState(() {
                              modalError = 'Please enter valid numerical coordinates.';
                            });
                            return;
                          }

                          if (lat < 8.0 || lat > 37.5 || lon < 68.0 || lon > 97.5) {
                            setModalState(() {
                              modalError = 'Coordinates must fall within Indian geographical bounds (8°N–37.5°N, 68°E–97.5°E).';
                            });
                            return;
                          }

                          setModalState(() {
                            isSubmitting = true;
                            modalError = null;
                          });

                          try {
                            await _apiService.addShipmentWaypoint(
                              widget.shipmentId,
                              latitude: lat,
                              longitude: lon,
                              speedKmh: speed,
                              headingDeg: heading,
                              locationMetadata: {
                                'note': noteController.text.trim(),
                                'source': 'mobile_app_manual_fix',
                              },
                            );
                            if (ctx.mounted) {
                              Navigator.pop(ctx);
                            }
                            if (mounted) {
                              _loadShipmentData();
                            }
                          } catch (e) {
                            setModalState(() {
                              isSubmitting = false;
                              modalError = 'Failed to submit waypoint: $e';
                            });
                          }
                        },
                  icon: isSubmitting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.add_location),
                  label: Text(isSubmitting ? 'Recording Waypoint...' : 'Commit PostGIS Waypoint'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue.shade800,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 13),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.shipmentId),
        backgroundColor: const Color(0xFF1B5E20),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            key: const Key('appbar_live_tracking_button'),
            icon: const Icon(Icons.radar),
            tooltip: 'Open Live Tracking',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ShipmentTrackingScreen(
                    shipmentId: widget.shipmentId,
                    initialShipment: _shipment,
                  ),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Reload',
            onPressed: _loadShipmentData,
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _showAddWaypointModal,
                  icon: const Icon(Icons.add_location_alt, size: 18),
                  label: const Text('Add GPS Fix'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.blue.shade800,
                    side: BorderSide(color: Colors.blue.shade700),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _showAddTelemetryModal,
                  icon: const Icon(Icons.add_chart, size: 18),
                  label: const Text('Add Telemetry'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF1B5E20),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFF1B5E20)),
      );
    }

    if (_errorMessage != null) {
      return ErrorView(
        title: _isServiceUnavailable
            ? 'Service Unavailable'
            : (_isNetworkError ? 'Network Connection Error' : 'Could Not Load Details'),
        message: _errorMessage!,
        isNetworkError: _isNetworkError,
        isServiceUnavailable: _isServiceUnavailable,
        onRetry: _loadShipmentData,
      );
    }

    final shipment = _shipment;
    if (shipment == null) {
      return const Center(child: Text('Shipment not found.'));
    }

    return RefreshIndicator(
      onRefresh: _loadShipmentData,
      color: const Color(0xFF1B5E20),
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // Shipment Metadata Card
          _buildMetadataCard(shipment),
          const SizedBox(height: 14),

          // Prominent "Open Live Tracking" Action Button near the top
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              key: const Key('open_live_tracking_button'),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => ShipmentTrackingScreen(
                      shipmentId: widget.shipmentId,
                      initialShipment: shipment,
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.radar, size: 20),
              label: const Text(
                'Open Live Tracking',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.3,
                ),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF1B5E20),
                foregroundColor: Colors.white,
                elevation: 2,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Linked Storage Facilities (Origin & Destination)
          _buildFacilitiesRow(shipment),
          const SizedBox(height: 16),

          // Geospatial Route Corridor Card
          GeospatialRouteCard(
            shipment: shipment,
            waypoints: _waypointsList,
            onAddWaypoint: _showAddWaypointModal,
          ),
          const SizedBox(height: 10),

          // Secondary Live Tracking Radar Action below route card
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              key: const Key('secondary_live_tracking_button'),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => ShipmentTrackingScreen(
                      shipmentId: widget.shipmentId,
                      initialShipment: shipment,
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.radar, size: 18),
              label: const Text(
                'Open Live Tracking Radar',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF1B5E20),
                side: const BorderSide(color: Color(0xFF1B5E20), width: 1.5),
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Cold-Chain Risk Card
          if (_riskInfo != null) _buildRiskCard(_riskInfo!),
          const SizedBox(height: 20),

          // Telemetry Sequence Section
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Telemetry Readings',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              Text(
                '${_telemetryList.length} logs recorded',
                style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
              ),
            ],
          ),
          const SizedBox(height: 8),

          if (_telemetryList.isEmpty)
            const EmptyView(
              icon: Icons.thermostat_outlined,
              title: 'No Telemetry Recorded',
              message: 'No sensor logs recorded for this shipment yet. Tap "Add Telemetry" below to record a temperature checkpoint.',
            )
          else
            ..._telemetryList.map(_buildTelemetryCard),

          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildMetadataCard(Shipment shipment) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                shipment.id,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              StatusChip(status: shipment.status),
            ],
          ),
          const Divider(height: 20),
          _buildMetaRow(Icons.agriculture, 'Produce', '${shipment.produceType} (${shipment.quantity.toStringAsFixed(0)} kg / ${shipment.quantityCrates} crates)'),
          const SizedBox(height: 6),
          _buildMetaRow(Icons.location_on_outlined, 'Route', '${shipment.origin} → ${shipment.destination}'),
          const SizedBox(height: 6),
          _buildMetaRow(Icons.calendar_today_outlined, 'Created', shipment.createdAt),
          const SizedBox(height: 6),
          _buildMetaRow(Icons.update_outlined, 'Last Update', shipment.lastUpdate),
        ],
      ),
    );
  }

  Widget _buildFacilitiesRow(Shipment shipment) {
    final oFac = shipment.originFacility;
    final dFac = shipment.destinationFacility;

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
          const Text(
            'Terminal Facilities',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: Color(0xFF334155),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'ORIGIN FACILITY',
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B)),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        oFac != null ? oFac.name : shipment.origin,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (oFac != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          '${oFac.formattedType} • ${oFac.district}',
                          style: const TextStyle(fontSize: 11, color: Color(0xFF475569)),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 8.0),
                child: Icon(Icons.arrow_forward, size: 16, color: Color(0xFF94A3B8)),
              ),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'DESTINATION HUB',
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B)),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        dFac != null ? dFac.name : shipment.destination,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (dFac != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          '${dFac.formattedType} • ${dFac.district}',
                          style: const TextStyle(fontSize: 11, color: Color(0xFF475569)),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetaRow(IconData icon, String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: const Color(0xFF64748B)),
        const SizedBox(width: 8),
        Text(
          '$label: ',
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: Color(0xFF475569),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontSize: 12, color: Color(0xFF1E293B)),
          ),
        ),
      ],
    );
  }

  Widget _buildRiskCard(ShipmentRiskInfo risk) {
    final isAlert = risk.alert;
    final riskColor = isAlert ? Colors.red.shade700 : const Color(0xFF1B5E20);
    final bgColor = isAlert ? const Color(0xFFFEF2F2) : const Color(0xFFF0FDF4);
    final borderColor = isAlert ? const Color(0xFFFECACA) : const Color(0xFFBBF7D0);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isAlert ? Icons.warning_rounded : Icons.verified_user_rounded,
                color: riskColor,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  isAlert ? 'Cold-Chain Excursion Alert' : 'Cold-Chain Stable',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: riskColor,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: isAlert ? Colors.red.shade100 : Colors.green.shade100,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  isAlert ? 'HIGH RISK' : 'NORMAL',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: riskColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildRiskMetric('Current Risk', '${risk.currentRisk.toStringAsFixed(1)}%'),
              _buildRiskMetric('Arrival Risk', '${risk.predictedArrivalRisk.toStringAsFixed(1)}%'),
              _buildRiskMetric('Avg Temp', '${risk.avgTemperatureC.toStringAsFixed(1)}°C'),
              _buildRiskMetric('Excursions', '${risk.excursionEvents}'),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            risk.telemetryPointsEvaluated == 0
                ? 'Notice: Zero historical telemetry points evaluated. Showing baseline estimate.'
                : 'Evaluated ${risk.telemetryPointsEvaluated} cold-chain sensor readings. Target: 4.0°C – 8.0°C.',
            style: const TextStyle(fontSize: 11, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
          ),
        ],
      ),
    );
  }

  Widget _buildRiskMetric(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1E293B),
          ),
        ),
      ],
    );
  }

  Widget _buildTelemetryCard(TelemetryRecord record) {
    final isExcursion = record.isThermalExcursion;

    return Card(
      elevation: 0.5,
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(
          color: isExcursion ? Colors.red.shade200 : const Color(0xFFE2E8F0),
        ),
      ),
      color: isExcursion ? const Color(0xFFFFF7ED) : Colors.white,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: isExcursion ? Colors.red.shade100 : Colors.green.shade50,
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.thermostat,
                size: 20,
                color: isExcursion ? Colors.red.shade800 : Colors.green.shade700,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        '${record.temperature.toStringAsFixed(1)}°C',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: isExcursion ? Colors.red.shade800 : const Color(0xFF1E293B),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '•  ${record.humidity.toStringAsFixed(1)}% RH',
                        style: const TextStyle(fontSize: 13, color: Color(0xFF475569)),
                      ),
                      if (isExcursion) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.red.shade700,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text(
                            'EXCURSION',
                            style: TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${record.location.isNotEmpty ? record.location : 'Checkpoint'} • ${record.sensorId}',
                    style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                  ),
                  Text(
                    record.timestamp,
                    style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
