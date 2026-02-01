import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class MyScheduleScreen extends ConsumerStatefulWidget {
  const MyScheduleScreen({super.key});

  @override
  ConsumerState<MyScheduleScreen> createState() => _MyScheduleScreenState();
}

class _MyScheduleScreenState extends ConsumerState<MyScheduleScreen> {
  DateTime _selectedWeekStart = _getMonday(DateTime.now());
  bool _isLoading = false;
  List<EmployeeScheduleEntry> _scheduleEntries = [];

  static DateTime _getMonday(DateTime date) {
    return date.subtract(Duration(days: date.weekday - 1));
  }

  DateTime get _selectedWeekEnd => _selectedWeekStart.add(const Duration(days: 6));

  @override
  void initState() {
    super.initState();
    _loadSchedule();
  }

  Future<void> _loadSchedule() async {
    setState(() => _isLoading = true);
    
    try {
      final schedules = await ref.read(apiServiceProvider).getEmployeeSchedule(
        _selectedWeekStart,
        _selectedWeekEnd,
      );
      
      setState(() {
        _scheduleEntries = schedules;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd ładowania: $e')),
        );
      }
    }
  }

  void _previousWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.subtract(const Duration(days: 7));
    });
    _loadSchedule();
  }

  void _nextWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.add(const Duration(days: 7));
    });
    _loadSchedule();
  }

  @override
  Widget build(BuildContext context) {
    // NOTE: No Scaffold here - this is embedded inside EmployeeDashboard which has AppBar
    return _isLoading
        ? const Center(child: CircularProgressIndicator())
        : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  // Week Selector
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.chevron_left),
                            onPressed: _previousWeek,
                          ),
                          Text(
                            '${DateFormat('d MMM', 'pl_PL').format(_selectedWeekStart)} - ${DateFormat('d MMM yyyy', 'pl_PL').format(_selectedWeekEnd)}',
                            style: GoogleFonts.inter(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.chevron_right),
                            onPressed: _nextWeek,
                          ),
                        ],
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 16),
                  
                  // Schedule List
                  if (_scheduleEntries.isEmpty) ...[
                    Center(
                      child: Padding(
                        padding: const EdgeInsets.all(48),
                        child: Column(
                          children: [
                            Icon(
                              Icons.event_busy,
                              size: 64,
                              color: Colors.grey.shade400,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Brak przypisanych zmian',
                              style: GoogleFonts.outfit(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                                color: Colors.grey.shade600,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Grafik nie został jeszcze opublikowany',
                              style: GoogleFonts.inter(
                                fontSize: 14,
                                color: Colors.grey.shade500,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ] else ...[
                    Text(
                      'Twoje zmiany',
                      style: GoogleFonts.outfit(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 12),
                    
                    // Group by date
                    ...(_groupByDate(_scheduleEntries).entries.map((entry) {
                      final date = entry.key;
                      final shifts = entry.value;
                      
                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 12,
                                      vertical: 6,
                                    ),
                                    decoration: BoxDecoration(
                                      color: Colors.teal.shade700,
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      DateFormat('EEE', 'pl_PL').format(date),
                                      style: GoogleFonts.inter(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Text(
                                    DateFormat('d MMMM yyyy', 'pl_PL').format(date),
                                    style: GoogleFonts.inter(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                              const Divider(height: 24),
                              
                              // Shifts for this day
                              ...shifts.map((shift) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(
                                        color: Colors.teal.shade50,
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Icon(
                                        Icons.access_time,
                                        color: Colors.teal.shade700,
                                        size: 24,
                                      ),
                                    ),
                                    const SizedBox(width: 16),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            shift.shiftName,
                                            style: GoogleFonts.inter(
                                              fontSize: 16,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                          const SizedBox(height: 4),
                                          Row(
                                            children: [
                                              Icon(
                                                Icons.schedule,
                                                size: 14,
                                                color: Colors.grey.shade600,
                                              ),
                                              const SizedBox(width: 4),
                                              Text(
                                                '${shift.startTime} - ${shift.endTime}',
                                                style: GoogleFonts.inter(
                                                  fontSize: 14,
                                                  color: Colors.grey.shade600,
                                                ),
                                              ),
                                              const SizedBox(width: 16),
                                              Icon(
                                                Icons.badge,
                                                size: 14,
                                                color: Colors.grey.shade600,
                                              ),
                                              const SizedBox(width: 4),
                                              Text(
                                                shift.roleName,
                                                style: GoogleFonts.inter(
                                                  fontSize: 14,
                                                  color: Colors.grey.shade600,
                                                ),
                                              ),
                                            ],
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              )),
                            ],
                          ),
                        ),
                      );
                    })),
                  ],
                  
                  const SizedBox(height: 16),
                  
                  // Info Card
                  Card(
                    color: Colors.blue.shade50,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          Icon(Icons.info_outline, color: Colors.blue.shade700),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'Wyświetlane są tylko opublikowane grafiki. Jeśli nie widzisz zmian, skontaktuj się z managerem.',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: Colors.blue.shade900,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            );

  }


  Map<DateTime, List<EmployeeScheduleEntry>> _groupByDate(List<EmployeeScheduleEntry> entries) {
    final Map<DateTime, List<EmployeeScheduleEntry>> grouped = {};
    
    for (var entry in entries) {
      final dateKey = DateTime(entry.date.year, entry.date.month, entry.date.day);
      if (!grouped.containsKey(dateKey)) {
        grouped[dateKey] = [];
      }
      grouped[dateKey]!.add(entry);
    }
    
    // Sort by date
    final sortedKeys = grouped.keys.toList()..sort();
    final sortedMap = <DateTime, List<EmployeeScheduleEntry>>{};
    for (var key in sortedKeys) {
      sortedMap[key] = grouped[key]!;
    }
    
    return sortedMap;
  }
}
