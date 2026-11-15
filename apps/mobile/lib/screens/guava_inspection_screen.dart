import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../config/app_config.dart';
import '../models/cnn_prediction.dart';
import '../services/api_service.dart';
import '../widgets/scientific_disclaimer_card.dart';

class GuavaInspectionScreen extends StatefulWidget {
  const GuavaInspectionScreen({super.key});

  @override
  State<GuavaInspectionScreen> createState() => _GuavaInspectionScreenState();
}

class _GuavaInspectionScreenState extends State<GuavaInspectionScreen> {
  final ApiService _apiService = ApiService();
  final ImagePicker _picker = ImagePicker();

  XFile? _selectedImage;
  Uint8List? _imageBytes;

  bool _isEvaluating = false;
  String? _errorMessage;
  bool _isServiceUnavailable = false;
  CNNPredictionResult? _predictionResult;

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(
        source: source,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );

      if (picked != null) {
        final bytes = await picked.readAsBytes();
        setState(() {
          _selectedImage = picked;
          _imageBytes = bytes;
          _predictionResult = null;
          _errorMessage = null;
          _isServiceUnavailable = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to capture or select image: $e';
      });
    }
  }

  Future<void> _runInference() async {
    if (_imageBytes == null || _selectedImage == null) return;

    setState(() {
      _isEvaluating = true;
      _errorMessage = null;
      _isServiceUnavailable = false;
    });

    try {
      final result = await _apiService.predictGuavaMaturity(
        _imageBytes!,
        _selectedImage!.name,
      );

      if (!mounted) return;
      setState(() {
        _predictionResult = result;
        _isEvaluating = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _isEvaluating = false;
        _errorMessage = e.message;
        _isServiceUnavailable = e.isServiceUnavailable;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isEvaluating = false;
        _errorMessage = 'Unexpected prediction failure: $e';
      });
    }
  }

  Color _getClassColor(String className) {
    switch (className.toLowerCase()) {
      case 'green':
        return const Color(0xFF15803D);
      case 'mature green':
        return const Color(0xFF854D0E);
      case 'ripe':
        return const Color(0xFFD97706);
      default:
        return Colors.blueGrey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Guava Maturity Ingest'),
        backgroundColor: const Color(0xFF1B5E20),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Target Crop Banner
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFFE8F5E9),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFA5D6A7)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.eco, color: Color(0xFF1B5E20), size: 20),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Target Crop: Guava (Psidium guajava L.) • ResNet18 Maturity Classifier',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1B5E20),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Image Picker / Preview Card
            _buildImageCard(),
            const SizedBox(height: 16),

            // Inference Trigger Button
            if (_imageBytes != null && _predictionResult == null)
              ElevatedButton.icon(
                onPressed: _isEvaluating ? null : _runInference,
                icon: _isEvaluating
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.bolt),
                label: Text(
                  _isEvaluating ? 'Evaluating on Backend...' : 'Run Maturity Classification',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1B5E20),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),

            // Error Display (handles HTTP 503 or Network Failure)
            if (_errorMessage != null) ...[
              const SizedBox(height: 16),
              _buildErrorBanner(),
            ],

            // Prediction Result Card
            if (_predictionResult != null) ...[
              const SizedBox(height: 16),
              _buildResultCard(_predictionResult!),
            ],

            const SizedBox(height: 20),
            const ScientificDisclaimerCard(),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildImageCard() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFCBD5E1)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          if (_imageBytes != null)
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
              child: Image.memory(
                _imageBytes!,
                height: 240,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            )
          else
            Container(
              height: 180,
              decoration: const BoxDecoration(
                color: Color(0xFFF8FAFC),
                borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.add_photo_alternate_outlined,
                        size: 48, color: Colors.grey.shade400),
                    const SizedBox(height: 8),
                    Text(
                      'No Guava sample selected',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey.shade600,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Capture or upload a clear photo of the fruit lot sample',
                      style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                    ),
                  ],
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(12.0),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isEvaluating ? null : () => _pickImage(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt, size: 18),
                    label: const Text('Take Photo'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF1B5E20),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isEvaluating ? null : () => _pickImage(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library, size: 18),
                    label: const Text('From Gallery'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF1B5E20),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _isServiceUnavailable ? const Color(0xFFFFFBEB) : const Color(0xFFFEF2F2),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: _isServiceUnavailable ? const Color(0xFFFDE68A) : const Color(0xFFFECACA),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                _isServiceUnavailable ? Icons.warning_amber_rounded : Icons.error_outline,
                color: _isServiceUnavailable ? Colors.amber.shade900 : Colors.red.shade800,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                _isServiceUnavailable ? 'Model Service Unavailable (503)' : 'Inference Failed',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: _isServiceUnavailable ? Colors.amber.shade900 : Colors.red.shade800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _errorMessage!,
            style: TextStyle(
              fontSize: 12,
              color: _isServiceUnavailable ? Colors.amber.shade900 : Colors.red.shade900,
              height: 1.35,
            ),
          ),
          if (_isServiceUnavailable) ...[
            const SizedBox(height: 8),
            const Text(
              'Diagnostic Notice: Ensure the FastAPI backend is launched with TARGET_CROP=guava and GUAVA_MODEL_ACTIVATED=true.',
              style: TextStyle(fontSize: 11, fontStyle: FontStyle.italic, color: Color(0xFF78350F)),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildResultCard(CNNPredictionResult result) {
    final classColor = _getClassColor(result.predictedClass);
    final isUncertain = result.isUncertain;

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
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
          // Header Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Maturity Classification',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  '${result.inferenceMs?.toStringAsFixed(1) ?? '—'} ms • ${result.device.toUpperCase()}',
                  style: const TextStyle(fontSize: 11, color: Color(0xFF475569)),
                ),
              ),
            ],
          ),
          const Divider(height: 20),

          // Main Class Badge
          Center(
            child: Column(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  decoration: BoxDecoration(
                    color: classColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(30),
                    border: Border.all(color: classColor, width: 1.5),
                  ),
                  child: Text(
                    result.predictedClass.toUpperCase(),
                    style: TextStyle(
                      color: classColor,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Softmax Score: ${(result.confidence * 100).toStringAsFixed(1)}%',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF475569),
                  ),
                ),
                const Text(
                  '(Heuristic uncalibrated score)',
                  style: TextStyle(fontSize: 10, color: Color(0xFF94A3B8)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Phase 7 Uncertainty Heuristic Notice
          if (isUncertain) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF3C7),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFFCD34D)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.warning_amber_rounded, size: 20, color: Color(0xFFB45309)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'High Prediction Uncertainty',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFFB45309),
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          result.uncertaintyReason ??
                              'Confidence score is below recommended threshold.',
                          style: const TextStyle(fontSize: 11, color: Color(0xFF92400E)),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Inspector Action: Conduct secondary manual review before sorting lot.',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF78350F),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Probability Distribution Bars
          const Text(
            'Ripeness Distribution',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: Color(0xFF334155),
            ),
          ),
          const SizedBox(height: 10),

          ...AppConfig.guavaClasses.map((className) {
            final score = result.probabilities[className] ?? 0.0;
            final isPredicted = result.predictedClass.toLowerCase() == className.toLowerCase();

            return Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        className,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: isPredicted ? FontWeight.bold : FontWeight.normal,
                          color: isPredicted ? const Color(0xFF1E293B) : const Color(0xFF64748B),
                        ),
                      ),
                      Text(
                        '${(score * 100).toStringAsFixed(1)}%',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: isPredicted ? FontWeight.bold : FontWeight.normal,
                          color: isPredicted ? _getClassColor(className) : const Color(0xFF64748B),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: score,
                      minHeight: 6,
                      backgroundColor: const Color(0xFFE2E8F0),
                      valueColor: AlwaysStoppedAnimation<Color>(
                        _getClassColor(className),
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),

          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () {
                setState(() {
                  _selectedImage = null;
                  _imageBytes = null;
                  _predictionResult = null;
                  _errorMessage = null;
                });
              },
              icon: const Icon(Icons.refresh, size: 16),
              label: const Text('Inspect Another Sample'),
            ),
          ),
        ],
      ),
    );
  }
}
