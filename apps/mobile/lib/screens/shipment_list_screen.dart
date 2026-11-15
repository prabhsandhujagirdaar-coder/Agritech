import 'dart:async';
import 'package:flutter/material.dart';

import '../models/shipment.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../widgets/empty_view.dart';
import '../widgets/error_view.dart';
import '../widgets/status_chip.dart';
import 'shipment_detail_screen.dart';
import 'shipment_tracking_screen.dart';

class ShipmentListScreen extends StatefulWidget {
  final ApiService? apiService;
  final List<Shipment>? initialShipments;

  const ShipmentListScreen({
    super.key,
    this.apiService,
    this.initialShipments,
  });

  @override
  State<ShipmentListScreen> createState() => _ShipmentListScreenState();
}

class _ShipmentListScreenState extends State<ShipmentListScreen> {
  late final ApiService _apiService;
  final WebSocketService _wsService = WebSocketService();

  bool _isLoading = true;
  String? _errorMessage;
  bool _isNetworkError = false;
  bool _isServiceUnavailable = false;

  List<Shipment> _allShipments = [];
  String _filterStatus = 'all';
  String _searchQuery = '';

  StreamSubscription<WebSocketEvent>? _wsSubscription;

  @override
  void initState() {
    super.initState();
    _apiService = widget.apiService ?? ApiService();
    if (widget.initialShipments != null) {
      _allShipments = List.from(widget.initialShipments!);
      _isLoading = false;
    } else {
      _fetchShipments();
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

      if (event.event == 'shipment_created') {
        try {
          final shp = Shipment.fromJson(event.data);
          setState(() {
            _allShipments.insert(0, shp);
          });
        } catch (_) {}
      } else if (event.event == 'shipment_update') {
        try {
          final updated = Shipment.fromJson(event.data);
          setState(() {
            final idx = _allShipments.indexWhere((s) => s.id == updated.id);
            if (idx != -1) {
              _allShipments[idx] = updated;
            }
          });
        } catch (_) {}
      }
    });
  }

  Future<void> _fetchShipments() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _isNetworkError = false;
      _isServiceUnavailable = false;
    });

    try {
      final shipments = await _apiService.getShipments();
      if (!mounted) return;
      setState(() {
        _allShipments = shipments;
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
        _errorMessage = 'Error loading shipments: $e';
      });
    }
  }

  List<Shipment> get _filteredShipments {
    return _allShipments.where((s) {
      // Status filter
      if (_filterStatus != 'all' && s.status.toLowerCase() != _filterStatus) {
        return false;
      }

      // Search filter
      if (_searchQuery.isNotEmpty) {
        final q = _searchQuery.toLowerCase();
        final matchesId = s.id.toLowerCase().contains(q);
        final matchesOrigin = s.origin.toLowerCase().contains(q);
        final matchesDest = s.destination.toLowerCase().contains(q);
        final matchesProduce = s.produceType.toLowerCase().contains(q);
        return matchesId || matchesOrigin || matchesDest || matchesProduce;
      }

      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Produce Shipments'),
        backgroundColor: const Color(0xFF1B5E20),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchShipments,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search & Filter Bar
          Container(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            color: Colors.white,
            child: Column(
              children: [
                TextField(
                  decoration: InputDecoration(
                    hintText: 'Search shipment ID, origin, mandi...',
                    prefixIcon: const Icon(Icons.search, size: 20),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
                    ),
                    filled: true,
                    fillColor: const Color(0xFFF8FAFC),
                  ),
                  onChanged: (val) {
                    setState(() {
                      _searchQuery = val.trim();
                    });
                  },
                ),
                const SizedBox(height: 8),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _buildFilterChip('All', 'all'),
                      const SizedBox(width: 8),
                      _buildFilterChip('In Transit', 'in_transit'),
                      const SizedBox(width: 8),
                      _buildFilterChip('Created', 'created'),
                      const SizedBox(width: 8),
                      _buildFilterChip('Delivered', 'delivered'),
                      const SizedBox(width: 8),
                      _buildFilterChip('Delayed', 'delayed'),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: Color(0xFFE2E8F0)),

          // Body Content
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, String value) {
    final isSelected = _filterStatus == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          setState(() {
            _filterStatus = value;
          });
        }
      },
      selectedColor: const Color(0xFFE8F5E9),
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        color: isSelected ? const Color(0xFF1B5E20) : const Color(0xFF475569),
      ),
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
            : (_isNetworkError ? 'Network Connection Error' : 'Could Not Load Shipments'),
        message: _errorMessage!,
        isNetworkError: _isNetworkError,
        isServiceUnavailable: _isServiceUnavailable,
        onRetry: _fetchShipments,
      );
    }

    final shipments = _filteredShipments;

    if (shipments.isEmpty) {
      return EmptyView(
        icon: Icons.local_shipping_outlined,
        title: 'No Shipments Found',
        message: _allShipments.isEmpty
            ? 'The ledger currently contains no produce shipments.'
            : 'No shipments match your filter criteria.',
        actionLabel: 'Refresh List',
        onAction: _fetchShipments,
      );
    }

    return RefreshIndicator(
      onRefresh: _fetchShipments,
      color: const Color(0xFF1B5E20),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: shipments.length,
        separatorBuilder: (context, index) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          final shipment = shipments[index];
          return _buildShipmentCard(shipment);
        },
      ),
    );
  }

  Widget _buildShipmentCard(Shipment shipment) {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => ShipmentDetailScreen(shipmentId: shipment.id),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      shipment.id,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1E293B),
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  if (shipment.hasGps)
                    Container(
                      margin: const EdgeInsets.only(right: 6),
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
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.bold,
                              color: Colors.blue.shade700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  StatusChip(status: shipment.status),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.place, size: 16, color: Color(0xFF64748B)),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      '${shipment.origin} → ${shipment.destination}',
                      style: const TextStyle(
                        fontSize: 13,
                        color: Color(0xFF334155),
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Produce: ${shipment.produceType} (${shipment.quantity.toStringAsFixed(0)} kg)',
                      style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: shipment.isAlert ? Colors.red.shade50 : Colors.green.shade50,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: shipment.isAlert ? Colors.red.shade200 : Colors.green.shade200,
                      ),
                    ),
                    child: Text(
                      'Risk: ${shipment.riskIndex.toStringAsFixed(1)}%',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: shipment.isAlert ? Colors.red.shade700 : Colors.green.shade800,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      key: Key('details_btn_${shipment.id}'),
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => ShipmentDetailScreen(shipmentId: shipment.id),
                          ),
                        );
                      },
                      icon: const Icon(Icons.info_outline, size: 15),
                      label: const Text(
                        'Details',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                      ),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFF334155),
                        side: const BorderSide(color: Color(0xFFCBD5E1)),
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ElevatedButton.icon(
                      key: Key('live_track_btn_${shipment.id}'),
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => ShipmentTrackingScreen(
                              shipmentId: shipment.id,
                              initialShipment: shipment,
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.radar, size: 15),
                      label: const Text(
                        'Live Track',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF1B5E20),
                        foregroundColor: Colors.white,
                        elevation: 1,
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
