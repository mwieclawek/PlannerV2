import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class LeaveRequestsTab extends ConsumerStatefulWidget {
  const LeaveRequestsTab({super.key});

  @override
  ConsumerState<LeaveRequestsTab> createState() => _LeaveRequestsTabState();
}

class _LeaveRequestsTabState extends ConsumerState<LeaveRequestsTab> {
  bool _isLoading = false;
  List<LeaveRequest> _requests = [];

  @override
  void initState() {
    super.initState();
    _loadRequests();
  }

  Future<void> _loadRequests() async {
    setState(() => _isLoading = true);
    try {
      final requests = await ref.read(apiServiceProvider).getMyLeaveRequests();
      setState(() {
        _requests = requests;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Błąd pobierania wniosków: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }

  void _showCreateDialog() {
    DateTimeRange? selectedRange;
    final reasonController = TextEditingController();
    bool isSubmitting = false;

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title: const Text('Złóż wniosek urlopowy'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                OutlinedButton.icon(
                  onPressed: () async {
                    final range = await showDateRangePicker(
                      context: context,
                      firstDate: DateTime.now(),
                      lastDate: DateTime.now().add(const Duration(days: 365)),
                    );
                    if (range != null) {
                      setDialogState(() => selectedRange = range);
                    }
                  },
                  icon: const Icon(Icons.date_range),
                  label: Text(
                    selectedRange == null
                        ? 'Wybierz daty'
                        : '${DateFormat('dd.MM.yyyy').format(selectedRange!.start)} - ${DateFormat('dd.MM.yyyy').format(selectedRange!.end)}',
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: reasonController,
                  decoration: const InputDecoration(
                    labelText: 'Powód (opcjonalnie)',
                    border: OutlineInputBorder(),
                  ),
                  maxLines: 3,
                ),
                if (isSubmitting)
                  const Padding(
                    padding: EdgeInsets.only(top: 16),
                    child: Center(child: CircularProgressIndicator()),
                  ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: isSubmitting ? null : () => Navigator.pop(context),
                child: const Text('Anuluj'),
              ),
              FilledButton(
                onPressed: isSubmitting || selectedRange == null
                    ? null
                    : () async {
                        setDialogState(() => isSubmitting = true);
                        try {
                          await ref.read(apiServiceProvider).createLeaveRequest(
                                selectedRange!.start,
                                selectedRange!.end,
                                reasonController.text.trim(),
                              );
                          if (mounted) {
                            Navigator.pop(context);
                            _loadRequests();
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Wniosek został złożony'),
                                backgroundColor: Colors.green,
                              ),
                            );
                          }
                        } catch (e) {
                          setDialogState(() => isSubmitting = false);
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text('Błąd: $e'),
                                backgroundColor: Theme.of(context).colorScheme.error,
                              ),
                            );
                          }
                        }
                      },
                child: const Text('Wyślij'),
              ),
            ],
          );
        },
      ),
    );
  }

  void _cancelRequest(String id) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Anuluj wniosek'),
        content: const Text('Czy na pewno chcesz anulować ten wniosek?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Nie'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(backgroundColor: Theme.of(context).colorScheme.error),
            child: const Text('Tak, anuluj'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    setState(() => _isLoading = true);
    try {
      await ref.read(apiServiceProvider).cancelLeaveRequest(id);
      _loadRequests();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Wniosek anulowany'), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e'), backgroundColor: Theme.of(context).colorScheme.error),
        );
      }
    }
  }

  Widget _buildStatusBadge(String status) {
    MaterialColor color;
    String label;

    switch (status) {
      case 'PENDING':
        color = Colors.amber;
        label = '🟡 Oczekuje';
        break;
      case 'APPROVED':
        color = Colors.green;
        label = '✅ Zaakceptowany';
        break;
      case 'REJECTED':
        color = Colors.red;
        label = '🔴 Odrzucony';
        break;
      case 'CANCELLED':
        color = Colors.grey;
        label = '⚫ Anulowany';
        break;
      default:
        color = Colors.grey;
        label = status;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(
          color: color.shade800,
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Twoje wnioski urlopowe',
                style: GoogleFonts.outfit(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              FilledButton.icon(
                onPressed: _showCreateDialog,
                icon: const Icon(Icons.add),
                label: const Text('Złóż wniosek'),
              ),
            ],
          ),
        ),
        Expanded(
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _requests.isEmpty
                  ? Center(
                      child: Text(
                        'Brak wniosków urlopowych',
                        style: GoogleFonts.inter(color: Colors.grey.shade600, fontSize: 16),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      itemCount: _requests.length,
                      itemBuilder: (context, index) {
                        final req = _requests[index];
                        final startDate = DateTime.parse(req.startDate);
                        final endDate = DateTime.parse(req.endDate);

                        return Card(
                          margin: const EdgeInsets.only(bottom: 12),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                            side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(16.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Row(
                                      children: [
                                        Icon(Icons.calendar_today, size: 18, color: Theme.of(context).colorScheme.primary),
                                        const SizedBox(width: 8),
                                        Text(
                                          '${DateFormat('dd.MM.yyyy').format(startDate)} – ${DateFormat('dd.MM.yyyy').format(endDate)}',
                                          style: GoogleFonts.inter(
                                            fontSize: 16,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ],
                                    ),
                                    _buildStatusBadge(req.status),
                                  ],
                                ),
                                if (req.reason != null && req.reason!.isNotEmpty) ...[
                                  const SizedBox(height: 8),
                                  Text(
                                    'Powód: ${req.reason}',
                                    style: GoogleFonts.inter(color: Colors.grey.shade700),
                                  ),
                                ],
                                if (req.status == 'PENDING') ...[
                                  const SizedBox(height: 12),
                                  Align(
                                    alignment: Alignment.centerRight,
                                    child: OutlinedButton(
                                      onPressed: () => _cancelRequest(req.id),
                                      style: OutlinedButton.styleFrom(
                                        foregroundColor: Theme.of(context).colorScheme.error,
                                        side: BorderSide(color: Theme.of(context).colorScheme.error),
                                      ),
                                      child: const Text('Anuluj'),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        );
                      },
                    ),
        ),
      ],
    );
  }
}
