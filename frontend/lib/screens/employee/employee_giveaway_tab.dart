import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';

class EmployeeGiveawayTab extends ConsumerStatefulWidget {
  const EmployeeGiveawayTab({super.key});

  @override
  ConsumerState<EmployeeGiveawayTab> createState() =>
      _EmployeeGiveawayTabState();
}

class _EmployeeGiveawayTabState extends ConsumerState<EmployeeGiveawayTab> {
  List<Map<String, dynamic>> _giveaways = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await ref.read(apiServiceProvider).getEmployeeGiveaways();
      setState(() {
        _giveaways = data;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _claim(Map<String, dynamic> g) async {
    // Show confirm dialog
    final confirm = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Wziąć zmianę?'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${g['shift_name'] ?? ''} — ${g['date'] ?? ''}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Text('${g['start_time']} – ${g['end_time']}'),
                const SizedBox(height: 8),
                Text(
                  'Od: ${g['offered_by_name'] ?? ''}',
                  style: TextStyle(color: Colors.grey.shade600),
                ),
                if (g['conflict_type'] == 'same_day') ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade50,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.orange.shade200),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          Icons.warning,
                          color: Colors.orange.shade700,
                          size: 18,
                        ),
                        const SizedBox(width: 8),
                        const Expanded(
                          child: Text(
                            'Masz już inną zmianę w tym dniu (godziny się nie nakładają).',
                            style: TextStyle(fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Anuluj'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Weź zmianę'),
              ),
            ],
          ),
    );
    if (confirm != true) return;

    try {
      await ref.read(apiServiceProvider).claimGiveaway(g['id'] as String);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✓ Zmiana dodana do Twojego grafiku'),
            backgroundColor: Colors.green,
          ),
        );
      }
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Color _conflictColor(String? ct) {
    switch (ct) {
      case 'overlap':
        return Colors.red.shade700;
      case 'same_day':
        return Colors.orange.shade700;
      default:
        return Colors.green.shade700;
    }
  }

  IconData _conflictIcon(String? ct) {
    switch (ct) {
      case 'overlap':
        return Icons.block;
      case 'same_day':
        return Icons.warning_amber;
      default:
        return Icons.check_circle_outline;
    }
  }

  String _conflictLabel(String? ct) {
    switch (ct) {
      case 'overlap':
        return 'Masz już zmianę w tym czasie';
      case 'same_day':
        return 'Masz zmianę w tym dniu';
      default:
        return 'Brak konfliktu';
    }
  }

  String? _availabilityHint(String? hint) {
    if (hint == null) return null;
    if (hint == 'AVAILABLE') return 'Złożyłeś dyspozycyjność: Chcę pracować ✓';
    if (hint == 'UNAVAILABLE') return 'Złożyłeś dyspozycyjność: Nie mogę';
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    if (_loading) return const Center(child: CircularProgressIndicator());

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 48, color: colorScheme.error),
            const SizedBox(height: 12),
            Text(_error!, style: theme.textTheme.bodySmall),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _load,
              icon: const Icon(Icons.refresh),
              label: const Text('Ponów'),
            ),
          ],
        ),
      );
    }

    if (_giveaways.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.swap_horiz,
              size: 64,
              color: colorScheme.outline.withOpacity(0.4),
            ),
            const SizedBox(height: 16),
            Text(
              'Brak zmian do wzięcia',
              style: theme.textTheme.titleMedium?.copyWith(
                color: colorScheme.outline,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Gdy ktoś odda zmianę, pojawi się tutaj',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.outline,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _giveaways.length,
        itemBuilder: (context, index) {
          final g = _giveaways[index];
          final conflictType = g['conflict_type'] as String?;
          final isBlocked = conflictType == 'overlap';
          final availHint = _availabilityHint(
            g['availability_hint'] as String?,
          );

          return Card(
            margin: const EdgeInsets.only(bottom: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side:
                  isBlocked
                      ? BorderSide(color: Colors.red.shade200, width: 1.5)
                      : conflictType == 'same_day'
                      ? BorderSide(color: Colors.orange.shade200, width: 1.5)
                      : BorderSide.none,
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        backgroundColor: colorScheme.primaryContainer,
                        child: Icon(
                          Icons.swap_horiz,
                          color: colorScheme.onPrimaryContainer,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${g['shift_name'] ?? ''} · ${g['role_name'] ?? ''}',
                              style: GoogleFonts.inter(
                                fontWeight: FontWeight.w600,
                                fontSize: 14,
                              ),
                            ),
                            Text(
                              '${_formatDate(g['date'] as String?)}  ${g['start_time']} – ${g['end_time']}',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: colorScheme.outline,
                              ),
                            ),
                            Text(
                              'Od: ${g['offered_by_name'] ?? ''}',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                color: colorScheme.outline,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),

                  // Conflict badge
                  Row(
                    children: [
                      Icon(
                        _conflictIcon(conflictType),
                        size: 14,
                        color: _conflictColor(conflictType),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        _conflictLabel(conflictType),
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: _conflictColor(conflictType),
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),

                  // Availability hint
                  if (availHint != null) ...[
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(
                          Icons.info_outline,
                          size: 13,
                          color:
                              availHint.contains('Chcę')
                                  ? Colors.green.shade600
                                  : Colors.grey.shade600,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          availHint,
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            color:
                                availHint.contains('Chcę')
                                    ? Colors.green.shade600
                                    : Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ),
                  ],

                  const SizedBox(height: 10),

                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: isBlocked ? null : () => _claim(g),
                      icon: Icon(
                        isBlocked ? Icons.block : Icons.add_task,
                        size: 16,
                      ),
                      label: Text(
                        isBlocked
                            ? 'Nie możesz wziąć tej zmiany'
                            : 'Weź zmianę',
                      ),
                      style: FilledButton.styleFrom(
                        backgroundColor:
                            isBlocked
                                ? Colors.grey.shade300
                                : conflictType == 'same_day'
                                ? Colors.orange
                                : colorScheme.primary,
                        foregroundColor:
                            isBlocked ? Colors.grey.shade600 : Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  String _formatDate(String? isoDate) {
    if (isoDate == null) return '';
    try {
      final d = DateTime.parse(isoDate);
      return DateFormat('EEEE, d MMM', 'pl_PL').format(d);
    } catch (_) {
      return isoDate;
    }
  }
}
