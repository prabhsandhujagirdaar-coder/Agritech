import 'package:flutter/material.dart';
import '../models/facility.dart';
import '../services/api_service.dart';
import '../widgets/empty_view.dart';
import '../widgets/error_view.dart';

class FacilityDirectoryScreen extends StatefulWidget {
  const FacilityDirectoryScreen({super.key});

  @override
  State<FacilityDirectoryScreen> createState() => _FacilityDirectoryScreenState();
}

class _FacilityDirectoryScreenState extends State<FacilityDirectoryScreen> {
  final ApiService _apiService = ApiService();

  bool _isLoading = true;
  String? _errorMessage;
  bool _isNetworkError = false;
  bool _isServiceUnavailable = false;

  List<Facility> _allFacilities = [];
  String _selectedType = 'all';
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _loadFacilities();
  }

  Future<void> _loadFacilities() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _isNetworkError = false;
      _isServiceUnavailable = false;
    });

    try {
      final facilities = await _apiService.getFacilities();
      if (!mounted) return;
      setState(() {
        _allFacilities = facilities;
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
        _errorMessage = 'Failed to load storage facilities: $e';
      });
    }
  }

  List<Facility> get _filteredFacilities {
    return _allFacilities.where((f) {
      if (_selectedType != 'all' && f.facilityType.toLowerCase() != _selectedType) {
        return false;
      }
      if (_searchQuery.isNotEmpty) {
        final q = _searchQuery.toLowerCase();
        final matchesName = f.name.toLowerCase().contains(q);
        final matchesDistrict = f.district.toLowerCase().contains(q);
        final matchesCity = f.villageOrCity.toLowerCase().contains(q);
        final matchesId = f.id.toLowerCase().contains(q);
        return matchesName || matchesDistrict || matchesCity || matchesId;
      }
      return true;
    }).toList();
  }

  void _showFacilityDetails(Facility facility) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.65,
        minChildSize: 0.4,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8F5E9),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFFA5D6A7)),
                    ),
                    child: Text(
                      facility.formattedType,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1B5E20),
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              Text(
                facility.name,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              Text(
                'ID: ${facility.id} • ${facility.operationalStatus.toUpperCase()}',
                style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
              ),
              const Divider(height: 24),

              // Geographic Coordinates Card
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.location_on, size: 16, color: Color(0xFF1B5E20)),
                        SizedBox(width: 6),
                        Text(
                          'Geographic Coordinates (WGS84)',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${facility.latitude.toStringAsFixed(4)}°N, ${facility.longitude.toStringAsFixed(4)}°E',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF1E293B),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${facility.address}, ${facility.villageOrCity}, ${facility.district}, ${facility.state}'
                      '${facility.postalCode != null ? ' - ${facility.postalCode}' : ''}',
                      style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Operational Metrics
              const Text(
                'Facility Capacity & Environment',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),

              Row(
                children: [
                  Expanded(
                    child: _buildDetailTile(
                      label: 'Storage Capacity',
                      value: facility.capacity != null
                          ? '${facility.capacity!.toStringAsFixed(0)} ${facility.capacityUnit}'
                          : 'Not Specified',
                      icon: Icons.inventory_2_outlined,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _buildDetailTile(
                      label: 'Current Utilization',
                      value: facility.currentUtilization != null
                          ? '${facility.currentUtilization!.toStringAsFixed(1)}%'
                          : 'Unavailable',
                      icon: Icons.pie_chart_outline,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              Row(
                children: [
                  Expanded(
                    child: _buildDetailTile(
                      label: 'Optimal Temp Window',
                      value: facility.formattedTempRange,
                      icon: Icons.thermostat_outlined,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _buildDetailTile(
                      label: 'Data Pedigree',
                      value: facility.isDemoSimulated ? 'Demo Simulated' : 'Verified Facility',
                      icon: facility.isDemoSimulated ? Icons.science_outlined : Icons.verified_user_outlined,
                      highlight: !facility.isDemoSimulated,
                    ),
                  ),
                ],
              ),

              if (facility.isDemoSimulated) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFEF3C7),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFFFCD34D)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.info_outline, size: 16, color: Color(0xFFB45309)),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Notice: This facility location is marked "demo_simulated" as a Punjab corridor test fixture for academic validation.',
                          style: TextStyle(fontSize: 11, color: Color(0xFF92400E)),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailTile({
    required String label,
    required String value,
    required IconData icon,
    bool highlight = false,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
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
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: highlight ? const Color(0xFF16A34A) : const Color(0xFF1E293B),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Storage Facilities & Godowns'),
        backgroundColor: const Color(0xFF1B5E20),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _loadFacilities,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search & Filter Section
          Container(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            color: Colors.white,
            child: Column(
              children: [
                TextField(
                  decoration: InputDecoration(
                    hintText: 'Search facility name, district, mandi...',
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
                      _buildTypeFilterChip('All', 'all'),
                      const SizedBox(width: 8),
                      _buildTypeFilterChip('Cold Storage', 'cold_storage'),
                      const SizedBox(width: 8),
                      _buildTypeFilterChip('Godown', 'godown'),
                      const SizedBox(width: 8),
                      _buildTypeFilterChip('Packhouse', 'packhouse'),
                      const SizedBox(width: 8),
                      _buildTypeFilterChip('Warehouse', 'warehouse'),
                      const SizedBox(width: 8),
                      _buildTypeFilterChip('Mandi', 'mandi'),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: Color(0xFFE2E8F0)),

          // List Body
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildTypeFilterChip(String label, String value) {
    final isSelected = _selectedType == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          setState(() {
            _selectedType = value;
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
            ? 'Facilities Service Unavailable'
            : (_isNetworkError ? 'Network Connection Error' : 'Could Not Load Facilities'),
        message: _errorMessage!,
        isNetworkError: _isNetworkError,
        isServiceUnavailable: _isServiceUnavailable,
        onRetry: _loadFacilities,
      );
    }

    final facilities = _filteredFacilities;

    if (facilities.isEmpty) {
      return EmptyView(
        icon: Icons.store_mall_directory_outlined,
        title: 'No Facilities Found',
        message: _allFacilities.isEmpty
            ? 'No agricultural storage facilities registered in database.'
            : 'No storage facilities match your current search or filter criteria.',
        actionLabel: 'Refresh Directory',
        onAction: _loadFacilities,
      );
    }

    return RefreshIndicator(
      onRefresh: _loadFacilities,
      color: const Color(0xFF1B5E20),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: facilities.length,
        separatorBuilder: (context, index) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          final facility = facilities[index];
          return _buildFacilityCard(facility);
        },
      ),
    );
  }

  Widget _buildFacilityCard(Facility facility) {
    final utilization = facility.currentUtilization;

    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => _showFacilityDetails(facility),
        child: Padding(
          padding: const EdgeInsets.all(14.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      facility.name,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1E293B),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8F5E9),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      facility.formattedType,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1B5E20),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  const Icon(Icons.location_on_outlined, size: 14, color: Color(0xFF64748B)),
                  const SizedBox(width: 4),
                  Text(
                    '${facility.villageOrCity}, ${facility.district} • ${facility.state}',
                    style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Temp: ${facility.formattedTempRange}',
                    style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                  ),
                  if (utilization != null)
                    Text(
                      'Utilization: ${utilization.toStringAsFixed(0)}%',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: utilization > 85 ? Colors.amber.shade900 : const Color(0xFF1B5E20),
                      ),
                    ),
                  if (facility.isDemoSimulated)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFEF3C7),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'DEMO DATA',
                        style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Color(0xFF92400E)),
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
