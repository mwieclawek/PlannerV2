import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/providers.dart';

class BugReportDialog extends ConsumerStatefulWidget {
  const BugReportDialog({super.key});

  @override
  ConsumerState<BugReportDialog> createState() => _BugReportDialogState();
}

class _BugReportDialogState extends ConsumerState<BugReportDialog> {
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _stepsController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _stepsController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_titleController.text.trim().isEmpty ||
        _descriptionController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Wypełnij tytuł i opis')),
      );
      return;
    }

    setState(() => _submitting = true);
    try {
      final api = ref.read(apiServiceProvider);
      final result = await api.submitBugReport(
        title: _titleController.text.trim(),
        description: _descriptionController.text.trim(),
        steps: _stepsController.text.trim(),
      );

      if (mounted) {
        Navigator.of(context).pop();
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            icon: Icon(Icons.check_circle, color: Colors.green.shade600, size: 48),
            title: const Text('Zgłoszenie wysłane!'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Zgłoszenie #${result['issue_number']} zostało utworzone.'),
                const SizedBox(height: 12),
                TextButton.icon(
                  onPressed: () {
                    final url = result['issue_url'] as String?;
                    if (url != null) {
                      launchUrl(Uri.parse(url));
                    }
                  },
                  icon: const Icon(Icons.open_in_new, size: 16),
                  label: const Text('Otwórz w GitHub'),
                ),
              ],
            ),
            actions: [
              FilledButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Błąd wysyłania: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Dialog(
      insetPadding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 500),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.bug_report, color: theme.colorScheme.error),
                  const SizedBox(width: 8),
                  Text(
                    'Zgłoś błąd',
                    style: GoogleFonts.outfit(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Zgłoszenie zostanie przesłane do zespołu deweloperskiego',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
              const SizedBox(height: 20),
              TextField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'Tytuł *',
                  hintText: 'Np. "Grafik nie wyświetla się po zalogowaniu"',
                ),
                textInputAction: TextInputAction.next,
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _descriptionController,
                decoration: const InputDecoration(
                  labelText: 'Opis problemu *',
                  hintText: 'Opisz co się dzieje i czego oczekujesz',
                  alignLabelWithHint: true,
                ),
                maxLines: 4,
                textInputAction: TextInputAction.next,
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _stepsController,
                decoration: const InputDecoration(
                  labelText: 'Kroki do odtworzenia (opcjonalne)',
                  hintText: '1. Zaloguj się\n2. Przejdź do...\n3. ...',
                  alignLabelWithHint: true,
                ),
                maxLines: 3,
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _submitting ? null : _submit,
                  icon: _submitting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.send),
                  label: Text(_submitting ? 'Wysyłanie...' : 'Wyślij zgłoszenie'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
