import '../config/app_config.dart';

class CNNPredictionResult {
  final String predictedClass;
  final int classIndex;
  final String label;
  final double confidence;
  final Map<String, double> probabilities;
  final String targetCrop;
  final String modelName;
  final String? modelVersion;
  final String device;
  final double? inferenceMs;

  CNNPredictionResult({
    required this.predictedClass,
    required this.classIndex,
    required this.label,
    required this.confidence,
    required this.probabilities,
    required this.targetCrop,
    required this.modelName,
    this.modelVersion,
    required this.device,
    this.inferenceMs,
  });

  factory CNNPredictionResult.fromJson(Map<String, dynamic> json) {
    final probsRaw = json['probabilities'];
    final Map<String, double> probs = {};
    if (probsRaw is Map) {
      probsRaw.forEach((key, value) {
        if (value is num) {
          probs[key.toString()] = value.toDouble();
        }
      });
    }

    return CNNPredictionResult(
      predictedClass: json['predicted_class']?.toString() ?? 'Unknown',
      classIndex: (json['class_index'] as num?)?.toInt() ?? 0,
      label: json['label']?.toString() ?? json['predicted_class']?.toString() ?? 'Unknown',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      probabilities: probs,
      targetCrop: json['target_crop']?.toString() ?? 'guava',
      modelName: json['model_name']?.toString() ?? 'resnet18',
      modelVersion: json['model_version']?.toString(),
      device: json['device']?.toString() ?? 'cpu',
      inferenceMs: (json['inference_ms'] as num?)?.toDouble(),
    );
  }

  /// Phase 7 Uncertainty Heuristic Evaluation
  /// Low top score (<60%) OR top score margin with 2nd class is <15%
  bool get isUncertain {
    if (confidence < AppConfig.minTopScore) {
      return true;
    }

    if (probabilities.length >= 2) {
      final sortedScores = probabilities.values.toList()
        ..sort((a, b) => b.compareTo(a));
      final top = sortedScores[0];
      final second = sortedScores[1];
      if ((top - second) < AppConfig.minScoreMargin) {
        return true;
      }
    }

    return false;
  }

  String? get uncertaintyReason {
    if (confidence < AppConfig.minTopScore) {
      return 'Top softmax score (${(confidence * 100).toStringAsFixed(1)}%) is below the ${((AppConfig.minTopScore) * 100).toInt()}% threshold.';
    }

    if (probabilities.length >= 2) {
      final sortedScores = probabilities.values.toList()
        ..sort((a, b) => b.compareTo(a));
      final top = sortedScores[0];
      final second = sortedScores[1];
      final margin = top - second;
      if (margin < AppConfig.minScoreMargin) {
        return 'Close classification margin (${(margin * 100).toStringAsFixed(1)}% difference between top 2 classes < ${(AppConfig.minScoreMargin * 100).toInt()}%).';
      }
    }

    return null;
  }
}
