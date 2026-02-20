import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class GiveawayTab extends ConsumerStatefulWidget {
  const GiveawayTab({super.key});

  @override
  ConsumerState<GiveawayTab> createState() => _GiveawayTabState();
}

class _GiveawayTabState extends ConsumerState<GiveawayTab> {
  List<ShiftGiveaway> _giveaways = [];
  bool _loading = true;
  String? _error;
  // Track which card is expanded
  final Set<String> _expanded = {};

  @override
  void initState() {
    super.initState();
    _loadGiveaways();
  }

  Future<void> _loadGiveaways() async {
    setState(() { _loading = true; _error = null; });
    try {
      final api = ref.read(apiServiceProvider);
      final data = await api.getGiveaways();
      setState(() { _giveaways = data; _loading = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Future<void> _reassign(ShiftGiveaway g, GiveawaySuggestion s) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Potwierdź przydzielenie'),
        content: Text(
          'Przydzielić zmianę ${g.shiftName ?? ""} (${g.date ?? ""}) od ${g.offeredByName} do ${s.fullName}?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Anuluj')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Przydziel'),
          ),
        ],
      ),
    );
    if (confirm != true) return;

    try {
      final api = ref.read(apiServiceProvider);
      await api.reassignGiveaway(g.id, s.userId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Zmiana przydzielona do ${s.fullName}')),
        );
      }
      _loadGiveaways();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _cancel(ShiftGiveaway g) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Anulować oddanie?'),
        content: Text(
          'Anulować oddanie zmiany ${g.shiftName ?? ""} (${g.date ?? ""}) od ${g.offeredByName}?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Nie')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Anuluj oddanie'),
          ),
        ],
      ),
    );
    if (confirm != true) return;

    try {
      final api = ref.read(apiServiceProvider);
      await api.cancelGiveaway(g.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Oddanie anulowane')),
        );
      }
      _loadGiveaways();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Color _availabilityColor(String? status) {
    switch (status) {
      case 'AVAILABLE':
        return Colors.green;
      case 'UNAVAILABLE':
        return Colors.red;
      case 'ALREADY_SCHEDULED':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }

  String _availabilityLabel(String? status) {
    switch (status) {
      case 'AVAILABLE':
        return 'Dostępny';
      case 'UNAVAILABLE':
        return 'Niedostępny';
      case 'ALREADY_SCHEDULED':
        return 'Ma zmianę';
      case 'UNKNOWN':
        return 'Brak danych';
      default:
        return status ?? '?';
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 48, color: colorScheme.error),
            const SizedBox(height: 12),
            Text('Błąd ładowania', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(_error!, style: theme.textTheme.bodySmall),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _loadGiveaways,
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
            Icon(Icons.swap_horiz, size: 64, color: colorScheme.outline.withOpacity(0.4)),
            const SizedBox(height: 16),
            Text(
              'Brak otwartych oddań zmian',
              style: theme.textTheme.titleMedium?.copyWith(color: colorScheme.outline),
            ),
            const SizedBox(height: 8),
            Text(
              'Gdy pracownik odda zmianę, pojawi się tutaj',
              style: theme.textTheme.bodySmall?.copyWith(color: colorScheme.outline),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadGiveaways,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _giveaways.length,
        itemBuilder: (context, index) {
          final g = _giveaways[index];
          final isExpanded = _expanded.contains(g.id);

          return AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            margin: const EdgeInsets.only(bottom: 12),
            child: Card(
              elevation: isExpanded ? 3 : 1,
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () {
                  setState(() {
                    if (isExpanded) {
                      _expanded.remove(g.id);
                    } else {
                      _expanded.add(g.id);
                    }
                  });
                },
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Header row
                      Row(
                        children: [
                          CircleAvatar(
                            backgroundColor: colorScheme.primaryContainer,
                            child: Icon(Icons.swap_horiz, color: colorScheme.onPrimaryContainer),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  g.offeredByName,
                                  style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                                ),
                                Text(
                                  '${g.date ?? "?"} · ${g.shiftName ?? "?"} (${g.startTime ?? ""} - ${g.endTime ?? ""})',
                                  style: theme.textTheme.bodySmall?.copyWith(color: colorScheme.outline),
                                ),
                              ],
                            ),
                          ),
                          // Role chip
                          if (g.roleName != null)
                            Chip(
                              label: Text(g.roleName!, style: const TextStyle(fontSize: 11)),
                              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              visualDensity: VisualDensity.compact,
                            ),
                          const SizedBox(width: 4),
                          Icon(isExpanded ? Icons.expand_less : Icons.expand_more),
                        ],
                      ),

                      // Expanded: suggestion list + cancel button
                      if (isExpanded) ...[
                        const Divider(height: 24),
                        Row(
                          children: [
                            Text(
                              'Sugestie przydzielenia',
                              style: theme.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w600),
                            ),
                            const Spacer(),
                            TextButton.icon(
                              onPressed: () => _cancel(g),
                              icon: const Icon(Icons.close, size: 16),
                              label: const Text('Anuluj oddanie'),
                              style: TextButton.styleFrom(foregroundColor: colorScheme.error),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        if (g.suggestions.isEmpty)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: Text(
                              'Brak dostępnych pracowników z tą rolą',
                              style: theme.textTheme.bodySmall?.copyWith(color: colorScheme.outline),
                            ),
                          )
                        else
                          ...g.suggestions.map((s) => Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Row(
                              children: [
                                Container(
                                  width: 8,
                                  height: 8,
                                  decoration: BoxDecoration(
                                    color: _availabilityColor(s.availabilityStatus),
                                    shape: BoxShape.circle,
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(s.fullName, style: theme.textTheme.bodyMedium),
                                ),
                                Text(
                                  _availabilityLabel(s.availabilityStatus),
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    color: _availabilityColor(s.availabilityStatus),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                SizedBox(
                                  height: 32,
                                  child: FilledButton.tonal(
                                    onPressed: s.availabilityStatus == 'UNAVAILABLE'
                                        ? null
                                        : () => _reassign(g, s),
                                    style: FilledButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(horizontal: 12),
                                      textStyle: const TextStyle(fontSize: 12),
                                    ),
                                    child: const Text('Przydziel'),
                                  ),
                                ),
                              ],
                            ),
                          )),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
