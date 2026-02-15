import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../models/models.dart';
import '../providers/providers.dart';

class AvailabilityGrid extends ConsumerStatefulWidget {
  final DateTime weekStart;
  final List<ShiftDefinition> shifts;

  const AvailabilityGrid({
    super.key,
    required this.weekStart,
    required this.shifts,
  });

  @override
  ConsumerState<AvailabilityGrid> createState() => _AvailabilityGridState();
}

class _AvailabilityGridState extends ConsumerState<AvailabilityGrid> {
  // Local state: Map of (date, shiftId) -> status
  final Map<String, AvailabilityStatus> _localAvailability = {};
  bool _hasChanges = false;

  @override
  void initState() {
    super.initState();
    _loadAvailability();
  }

  @override
  void didUpdateWidget(AvailabilityGrid oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.weekStart != widget.weekStart) {
      _loadAvailability();
    }
  }

  void _loadAvailability() async {
    final weekEnd = widget.weekStart.add(const Duration(days: 6));
    final dateRange = DateRange(widget.weekStart, weekEnd);
    
    try {
      final availabilities = await ref.read(availabilityProvider(dateRange).future);
      
      setState(() {
        _localAvailability.clear();
        for (final avail in availabilities) {
          final key = '${avail.date.toIso8601String().split('T')[0]}_${avail.shiftDefId}';
          _localAvailability[key] = avail.status;
        }
        _hasChanges = false;
      });
    } catch (e) {
      // Handle error
    }
  }

  String _getKey(DateTime date, int shiftId) {
    return '${date.toIso8601String().split('T')[0]}_$shiftId';
  }

  AvailabilityStatus _getStatus(DateTime date, int shiftId) {
    return _localAvailability[_getKey(date, shiftId)] ?? AvailabilityStatus.available;
  }

  void _toggleStatus(DateTime date, int shiftId) {
    final key = _getKey(date, shiftId);
    final currentStatus = _getStatus(date, shiftId);
    
    AvailabilityStatus newStatus;
    switch (currentStatus) {
      case AvailabilityStatus.available:
        newStatus = AvailabilityStatus.preferred;
        break;
      case AvailabilityStatus.preferred:
        newStatus = AvailabilityStatus.neutral;
        break;
      case AvailabilityStatus.neutral:
        newStatus = AvailabilityStatus.unavailable;
        break;
      case AvailabilityStatus.unavailable:
        newStatus = AvailabilityStatus.available;
        break;
    }
    
    setState(() {
      _localAvailability[key] = newStatus;
      _hasChanges = true;
    });
  }

  Future<void> _saveChanges() async {
    final updates = <AvailabilityUpdate>[];
    
    for (int i = 0; i < 7; i++) {
      final date = widget.weekStart.add(Duration(days: i));
      for (final shift in widget.shifts) {
        final status = _getStatus(date, shift.id);
        updates.add(AvailabilityUpdate(
          date: date,
          shiftDefId: shift.id,
          status: status,
        ));
      }
    }
    
    try {
      await ref.read(apiServiceProvider).updateAvailability(updates);
      
      if (mounted) {
        setState(() => _hasChanges = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✓ Dostępność zapisana'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e')),
        );
      }
    }
  }

  Color _getStatusColor(AvailabilityStatus status) {
    switch (status) {
      case AvailabilityStatus.preferred:
        return Colors.green.shade400;
      case AvailabilityStatus.neutral:
        return Colors.amber.shade400;
      case AvailabilityStatus.unavailable:
        return Colors.red.shade400;
      case AvailabilityStatus.available:
        return Colors.red.shade100; // Changed from grey to light red to indicate "unwilling" by default
    }
  }

  IconData _getStatusIcon(AvailabilityStatus status) {
    switch (status) {
      case AvailabilityStatus.preferred:
        return Icons.thumb_up;
      case AvailabilityStatus.neutral:
        return Icons.remove_circle_outline;
      case AvailabilityStatus.unavailable:
        return Icons.block;
      case AvailabilityStatus.available:
        return Icons.close; // Changed icon
    }
  }

  String _getStatusLabel(AvailabilityStatus status) {
    switch (status) {
      case AvailabilityStatus.preferred:
        return 'Chcę';
      case AvailabilityStatus.neutral:
        return 'Mogę';
      case AvailabilityStatus.unavailable:
        return 'Nie mogę';
      case AvailabilityStatus.available:
        return 'Brak (Nie)'; // Changed label
    }
  }

  @override
  Widget build(BuildContext context) {
    final isMobile = MediaQuery.of(context).size.width < 600;
    
    return Column(
      children: [
        // Legend
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: Wrap(
            spacing: 16,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: AvailabilityStatus.values.map((status) {
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(_getStatusIcon(status), color: _getStatusColor(status), size: 20),
                  const SizedBox(width: 4),
                  Text(
                    _getStatusLabel(status),
                    style: GoogleFonts.inter(fontSize: 12),
                  ),
                ],
              );
            }).toList(),
          ),
        ),
        
        // Grid
        Expanded(
          child: isMobile ? _buildMobileView() : _buildDesktopView(),
        ),
        
        // Save Button
        if (_hasChanges)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 8,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: _saveChanges,
                icon: const Icon(Icons.save),
                label: const Text('Zapisz zmiany'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue.shade700,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildMobileView() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: 7,
      itemBuilder: (context, dayIndex) {
        final date = widget.weekStart.add(Duration(days: dayIndex));
        final dayName = DateFormat('EEEE, d MMM', 'pl_PL').format(date);
        
        return Card(
          margin: const EdgeInsets.only(bottom: 16),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  dayName,
                  style: GoogleFonts.outfit(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                ...widget.shifts.map((shift) {
                  final status = _getStatus(date, shift.id);
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: InkWell(
                      onTap: () => _toggleStatus(date, shift.id),
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: _getStatusColor(status),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(_getStatusIcon(status), color: Colors.white),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                shift.name,
                                style: GoogleFonts.inter(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            Text(
                              _getStatusLabel(status),
                              style: GoogleFonts.inter(
                                color: Colors.white,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildDesktopView() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Table(
            border: TableBorder.all(color: Colors.grey.shade300),
            defaultColumnWidth: const FixedColumnWidth(120),
            children: [
              // Header row
              TableRow(
                decoration: BoxDecoration(color: Colors.blue.shade50),
                children: [
                  _buildHeaderCell('Zmiana'),
                  ...List.generate(7, (i) {
                    final date = widget.weekStart.add(Duration(days: i));
                    return _buildHeaderCell(
                      DateFormat('EEE\nd MMM', 'pl_PL').format(date),
                    );
                  }),
                ],
              ),
              // Shift rows
              ...widget.shifts.map((shift) {
                return TableRow(
                  children: [
                    _buildShiftNameCell(shift.name),
                    ...List.generate(7, (i) {
                      final date = widget.weekStart.add(Duration(days: i));
                      final status = _getStatus(date, shift.id);
                      return _buildStatusCell(date, shift.id, status);
                    }),
                  ],
                );
              }),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderCell(String text) {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Text(
        text,
        textAlign: TextAlign.center,
        style: GoogleFonts.outfit(
          fontWeight: FontWeight.bold,
          fontSize: 14,
        ),
      ),
    );
  }

  Widget _buildShiftNameCell(String name) {
    return Container(
      padding: const EdgeInsets.all(12),
      color: Colors.grey.shade100,
      child: Text(
        name,
        style: GoogleFonts.inter(fontWeight: FontWeight.w600),
      ),
    );
  }

  Widget _buildStatusCell(DateTime date, int shiftId, AvailabilityStatus status) {
    return InkWell(
      onTap: () => _toggleStatus(date, shiftId),
      child: Container(
        height: 60,
        color: _getStatusColor(status),
        child: Center(
          child: Icon(
            _getStatusIcon(status),
            color: Colors.white,
            size: 28,
          ),
        ),
      ),
    );
  }
}
