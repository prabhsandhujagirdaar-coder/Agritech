import 'dart:async';
import 'package:flutter/material.dart';

import '../config/app_config.dart';
import '../models/facility.dart';
import '../models/service_status.dart';
import '../models/shipment.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../widgets/error_view.dart';
import '../widgets/scientific_disclaimer_card.dart';
import '../widgets/status_chip.dart';
import 'facility_directory_screen.dart';
import 'guava_inspection_screen.dart';
import 'shipment_detail_screen.dart';
import 'shipment_list_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService _apiService = ApiService();
  final WebSocketService _wsService = WebSocketService();

  bool _isLoading = true;
  String? _errorMessage;
  bool _isNetworkError = false;
  bool _isServiceUnavailable = false;

  ServiceStatus? _serviceStatus;
  List<Shipment> _recentShipments = [];
  List<Facility> _facilities = [];

  StreamSubscription<WebSocketEvent>? _wsSubscription;

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
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

      if (event.event == 'shipment_created') {
        try {
          final shp = Shipment.fromJson(event.data);
          setState(() {
            _recentShipments.insert(0, shp);
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('New Shipment Created: ${shp.id} (${shp.origin} → ${shp.destination})'),
              backgroundColor: const Color(0xFF1B5E20),
              duration: const Duration(seconds: 3),
            ),
          );
        } catch (_) {}
      } else if (event.event == 'shipment_update') {
        try {
          final updated = Shipment.fromJson(event.data);
          setState(() {
            final idx = _recentShipments.indexWhere((s) => s.id == updated.id);
            if (idx != -1) {
              _recentShipments[idx] = updated;
            }
          });
        } catch (_) {}
      }
    });
  }

  Future<void> _loadDashboardData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _isNetworkError = false;
      _isServiceUnavailable = false;
    });

    try {
      final results = await Future.wait([
        _apiService.getHealth(),
        _apiService.getShipments(),
        _apiService.getFacilities(),
      ]);

      if (!mounted) return;

      setState(() {
        _serviceStatus = results[0] as ServiceStatus;
        _recentShipments = results[1] as List<Shipment>;
        _facilities = results[2] as List<Facility>;
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
        _errorMessage = 'Unexpected dashboard error: $e';
      });
    }
  }

  void _showHostConfigDialog() {
    final controller = TextEditingController(text: AppConfig.activeBaseUrl.value);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Backend API Address'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Select network target:',
              style: TextStyle(fontSize: 13, color: Colors.black87),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'Base URL',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                ActionChip(
                  label: const Text('Emulator (10.0.2.2:8000)'),
                  onPressed: () {
                    controller.text = 'http://10.0.2.2:8000/api/v1';
                  },
                ),
                ActionChip(
                  label: const Text('Localhost (127.0.0.1:8000)'),
                  onPressed: () {
                    controller.text = 'http://127.0.0.1:8000/api/v1';
                  },
                ),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              final newUrl = controller.text.trim();
              if (newUrl.isNotEmpty) {
                AppConfig.activeBaseUrl.value = newUrl;
                Navigator.pop(ctx);
                _loadDashboardData();
              }
            },
            child: const Text('Apply'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.eco_rounded, color: Colors.white, size: 22),
            SizedBox(width: 8),
            Text(
              'AgriChain AI',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 19),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF1B5E20),
        foregroundColor: Colors.white,
        actions: [
          _buildLiveStatusBadge(),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: 'Configure Backend URL',
            onPressed: _showHostConfigDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _loadDashboardData,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildLiveStatusBadge() {
    return ValueListenableBuilder<WebSocketStatus>(
      valueListenable: _wsService.status,
      builder: (context, status, _) {
        Color badgeColor;
        String label;
        IconData icon;

        switch (status) {
          case WebSocketStatus.connected:
            badgeColor = const Color(0xFF4ADE80);
            label = 'LIVE';
            icon = Icons.bolt;
            break;
          case WebSocketStatus.connecting:
          case WebSocketStatus.reconnecting:
            badgeColor = Colors.amberAccent;
            label = 'SYNC';
            icon = Icons.sync;
            break;
          case WebSocketStatus.disconnected:
            badgeColor = Colors.white54;
            label = 'REST';
            icon = Icons.cloud_off;
            break;
        }

        return InkWell(
          onTap: () {
            if (status == WebSocketStatus.disconnected) {
              _wsService.connect();
            }
          },
          borderRadius: BorderRadius.circular(12),
          child: Container(
            margin: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: badgeColor.withValues(alpha: 0.8), width: 1),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 12, color: badgeColor),
                const SizedBox(width: 4),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: badgeColor,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
          ),
        );
      },
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
              'Connecting to AgriChain AI Backend...',
              style: TextStyle(color: Color(0xFF475569), fontSize: 14),
            ),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return ErrorView(
        title: _isServiceUnavailable
            ? 'Service Unavailable (503)'
            : (_isNetworkError ? 'Network Connection Error' : 'Connection Failed'),
        message: _errorMessage!,
        isNetworkError: _isNetworkError,
        isServiceUnavailable: _isServiceUnavailable,
        onRetry: _loadDashboardData,
      );
    }

    final totalShipments = _recentShipments.length;
    final inTransitCount = _recentShipments.where((s) => s.isInTransit).length;
    final alertCount = _recentShipments.where((s) => s.isAlert).length;
    final facilityCount = _facilities.length;

    return RefreshIndicator(
      onRefresh: _loadDashboardData,
      color: const Color(0xFF1B5E20),
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // Service Status Card
          _buildServiceStatusCard(),
          const SizedBox(height: 16),

          // Overview Metrics Row
          Row(
            children: [
              Expanded(
                child: _buildMetricTile(
                  title: 'Total Shipments',
                  value: '$totalShipments',
                  icon: Icons.inventory_2_outlined,
                  color: Colors.blue.shade700,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildMetricTile(
                  title: 'In Transit',
                  value: '$inTransitCount',
                  icon: Icons.local_shipping_outlined,
                  color: Colors.green.shade700,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildMetricTile(
                  title: 'Risk Alerts',
                  value: '$alertCount',
                  icon: Icons.warning_amber_rounded,
                  color: alertCount > 0 ? Colors.red.shade700 : Colors.grey.shade600,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: InkWell(
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const FacilityDirectoryScreen()),
                    );
                  },
                  borderRadius: BorderRadius.circular(10),
                  child: _buildMetricTile(
                    title: 'Facilities',
                    value: '$facilityCount',
                    icon: Icons.store_mall_directory_outlined,
                    color: Colors.purple.shade700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Quick Action 1: Guava Intake & Quality Assessment
          Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            color: const Color(0xFF1B5E20),
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const GuavaInspectionScreen()),
                );
              },
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.2),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.camera_alt, color: Colors.white, size: 28),
                    ),
                    const SizedBox(width: 16),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Guava Maturity Inspection',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(height: 4),
                          Text(
                            'Image upload • Green / Mature Green / Ripe CNN classifier',
                            style: TextStyle(
                              color: Colors.white70,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right, color: Colors.white),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 10),

          // Quick Action 2: Storage Facility Directory
          Card(
            elevation: 1.5,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            color: Colors.white,
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const FacilityDirectoryScreen()),
                );
              },
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.purple.shade50,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(Icons.warehouse, color: Colors.purple.shade700, size: 28),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Godown & Cold-Storage Directory',
                            style: TextStyle(
                              color: Color(0xFF1E293B),
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '$facilityCount storage terminals in Punjab & Northern corridor',
                            style: const TextStyle(
                              color: Color(0xFF64748B),
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right, color: Color(0xFF94A3B8)),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Recent Shipments Section Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Recent Shipments',
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              TextButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const ShipmentListScreen()),
                  );
                },
                child: const Text('View All'),
              ),
            ],
          ),
          const SizedBox(height: 8),

          if (_recentShipments.isEmpty)
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: const Center(
                child: Text(
                  'No shipments recorded yet in ledger.',
                  style: TextStyle(color: Color(0xFF64748B)),
                ),
              ),
            )
          else
            ..._recentShipments.take(3).map(_buildShipmentCard),

          const SizedBox(height: 20),
          const ScientificDisclaimerCard(),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildServiceStatusCard() {
    final status = _serviceStatus;
    if (status == null) return const SizedBox.shrink();

    final isHealthy = status.status.toLowerCase() == 'healthy';
    final dbConnected = status.database?.connected ?? false;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isHealthy ? const Color(0xFFBBF7D0) : const Color(0xFFFED7AA),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isHealthy ? Icons.check_circle_rounded : Icons.info_outline,
                color: isHealthy ? const Color(0xFF16A34A) : Colors.amber.shade800,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Backend Service: ${status.status.toUpperCase()}',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                    color: isHealthy ? const Color(0xFF16A34A) : Colors.amber.shade900,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'v${status.version}',
                  style: const TextStyle(fontSize: 11, color: Color(0xFF475569)),
                ),
              ),
            ],
          ),
          const Divider(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildStatusItem(
                label: 'Target Crop',
                value: status.targetCrop.toUpperCase(),
                icon: Icons.agriculture,
              ),
              _buildStatusItem(
                label: 'CNN Model',
                value: status.cnnReady ? 'Ready (${status.device})' : 'Offline',
                icon: Icons.psychology,
                highlight: status.cnnReady,
              ),
              _buildStatusItem(
                label: 'Database',
                value: status.database?.enabled == true
                    ? (dbConnected ? 'PostGIS Online' : 'Fallback File')
                    : 'File Ledger',
                icon: Icons.storage,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatusItem({
    required String label,
    required String value,
    required IconData icon,
    bool highlight = false,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: const Color(0xFF64748B)),
            const SizedBox(width: 4),
            Text(
              label,
              style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: highlight ? const Color(0xFF16A34A) : const Color(0xFF1E293B),
          ),
        ),
      ],
    );
  }

  Widget _buildMetricTile({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            title,
            style: const TextStyle(fontSize: 10, color: Color(0xFF64748B)),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildShipmentCard(Shipment shipment) {
    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: CircleAvatar(
          backgroundColor: shipment.isAlert ? Colors.red.shade50 : Colors.green.shade50,
          child: Icon(
            shipment.isAlert ? Icons.warning_amber_rounded : Icons.local_shipping,
            color: shipment.isAlert ? Colors.red.shade700 : Colors.green.shade700,
            size: 20,
          ),
        ),
        title: Row(
          children: [
            Text(
              shipment.id,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const SizedBox(width: 8),
            StatusChip(status: shipment.status),
            const Spacer(),
            if (shipment.hasGps)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.satellite_alt, size: 10, color: Colors.blue.shade700),
                    const SizedBox(width: 3),
                    Text(
                      'GPS',
                      style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.blue.shade700),
                    ),
                  ],
                ),
              ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text(
              '${shipment.origin} → ${shipment.destination}',
              style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
            ),
            const SizedBox(height: 2),
            Text(
              '${shipment.produceType} • ${shipment.quantity.toStringAsFixed(0)} kg • Risk: ${shipment.riskIndex.toStringAsFixed(1)}%',
              style: TextStyle(
                fontSize: 11,
                color: shipment.isAlert ? Colors.red.shade700 : Colors.grey.shade600,
                fontWeight: shipment.isAlert ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ],
        ),
        trailing: const Icon(Icons.chevron_right, size: 18),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => ShipmentDetailScreen(shipmentId: shipment.id),
            ),
          );
        },
      ),
    );
  }
}
