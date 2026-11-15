import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../models/geo_waypoint.dart';
import '../models/shipment.dart';

/// Interactive vector corridor map for AgriChain AI live shipment tracking.
/// Projects WGS84 PostGIS coordinates onto an interactive canvas with:
/// - Coordinate grid lines and True North indicator
/// - Traversed route corridor and planned transit segments
/// - Numbered waypoint checkpoints
/// - Origin packhouse and destination mandi terminal nodes
/// - Animated pulsing radar vehicle marker with bearing/heading
/// - Clear DEMO/SIMULATED or LIVE status watermarks
/// - Pan and zoom support via InteractiveViewer
class InteractiveRouteMap extends StatefulWidget {
  final Shipment shipment;
  final List<GeoWaypoint> waypoints;
  final bool isDemoMode;
  final double? currentLat;
  final double? currentLon;
  final double? speedKmh;
  final double? headingDeg;
  final String? lastUpdate;

  const InteractiveRouteMap({
    super.key,
    required this.shipment,
    required this.waypoints,
    this.isDemoMode = false,
    this.currentLat,
    this.currentLon,
    this.speedKmh,
    this.headingDeg,
    this.lastUpdate,
  });

  @override
  State<InteractiveRouteMap> createState() => _InteractiveRouteMapState();
}

