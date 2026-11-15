import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';

import '../config/app_config.dart';

enum WebSocketStatus {
  disconnected,
  connecting,
  connected,
  reconnecting,
}

class WebSocketEvent {
  final String event;
  final Map<String, dynamic> data;
  final String timestamp;

  WebSocketEvent({
    required this.event,
    required this.data,
    required this.timestamp,
  });

  factory WebSocketEvent.fromJson(Map<String, dynamic> json) {
    final rawData = json['data'];
    return WebSocketEvent(
      event: json['event']?.toString() ?? 'unknown',
      data: rawData is Map<String, dynamic>
          ? rawData
          : (rawData is Map ? Map<String, dynamic>.from(rawData) : {}),
      timestamp: json['timestamp']?.toString() ?? '',
    );
  }
}

/// Real-time WebSocket Gateway client for AgriChain AI.
/// Subscribes to /ws/shipments on FastAPI backend.
/// Handles keep-alive pings, automatic exponential backoff reconnection,
/// and live event broadcasting for shipments, telemetry, and waypoints.
class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  /// Global toggle (can be disabled during unit/widget testing)
  static bool enabled = true;

  WebSocket? _socket;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  bool _isDisposed = false;
  bool _autoReconnect = true;

  final ValueNotifier<WebSocketStatus> status =
      ValueNotifier<WebSocketStatus>(WebSocketStatus.disconnected);

  final StreamController<WebSocketEvent> _eventController =
      StreamController<WebSocketEvent>.broadcast();

  Stream<WebSocketEvent> get eventStream => _eventController.stream;

  /// Stream filtered for specific event types
  Stream<WebSocketEvent> onEvent(String eventName) {
    return _eventController.stream.where((e) => e.event == eventName);
  }

  void init() {
    _isDisposed = false;
    AppConfig.activeBaseUrl.addListener(_onBaseUrlChanged);
    if (enabled) {
      connect();
    }
  }

  void _onBaseUrlChanged() {
    if (_isDisposed) return;
    disconnect();
    _reconnectAttempts = 0;
    if (enabled) {
      connect();
    }
  }

  Future<void> connect() async {
    if (!enabled || _isDisposed) return;
    _autoReconnect = true;
    if (_socket != null &&
        (_socket!.readyState == WebSocket.connecting ||
            _socket!.readyState == WebSocket.open)) {
      return;
    }

    _cancelTimers();

    final wsUrl = AppConfig.getWsUrl('/ws/shipments');
    status.value = _reconnectAttempts > 0
        ? WebSocketStatus.reconnecting
        : WebSocketStatus.connecting;

    try {
      final uri = Uri.parse(wsUrl);
      final socket = await WebSocket.connect(uri.toString())
          .timeout(const Duration(seconds: 6));

      _socket = socket;
      status.value = WebSocketStatus.connected;
      _reconnectAttempts = 0;

      // Start ping heartbeat (FastAPI handles 'ping' -> 'pong')
      _startHeartbeat();

      _socket!.listen(
        _onMessageReceived,
        onDone: _onSocketClosed,
        onError: (err) {
          debugPrint('WebSocket error on $wsUrl: $err');
          _onSocketClosed();
        },
        cancelOnError: true,
      );
    } catch (e) {
      debugPrint('WebSocket connection failed to $wsUrl: $e');
      _scheduleReconnect();
    }
  }

  void _onMessageReceived(dynamic message) {
    try {
      final text = message.toString();
      if (text.trim().toLowerCase() == 'pong') {
        return; // Heartbeat response received
      }

      final Map<String, dynamic> jsonMsg = json.decode(text);
      if (jsonMsg['type'] == 'pong') {
        return;
      }

      final event = WebSocketEvent.fromJson(jsonMsg);
      _eventController.add(event);
    } catch (e) {
      debugPrint('Failed to parse incoming WebSocket message: $e');
    }
  }

  void _onSocketClosed() {
    _socket = null;
    _cancelHeartbeat();
    status.value = WebSocketStatus.disconnected;
    if (!_isDisposed) {
      _scheduleReconnect();
    }
  }

  void _startHeartbeat() {
    _cancelHeartbeat();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      if (_socket != null && _socket!.readyState == WebSocket.open) {
        try {
          _socket!.add(json.encode({'type': 'ping'}));
        } catch (_) {}
      }
    });
  }

  void _cancelHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  void _scheduleReconnect() {
    if (_isDisposed || !_autoReconnect) return;
    _cancelTimers();

    _reconnectAttempts++;
    status.value = WebSocketStatus.reconnecting;

    // Exponential backoff: 2s, 4s, 8s, max 16s
    final delaySeconds = (_reconnectAttempts <= 4)
        ? (1 << _reconnectAttempts)
        : 16;

    _reconnectTimer = Timer(Duration(seconds: delaySeconds), () {
      if (!_isDisposed && _autoReconnect) {
        connect();
      }
    });
  }

  void _cancelTimers() {
    _cancelHeartbeat();
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  void disconnect() {
    _autoReconnect = false;
    _cancelTimers();
    if (_socket != null) {
      try {
        _socket!.close();
      } catch (_) {}
      _socket = null;
    }
    status.value = WebSocketStatus.disconnected;
  }

  void dispose() {
    _isDisposed = true;
    AppConfig.activeBaseUrl.removeListener(_onBaseUrlChanged);
    disconnect();
    _eventController.close();
  }
}
