import 'package:flutter/material.dart';
import '../models/geo_waypoint.dart';
import '../models/shipment.dart';

class GeospatialRouteCard extends StatelessWidget {
  final Shipment shipment;
  final List<GeoWaypoint> waypoints;
  final VoidCallback? onAddWaypoint;

  const GeospatialRouteCard({
    super.key,
    required this.shipment,
    required this.waypoints,
    this.onAddWaypoint,
  });

  @override
  Widget build(BuildContext context) {
    final hasWaypoints = waypoints.isNotEmpty;
    final hasGps = shipment.hasGps || hasWaypoints;

    return Container(
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
          // Header Bar
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: hasGps ? Colors.blue.shade50 : Colors.grey.shade100,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    hasGps ? Icons.satellite_alt_rounded : Icons.location_off_outlined,
                    size: 18,
                    color: hasGps ? Colors.blue.shade700 : Colors.grey.shade600,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        hasGps ? 'Geospatial Transit Corridor' : 'GPS Tracking Status',
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1E293B),
                        ),
                      ),
                      Text(
                        hasGps ? 'PostGIS SRID 4326 (WGS84)' : 'Telemetry Sensor Inactive',
                        style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                      ),
                    ],
                  ),
                ),
                if (onAddWaypoint != null)
                  TextButton.icon(
                    onPressed: onAddWaypoint,
                    icon: const Icon(Icons.add_location_alt, size: 16),
                    label: const Text('Add GPS Fix', style: TextStyle(fontSize: 12)),
                    style: TextButton.styleFrom(
                      foregroundColor: const Color(0xFF1B5E20),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    ),
                  ),
              ],
            ),
          ),
          const Divider(height: 1, color: Color(0xFFE2E8F0)),

          // Body Content
          if (!hasGps)
            _buildLocationUnavailable()
          else
            _buildCorridorView(context),
        ],
      ),
    );
  }

  Widget _buildLocationUnavailable() {
    return Padding(
      padding: const EdgeInsets.all(20.0),
      child: Column(
        children: [
          Icon(Icons.location_disabled_rounded, size: 38, color: Colors.grey.shade400),
          const SizedBox(height: 10),
          const Text(
            'GPS Location Unavailable',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Color(0xFF475569),
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'No PostGIS geographic waypoints have been recorded for this shipment yet. '
            'Geographic telemetry will update once vehicle tracking transponders ping or a manual checkpoint fix is logged.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: Color(0xFF64748B), height: 1.35),
          ),
          if (onAddWaypoint != null) ...[
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: onAddWaypoint,
              icon: const Icon(Icons.add_location_outlined, size: 16),
              label: const Text('Record First Checkpoint Fix'),
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF1B5E20),
                side: const BorderSide(color: Color(0xFF1B5E20)),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCorridorView(BuildContext context) {
    final latestWp = waypoints.isNotEmpty ? waypoints.last : shipment.latestWaypoint;
    final lat = latestWp?.latitude ?? shipment.latitude ?? 0.0;
    final lon = latestWp?.longitude ?? shipment.longitude ?? 0.0;
    final speed = latestWp?.speedKmh;
    final heading = latestWp?.headingDeg;
    final recordedAt = latestWp?.recordedAt ?? shipment.lastUpdate;

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Current GPS Banner
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF0FDF4),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFFBBF7D0)),
            ),
            child: Row(
              children: [
                const Icon(Icons.my_location_rounded, size: 20, color: Color(0xFF16A34A)),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '${lat.toStringAsFixed(4)}°N, ${lon.toStringAsFixed(4)}°E',
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF14532D),
                            ),
                          ),
                          if (speed != null)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: const Color(0xFFDCFCE7),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                '${speed.toStringAsFixed(0)} km/h',
                                style: const TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFF15803D),
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Fix logged: $recordedAt'
                        '${heading != null ? ' • Bearing: ${heading.toStringAsFixed(0)}°' : ''}',
                        style: const TextStyle(fontSize: 11, color: Color(0xFF166534)),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Corridor Progression Milestones
          const Text(
            'Corridor Transit Milestones',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: Color(0xFF334155),
            ),
          ),
          const SizedBox(height: 10),

          // Milestone Track
          _buildMilestoneItem(
            title: 'Origin: ${shipment.origin}',
            subtitle: shipment.originFacility != null
                ? '${shipment.originFacility!.formattedType} • ${shipment.originFacility!.district}'
                : 'Departure Terminal',
            isComplete: true,
            icon: Icons.store_mall_directory_outlined,
            color: const Color(0xFF1B5E20),
          ),

          if (waypoints.isNotEmpty) ...[
            ...waypoints.take(3).map((wp) => _buildMilestoneItem(
                  title: 'Waypoint (${wp.latitude.toStringAsFixed(3)}°N, ${wp.longitude.toStringAsFixed(3)}°E)',
                  subtitle: '${wp.recordedAt}${wp.speedKmh != null ? ' • ${wp.speedKmh!.toStringAsFixed(0)} km/h' : ''}',
                  isComplete: true,
                  icon: Icons.navigation_outlined,
                  color: Colors.blue.shade700,
                )),
            if (waypoints.length > 3)
              Padding(
                padding: const EdgeInsets.only(left: 36, bottom: 8),
                child: Text(
                  '+ ${waypoints.length - 3} earlier GPS transit fixes recorded',
                  style: const TextStyle(fontSize: 11, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
                ),
              ),
          ],

          _buildMilestoneItem(
            title: 'Destination: ${shipment.destination}',
            subtitle: shipment.destinationFacility != null
                ? '${shipment.destinationFacility!.formattedType} • ${shipment.destinationFacility!.district}'
                : 'Arrival Mandi / Hub',
            isComplete: shipment.isDelivered,
            icon: Icons.warehouse_outlined,
            color: shipment.isDelivered ? const Color(0xFF1B5E20) : Colors.grey.shade600,
            isLast: true,
          ),

          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: const Row(
              children: [
                Icon(Icons.info_outline, size: 14, color: Color(0xFF64748B)),
                SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Corridor waypoints represent direct geospatial fixes (WGS84). '
                    'Connections between points are schematic milestones, not confirmed turn-by-turn road paths.',
                    style: TextStyle(fontSize: 10, color: Color(0xFF64748B)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMilestoneItem({
    required String title,
    required String subtitle,
    required bool isComplete,
    required IconData icon,
    required Color color,
    bool isLast = false,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: isComplete ? color.withValues(alpha: 0.12) : Colors.grey.shade100,
                shape: BoxShape.circle,
                border: Border.all(
                  color: isComplete ? color : Colors.grey.shade400,
                  width: 1.5,
                ),
              ),
              child: Icon(icon, size: 14, color: isComplete ? color : Colors.grey.shade500),
            ),
            if (!isLast)
              Container(
                width: 1.5,
                height: 24,
                color: isComplete ? color.withValues(alpha: 0.4) : Colors.grey.shade300,
              ),
          ],
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: isComplete ? const Color(0xFF1E293B) : const Color(0xFF64748B),
                  ),
                ),
                Text(
                  subtitle,
                  style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
