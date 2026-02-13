import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../providers/config_provider.dart';

class QrConfigDialog extends ConsumerWidget {
  const QrConfigDialog({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    debugPrint('Building QrConfigDialog...');
    final baseUrl = ref.watch(configProvider);
    
    // Create the JSON string for the QR code
    final configJson = jsonEncode({'apiUrl': baseUrl});
    debugPrint('QR Data: $configJson');

    return AlertDialog(
      title: const Text('Konfiguracja Serwera'),
      content: SizedBox(
        width: 300,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Pracownicy mogą zeskanować ten kod, aby automatycznie skonfigurować aplikację.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 20),
            if (baseUrl != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: SizedBox(
                  width: 200,
                  height: 200,
                  // Simplified rendering for Web stability
                  child: QrImageView(
                    data: configJson,
                    version: QrVersions.auto,
                    size: 200.0,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              SelectableText(
                baseUrl,
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: baseUrl));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Skopiowano do schowka!')),
                  );
                },
                icon: const Icon(Icons.copy, size: 18),
                label: const Text('Kopiuj adres'),
              ),
            ] else 
              const Text('Błąd: Brak skonfigurowanego adresu URL.'),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Zamknij'),
        ),
      ],
    );
  }
}