class _InteractiveRouteMapState extends State<InteractiveRouteMap>
    with SingleTickerProviderStateMixin {
  late AnimationController _radarController;
  final TransformationController _transformController = TransformationController();

  @override
  void initState() {
    super.initState();
    _radarController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat();
  }

  @override
  void dispose() {
    _radarController.dispose();
    _transformController.dispose();
    super.dispose();
  }

  void _resetZoom() {
    _transformController.value = Matrix4.identity();
  }

  @override
  Widget build(BuildContext context) {
    final effectiveLat = widget.currentLat ??
        (widget.waypoints.isNotEmpty ? widget.waypoints.last.latitude : widget.shipment.latitude);
    final effectiveLon = widget.currentLon ??
        (widget.waypoints.isNotEmpty ? widget.waypoints.last.longitude : widget.shipment.longitude);

    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Container(
        height: 380,
        decoration: const BoxDecoration(
          color: Color(0xFF0A1128), // Deep tactical radar slate
        ),
        child: Stack(
          children: [
            // Interactive vector canvas
            InteractiveViewer(
              transformationController: _transformController,
              minScale: 0.7,
              maxScale: 4.0,
              boundaryMargin: const EdgeInsets.all(40),
              child: AnimatedBuilder(
                animation: _radarController,
                builder: (context, _) {
                  return CustomPaint(
                    size: const Size(double.infinity, 380),
                    painter: _CorridorMapPainter(
                      shipment: widget.shipment,
                      waypoints: widget.waypoints,
                      currentLat: effectiveLat,
                      currentLon: effectiveLon,
                      speedKmh: widget.speedKmh ?? (widget.waypoints.isNotEmpty ? widget.waypoints.last.speedKmh : null),
                      headingDeg: widget.headingDeg ?? (widget.waypoints.isNotEmpty ? widget.waypoints.last.headingDeg : null),
                      pulseValue: _radarController.value,
                      isDemoMode: widget.isDemoMode,
                    ),
                  );
                },
              ),
            ),

            // Top-left: Compass True North Indicator
            Positioned(
              top: 14,
              left: 14,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.65),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 14,
                      height: 14,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.redAccent, width: 1.5),
                      ),
                      child: const Text(
                        'N',
                        style: TextStyle(
                          color: Colors.redAccent,
                          fontSize: 9,
                          fontWeight: FontWeight.bold,
                          height: 1.0,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    const Text(
                      'WGS84 SRID 4326',
                      style: TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Top-right: Live vs Demo Mode Watermark Badge
            Positioned(
              top: 14,
              right: 14,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: widget.isDemoMode
                      ? const Color(0xFF581C87).withValues(alpha: 0.90) // Deep purple
                      : const Color(0xFF065F46).withValues(alpha: 0.85), // Deep emerald
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: widget.isDemoMode
                        ? const Color(0xFFC084FC)
                        : const Color(0xFF34D399),
                    width: 1.2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: widget.isDemoMode
                          ? Colors.purple.withValues(alpha: 0.3)
                          : Colors.green.withValues(alpha: 0.3),
                      blurRadius: 8,
                    ),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      widget.isDemoMode
                          ? Icons.science_outlined
                          : Icons.fiber_manual_record,
                      size: 11,
                      color: widget.isDemoMode
                          ? const Color(0xFFF3E8FF)
                          : const Color(0xFF6EE7B7),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      widget.isDemoMode
                          ? 'DEMO / SIMULATED'
                          : 'LIVE TELEMETRY',
                      style: TextStyle(
                        color: widget.isDemoMode
                            ? Colors.white
                            : const Color(0xFFD1FAE5),
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Bottom-left: Schematic Route Corridor Disclaimer
            Positioned(
              bottom: 12,
              left: 14,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.60),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  '• Schematic transit corridor • Direct coordinate projection',
                  style: TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 10,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ),
            ),

            // Bottom-right: Interactive Controls (Fit route / Reset zoom)
            Positioned(
              bottom: 12,
              right: 14,
              child: FloatingActionButton.small(
                heroTag: 'recenter_map_fab',
                onPressed: _resetZoom,
                backgroundColor: const Color(0xFF1E293B),
                foregroundColor: const Color(0xFF38BDF8),
                tooltip: 'Reset View / Fit Route',
                child: const Icon(Icons.center_focus_strong, size: 18),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CorridorMapPainter extends CustomPainter {
  final Shipment shipment;
  final List<GeoWaypoint> waypoints;
  final double? currentLat;
  final double? currentLon;
  final double? speedKmh;
  final double? headingDeg;
  final double pulseValue;
  final bool isDemoMode;

  _CorridorMapPainter({
    required this.shipment,
    required this.waypoints,
    required this.currentLat,
    required this.currentLon,
    required this.speedKmh,
    required this.headingDeg,
    required this.pulseValue,
    required this.isDemoMode,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final width = size.width;
    final height = size.height;

    // 1. Establish origin & destination coordinates
    final originCoords = _getOriginCoords();
    final destCoords = _getDestCoords();

    // 2. Gather all plotted points for boundary calculations
    final List<math.Point<double>> points = [];
    points.add(math.Point(originCoords[0], originCoords[1]));
    for (final wp in waypoints) {
      points.add(math.Point(wp.latitude, wp.longitude));
    }
    if (currentLat != null && currentLon != null) {
      points.add(math.Point(currentLat!, currentLon!));
    }
    points.add(math.Point(destCoords[0], destCoords[1]));

    double minLat = points.map((p) => p.x).reduce(math.min);
    double maxLat = points.map((p) => p.x).reduce(math.max);
    double minLon = points.map((p) => p.y).reduce(math.min);
    double maxLon = points.map((p) => p.y).reduce(math.max);

    // Add safe margin
    final latPadding = math.max((maxLat - minLat) * 0.25, 0.25);
    final lonPadding = math.max((maxLon - minLon) * 0.25, 0.25);
    minLat -= latPadding;
    maxLat += latPadding;
    minLon -= lonPadding;
    maxLon += lonPadding;

    // Projection function from (lat, lon) to canvas Offset(x, y)
    Offset project(double lat, double lon) {
      final normX = (lon - minLon) / (maxLon - minLon);
      // Invert Y because canvas Y grows downwards while Latitude grows upwards
      final normY = (maxLat - lat) / (maxLat - minLat);

      const margin = 40.0;
      final usableWidth = width - margin * 2;
      final usableHeight = height - margin * 2;

      final x = margin + normX * usableWidth;
      final y = margin + normY * usableHeight;
      return Offset(x, y);
    }

    // 3. Draw radar coordinate grid
    _drawGrid(canvas, size, minLat, maxLat, minLon, maxLon);

    // 4. Project key points
    final originOffset = project(originCoords[0], originCoords[1]);
    final destOffset = project(destCoords[0], destCoords[1]);
    final waypointOffsets = waypoints.map((wp) => project(wp.latitude, wp.longitude)).toList();

    final Offset vehicleOffset;
    if (currentLat != null && currentLon != null) {
      vehicleOffset = project(currentLat!, currentLon!);
    } else if (waypointOffsets.isNotEmpty) {
      vehicleOffset = waypointOffsets.last;
    } else {
      vehicleOffset = originOffset;
    }

    // 5. Draw corridor route path
    _drawRouteCorridor(
      canvas: canvas,
      origin: originOffset,
      destination: destOffset,
      waypoints: waypointOffsets,
      vehicle: vehicleOffset,
    );

    // 6. Draw Waypoint Checkpoints
    for (int i = 0; i < waypointOffsets.length; i++) {
      final wpOffset = waypointOffsets[i];
      final wp = waypoints[i];
      final isSimulated = wp.locationMetadata['source'] == 'demo_simulated' ||
          wp.locationMetadata['simulated'] == true;
      _drawWaypointNode(canvas, wpOffset, i + 1, isSimulated);
    }

    // 7. Draw Origin packhouse terminal node
    _drawTerminalNode(
      canvas: canvas,
      offset: originOffset,
      label: 'ORIGIN',
      sublabel: shipment.originFacility?.district ?? 'Abohar',
      color: const Color(0xFF10B981), // Emerald
      iconCode: 0xe068, // warehouse/store
    );

    // 8. Draw Destination mandi hub terminal node
    _drawTerminalNode(
      canvas: canvas,
      offset: destOffset,
      label: 'DESTINATION',
      sublabel: shipment.destinationFacility?.district ?? 'Delhi APMC',
      color: const Color(0xFFF59E0B), // Amber
      iconCode: 0xe3a8, // location_on
    );

    // 9. Draw vehicle marker with radar pulses
    _drawVehicleMarker(
      canvas: canvas,
      offset: vehicleOffset,
      headingDeg: headingDeg ?? 85.0,
      speedKmh: speedKmh ?? 55.0,
      pulse: pulseValue,
    );
  }

  void _drawGrid(
    Canvas canvas,
    Size size,
    double minLat,
    double maxLat,
    double minLon,
    double maxLon,
  ) {
    final gridPaint = Paint()
      ..color = const Color(0xFF1E293B).withValues(alpha: 0.6)
      ..strokeWidth = 0.8
      ..style = PaintingStyle.stroke;

    final dotPaint = Paint()
      ..color = const Color(0xFF334155).withValues(alpha: 0.8)
      ..strokeWidth = 1.0;

    // Draw grid lines
    const gridCols = 5;
    const gridRows = 4;

    for (int c = 1; c < gridCols; c++) {
      final x = size.width * (c / gridCols);
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }

    for (int r = 1; r < gridRows; r++) {
      final y = size.height * (r / gridRows);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    // Small coordinate tick markers
    for (int c = 1; c < gridCols; c++) {
      for (int r = 1; r < gridRows; r++) {
        final x = size.width * (c / gridCols);
        final y = size.height * (r / gridRows);
        canvas.drawCircle(Offset(x, y), 1.5, dotPaint);
      }
    }
  }

  void _drawRouteCorridor({
    required Canvas canvas,
    required Offset origin,
    required Offset destination,
    required List<Offset> waypoints,
    required Offset vehicle,
  }) {
    // Halo glow paint for traversed path
    final haloPaint = Paint()
      ..color = const Color(0xFF0284C7).withValues(alpha: 0.20)
      ..strokeWidth = 10.0
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..style = PaintingStyle.stroke;

    // Traversed line paint (Solid cyan)
    final traversedPaint = Paint()
      ..color = const Color(0xFF38BDF8)
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..style = PaintingStyle.stroke;

    // Planned upcoming path paint (Dashed slate)
    final plannedPaint = Paint()
      ..color = const Color(0xFF64748B)
      ..strokeWidth = 2.0
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    final traversedPath = Path();
    traversedPath.moveTo(origin.dx, origin.dy);

    for (final wp in waypoints) {
      traversedPath.lineTo(wp.dx, wp.dy);
    }

    // Connect to vehicle marker
    traversedPath.lineTo(vehicle.dx, vehicle.dy);

    canvas.drawPath(traversedPath, haloPaint);
    canvas.drawPath(traversedPath, traversedPaint);

    // Draw planned path from vehicle to destination with dash effect
    _drawDashedLine(canvas, vehicle, destination, plannedPaint);
  }

  void _drawDashedLine(Canvas canvas, Offset p1, Offset p2, Paint paint) {
    const dashWidth = 6.0;
    const dashSpace = 4.0;
    final dx = p2.dx - p1.dx;
    final dy = p2.dy - p1.dy;
    final distance = math.sqrt(dx * dx + dy * dy);
    if (distance == 0) return;

    final unitDx = dx / distance;
    final unitDy = dy / distance;

    double currentDist = 0.0;
    while (currentDist < distance) {
      final start = Offset(p1.dx + unitDx * currentDist, p1.dy + unitDy * currentDist);
      final step = math.min(dashWidth, distance - currentDist);
      final end = Offset(start.dx + unitDx * step, start.dy + unitDy * step);
      canvas.drawLine(start, end, paint);
      currentDist += dashWidth + dashSpace;
    }
  }

  void _drawWaypointNode(Canvas canvas, Offset offset, int index, bool isSimulated) {
    final ringPaint = Paint()
      ..color = isSimulated ? const Color(0xFFA855F7) : const Color(0xFF38BDF8)
      ..style = PaintingStyle.fill;

    final centerPaint = Paint()
      ..color = const Color(0xFF0A1128)
      ..style = PaintingStyle.fill;

    canvas.drawCircle(offset, 8, ringPaint);
    canvas.drawCircle(offset, 5, centerPaint);

    // Text label for waypoint index
    final textSpan = TextSpan(
      text: '$index',
      style: TextStyle(
        color: isSimulated ? const Color(0xFFE9D5FF) : const Color(0xFFBAE6FD),
        fontSize: 8,
        fontWeight: FontWeight.bold,
      ),
    );
    final textPainter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
    )..layout();

    textPainter.paint(
      canvas,
      Offset(offset.dx - textPainter.width / 2, offset.dy - textPainter.height / 2),
    );
  }

  void _drawTerminalNode({
    required Canvas canvas,
    required Offset offset,
    required String label,
    required String sublabel,
    required Color color,
    required int iconCode,
  }) {
    // Outer pulse ring
    final pulsePaint = Paint()
      ..color = color.withValues(alpha: 0.25)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(offset, 14, pulsePaint);

    // Solid node
    final nodePaint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;
    canvas.drawCircle(offset, 9, nodePaint);

    // Inner white dot
    final whitePaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;
    canvas.drawCircle(offset, 4, whitePaint);

    // Label tag
    final textSpan = TextSpan(
      children: [
        TextSpan(
          text: '$label\n',
          style: TextStyle(
            color: color,
            fontSize: 9,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
        TextSpan(
          text: sublabel,
          style: const TextStyle(
            color: Color(0xFFCBD5E1),
            fontSize: 8,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
    final textPainter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
      textAlign: TextAlign.center,
    )..layout();

    textPainter.paint(
      canvas,
      Offset(offset.dx - textPainter.width / 2, offset.dy + 12),
    );
  }

  void _drawVehicleMarker({
    required Canvas canvas,
    required Offset offset,
    required double headingDeg,
    required double speedKmh,
    required double pulse,
  }) {
    // Radar pulsing concentric halo waves
    final maxRadius = 32.0;
    final currentRadius = 12.0 + (maxRadius - 12.0) * pulse;
    final waveAlpha = (1.0 - pulse) * 0.45;

    final wavePaint = Paint()
      ..color = const Color(0xFF00E5FF).withValues(alpha: waveAlpha)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;
    canvas.drawCircle(offset, currentRadius, wavePaint);

    // Inner glow
    final glowPaint = Paint()
      ..color = const Color(0xFF0284C7).withValues(alpha: 0.35)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(offset, 16, glowPaint);

    // Vehicle pin container
    final pinPaint = Paint()
      ..color = const Color(0xFF0284C7)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(offset, 11, pinPaint);

    final borderPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;
    canvas.drawCircle(offset, 11, borderPaint);

    // Vehicle directional pointer
    canvas.save();
    canvas.translate(offset.dx, offset.dy);
    // Convert heading from degrees to radians
    final rad = (headingDeg - 90.0) * math.pi / 180.0;
    canvas.rotate(rad);

    final arrowPath = Path()
      ..moveTo(6, 0)
      ..lineTo(-4, -4)
      ..lineTo(-2, 0)
      ..lineTo(-4, 4)
      ..close();

    final arrowPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;
    canvas.drawPath(arrowPath, arrowPaint);
    canvas.restore();

    // Callout bubble with speed
    final speedBadge = '${speedKmh.toStringAsFixed(0)} km/h';
    final badgeSpan = TextSpan(
      text: speedBadge,
      style: const TextStyle(
        color: Colors.white,
        fontSize: 9,
        fontWeight: FontWeight.bold,
      ),
    );
    final badgePainter = TextPainter(
      text: badgeSpan,
      textDirection: TextDirection.ltr,
    )..layout();

    final badgeRect = RRect.fromRectAndRadius(
      Rect.fromCenter(
        center: Offset(offset.dx, offset.dy - 19),
        width: badgePainter.width + 10,
        height: 14,
      ),
      const Radius.circular(4),
    );
    final badgeBgPaint = Paint()..color = const Color(0xFF0369A1);
    canvas.drawRRect(badgeRect, badgeBgPaint);
    badgePainter.paint(
      canvas,
      Offset(offset.dx - badgePainter.width / 2, offset.dy - 19 - badgePainter.height / 2),
    );
  }

  List<double> _getOriginCoords() {
    if (shipment.originFacility != null) {
      return [shipment.originFacility!.latitude, shipment.originFacility!.longitude];
    }
    if (shipment.origin.toLowerCase().contains('fazilka')) {
      return [30.4037, 74.0254];
    }
    // Default Abohar
    return [30.1453, 74.1994];
  }

  List<double> _getDestCoords() {
    if (shipment.destinationFacility != null) {
      return [shipment.destinationFacility!.latitude, shipment.destinationFacility!.longitude];
    }
    final dest = shipment.destination.toLowerCase();
    if (dest.contains('delhi') || dest.contains('azadpur')) {
      return [28.7161, 77.1772];
    }
    if (dest.contains('ludhiana')) {
      return [30.9010, 75.8573];
    }
    if (dest.contains('amritsar')) {
      return [31.6340, 74.8723];
    }
    if (dest.contains('bathinda')) {
      return [30.2110, 74.9455];
    }
    if (dest.contains('jalandhar')) {
      return [31.3260, 75.5762];
    }
    return [28.7161, 77.1772];
  }

  @override
  bool shouldRepaint(covariant _CorridorMapPainter oldDelegate) {
    return oldDelegate.pulseValue != pulseValue ||
        oldDelegate.currentLat != currentLat ||
        oldDelegate.currentLon != currentLon ||
        oldDelegate.waypoints.length != waypoints.length ||
        oldDelegate.isDemoMode != isDemoMode;
  }
}
