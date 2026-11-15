import 'package:flutter/foundation.dart';

/// Application configuration and environment constants for AgriChain AI Mobile.
class AppConfig {
  /// Default backend API Base URL.
  /// Android Emulator loopback uses 10.0.2.2:8000.
  /// Physical devices should set this to their host LAN IP (e.g. 192.168.1.50:8000).
  /// Desktop / Web test runners can use 127.0.0.1:8000.
  static const String _defaultEmulatorUrl = 'http://10.0.2.2:8000/api/v1';
  static const String _defaultLocalhostUrl = 'http://127.0.0.1:8000/api/v1';

  static String defaultBaseUrl = kIsWeb
      ? _defaultLocalhostUrl
      : (defaultTargetPlatform == TargetPlatform.android
          ? _defaultEmulatorUrl
          : _defaultLocalhostUrl);

  /// Compile-time environment override via `--dart-define=API_BASE_URL=...`
  static const String _envApiBaseUrl = String.fromEnvironment('API_BASE_URL');

  /// Active base URL (notifier allows dynamic changes at runtime for physical testing)
  static final ValueNotifier<String> activeBaseUrl = ValueNotifier<String>(
    _envApiBaseUrl.isNotEmpty ? _envApiBaseUrl : defaultBaseUrl,
  );

  /// Derive WebSocket Gateway URL from the active REST Base URL
  static String getWsUrl([String endpoint = '/ws/shipments']) {
    final base = activeBaseUrl.value.trim().replaceAll(RegExp(r'/+$'), '');
    String wsBase = base;
    if (wsBase.startsWith('https://')) {
      wsBase = wsBase.replaceFirst('https://', 'wss://');
    } else if (wsBase.startsWith('http://')) {
      wsBase = wsBase.replaceFirst('http://', 'ws://');
    } else if (!wsBase.startsWith('ws://') && !wsBase.startsWith('wss://')) {
      wsBase = 'ws://$wsBase';
    }

    // Strip REST route prefixes such as /api/v1 or /api
    wsBase = wsBase.replaceAll(RegExp(r'/api(/v1)?$'), '');

    final cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/$endpoint';
    return '$wsBase$cleanEndpoint';
  }

  /// Target Crop Specifications
  static const String targetCropName = 'Guava';
  static const String targetCropBotanical = 'Psidium guajava L.';

  /// Valid Guava Maturity Classes
  static const List<String> guavaClasses = [
    'Green',
    'Mature Green',
    'Ripe',
  ];

  /// Uncertainty Detection Thresholds (matching Phase 7 Frontend Heuristics)
  static const double minTopScore = 0.60;
  static const double minScoreMargin = 0.15;

  /// Scientific Disclaimers
  static const String softmaxDisclaimer =
      'Softmax output scores are uncalibrated heuristic scores, not statistical probabilities.';

  static const String maturityScopeLimitation =
      'Visual maturity estimation only. This tool does not diagnose diseases, '
      'detect internal pathogens, certify food safety, or assign statutory commercial grades.';

  static const String batchTrackingScope =
      'Evaluation is conducted on representative fruit lot samples and does not '
      'track or certify individual fruit identities.';
}
