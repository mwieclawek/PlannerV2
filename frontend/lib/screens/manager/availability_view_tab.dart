import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';

class AvailabilityViewTab extends ConsumerStatefulWidget {
  const AvailabilityViewTab({super.key});

  @override
  ConsumerState<AvailabilityViewTab> createState() => _AvailabilityViewTabState();
}

class _AvailabilityViewTabState extends ConsumerState<AvailabilityViewTab> {
  DateTime _selectedWeekStart = _getMonday(DateTime.now());
  List<TeamAvailability>? _availabilities;
  List<ShiftDefinition>? _shifts;
  bool _isLoading = true;
  String? _error;

  static DateTime _getMonday(DateTime date) {
    return date.subtract(Duration(days: date.weekday - 1));
  }

  DateTime get _selectedWeekEnd => _selectedWeekStart.add(const Duration(days: 6));

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = ref.read(apiServiceProvider);
      final availabilities = await api.getTeamAvailability(_selectedWeekStart, _selectedWeekEnd);
      final shifts = await api.getShifts();
      
      setState(() {
        _availabilities = availabilities;
        _shifts = shifts;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _previousWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.subtract(const Duration(days: 7));
    });
    _loadData();
  }

  void _nextWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.add(const Duration(days: 7));
    });
    _loadData();
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'AVAILABLE':
        return Colors.green.shade400;
      case 'UNAVAILABLE':
      default:
        return Colors.red.shade400;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Week Selector
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
            border: Border(bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              IconButton(
                icon: const Icon(Icons.chevron_left),
                onPressed: _previousWeek,
              ),
              Text(
                '${DateFormat('d MMM', 'pl_PL').format(_selectedWeekStart)} - ${DateFormat('d MMM yyyy', 'pl_PL').format(_selectedWeekEnd)}',
                style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w600),
              ),
              IconButton(
                icon: const Icon(Icons.chevron_right),
                onPressed: _nextWeek,
              ),
            ],
          ),
        ),

        // Content
        Expanded(
          child: _buildContent(),
        ),
      ],
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red.shade300),
            const SizedBox(height: 16),
            Text('Błąd: $_error'),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _loadData, child: const Text('Ponów')),
          ],
        ),
      );
    }

    if (_availabilities == null || _availabilities!.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.event_busy, size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            Text(
              'Brak danych o dostępności',
              style: GoogleFonts.inter(fontSize: 16, color: Colors.grey.shade600),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _availabilities!.length,
      itemBuilder: (context, index) {
        final teamAv = _availabilities![index];
        return _buildUserCard(teamAv);
      },
    );
  }

  Widget _buildUserCard(TeamAvailability teamAv) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              teamAv.userName,
              style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            
            // Week grid
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: List.generate(7, (dayIndex) {
                  final date = _selectedWeekStart.add(Duration(days: dayIndex));
                  final dateStr = date.toIso8601String().split('T')[0];
                  final dayEntries = teamAv.entries.where((e) => e.date == dateStr).toList();
                  
                  return Container(
                    width: 80,
                    margin: const EdgeInsets.only(right: 8),
                    child: Column(
                      children: [
                        Text(
                          DateFormat('EEE', 'pl_PL').format(date),
                          style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 12),
                        ),
                        Text(
                          DateFormat('d', 'pl_PL').format(date),
                          style: GoogleFonts.inter(fontSize: 10, color: Colors.grey),
                        ),
                        const SizedBox(height: 8),
                        if (_shifts != null)
                          ..._shifts!.map((shift) {
                            final entry = dayEntries.firstWhere(
                              (e) => e.shiftDefId == shift.id,
                              orElse: () => AvailabilityEntry(date: dateStr, shiftDefId: shift.id, status: 'UNAVAILABLE'),
                            );
                            return Container(
                              height: 24,
                              margin: const EdgeInsets.only(bottom: 2),
                              decoration: BoxDecoration(
                                color: _getStatusColor(entry.status),
                                borderRadius: BorderRadius.circular(4),
                              ),
                            );
                          }),
                      ],
                    ),
                  );
                }),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
