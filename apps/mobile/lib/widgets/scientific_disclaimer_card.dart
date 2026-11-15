import 'package:flutter/material.dart';
import '../config/app_config.dart';

class ScientificDisclaimerCard extends StatelessWidget {
  final bool compact;

  const ScientificDisclaimerCard({super.key, this.compact = false});

  @override
  Widget build(BuildContext context) {
    if (compact) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFFE2E8F0)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.info_outline, size: 16, color: Color(0xFF64748B)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '${AppConfig.softmaxDisclaimer} Visual maturity scope only.',
                style: const TextStyle(
                  fontSize: 11,
                  color: Color(0xFF475569),
                  height: 1.3,
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFCBD5E1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFFE2E8F0),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Icon(Icons.shield_outlined,
                    size: 18, color: Color(0xFF334155)),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(
                  'Academic & Regulatory Notice',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1E293B),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _buildBullet(
            'Uncalibrated Softmax',
            AppConfig.softmaxDisclaimer,
          ),
          const SizedBox(height: 6),
          _buildBullet(
            'Maturity Scope',
            AppConfig.maturityScopeLimitation,
          ),
          const SizedBox(height: 6),
          _buildBullet(
            'Lot-Level Scope',
            AppConfig.batchTrackingScope,
          ),
        ],
      ),
    );
  }

  Widget _buildBullet(String title, String content) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(top: 4),
          child: Icon(Icons.circle, size: 6, color: Color(0xFF64748B)),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: RichText(
            text: TextSpan(
              style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF334155),
                height: 1.35,
              ),
              children: [
                TextSpan(
                  text: '$title: ',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                TextSpan(text: content),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
