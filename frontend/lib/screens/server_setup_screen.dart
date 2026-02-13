import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:permission_handler/permission_handler.dart';
import '../providers/config_provider.dart';

class ServerSetupScreen extends ConsumerStatefulWidget {
  const ServerSetupScreen({super.key});

  @override
  ConsumerState<ServerSetupScreen> createState() => _ServerSetupScreenState();
}

class _ServerSetupScreenState extends ConsumerState<ServerSetupScreen> with WidgetsBindingObserver {
  final MobileScannerController _scannerController = MobileScannerController(
    detectionSpeed: DetectionSpeed.noDuplicates,
    returnImage: false,
  );
  bool _isCameraPermissionGranted = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _checkCameraPermission();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _scannerController.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (!_scannerController.value.isInitialized) {
      return;
    }
    if (state == AppLifecycleState.inactive) {
      _scannerController.stop();
    } else if (state == AppLifecycleState.resumed) {
      _scannerController.start();
    }
  }

  Future<void> _checkCameraPermission() async {
    final status = await Permission.camera.request();
    setState(() {
      _isCameraPermissionGranted = status.isGranted;
    });
  }

  void _onDetect(BarcodeCapture capture) {
    final List<Barcode> barcodes = capture.barcodes;
    for (final barcode in barcodes) {
      if (barcode.rawValue != null) {
        _process(barcode.rawValue!);
        break; // Process only the first valid code
      }
    }
  }

  void _process(String data) {
    try {
      // Try to parse JSON
      final json = jsonDecode(data);
      if (json is Map && json.containsKey('apiUrl')) {
        final url = json['apiUrl'] as String;
        _validateAndSave(url);
      } else {
        _showError('Invalid QR Code format. Expected JSON with "apiUrl".');
      }
    } catch (e) {
      // Not JSON? Maybe just a raw URL?
      if (data.startsWith('http')) {
        _validateAndSave(data);
      } else {
        _showError('Invalid data format.');
      }
    }
  }

  void _validateAndSave(String url) async {
    if (url.isEmpty) return;
    
    // Basic validation
    final uri = Uri.tryParse(url);
    if (uri == null || !uri.hasScheme || !uri.hasAuthority) {
      _showError('Invalid URL.');
      return;
    }

    try {
      // Pause scanner while validating/saving
      await _scannerController.stop();
      
      await ref.read(configProvider.notifier).setBaseUrl(url);
      
      if (mounted) {
        // Router will handle redirection
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Server configured successfully!')),
        );
      }
    } catch (e) {
      _showError('Failed to save configuration.');
      _scannerController.start();
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  void _showManualEntryDialog() {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Enter Server URL'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            hintText: 'https://example.com',
            labelText: 'API URL',
            border: OutlineInputBorder(),
          ),
          keyboardType: TextInputType.url,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(context);
              _validateAndSave(controller.text.trim());
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Connect to Server')),
      body: Column(
        children: [
          Expanded(
            child: _isCameraPermissionGranted
                ? MobileScanner(
                    controller: _scannerController,
                    onDetect: _onDetect,
                  )
                : Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.camera_alt_outlined, size: 64, color: Colors.grey),
                        const SizedBox(height: 16),
                        const Text('Camera permission required'),
                        TextButton(
                          onPressed: _checkCameraPermission,
                          child: const Text('Grant Permission'),
                        ),
                      ],
                    ),
                  ),
          ),
          Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              children: [
                const Text(
                  'Scan the QR code provided by your administrator',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 16),
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: _showManualEntryDialog,
                  icon: const Icon(Icons.keyboard),
                  label: const Text('Enter URL Manually'),
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(double.infinity, 48),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
