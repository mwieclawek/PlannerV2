import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';
import '../../widgets/availability_grid.dart';
import 'my_schedule_screen.dart';
import 'attendance_tab.dart';

class EmployeeDashboard extends ConsumerStatefulWidget {
  const EmployeeDashboard({super.key});

  @override
  ConsumerState<EmployeeDashboard> createState() => _EmployeeDashboardState();
}

class _EmployeeDashboardState extends ConsumerState<EmployeeDashboard> {
  DateTime _selectedWeekStart = _getMonday(DateTime.now());
  int _selectedIndex = 0;
  
  static DateTime _getMonday(DateTime date) {
    return date.subtract(Duration(days: date.weekday - 1));
  }

  DateTime get _selectedWeekEnd => _selectedWeekStart.add(const Duration(days: 6));

  void _previousWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.subtract(const Duration(days: 7));
    });
  }

  void _nextWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.add(const Duration(days: 7));
    });
  }

  @override
  Widget build(BuildContext context) {
    final userAsync = ref.watch(authProvider);
    final shiftsAsync = ref.watch(shiftsProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          _selectedIndex == 0 ? 'Mój Grafik' : _selectedIndex == 1 ? 'Moja Dostępność' : 'Obecność',
          style: GoogleFonts.outfit(fontWeight: FontWeight.bold),
        ),
        backgroundColor: _selectedIndex == 0 ? Colors.teal.shade700 : _selectedIndex == 1 ? Colors.blue.shade700 : Colors.purple.shade700,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
            },
          ),
        ],
      ),
      body: userAsync.when(
        data: (user) {
          if (user == null) return const Center(child: Text('Nie zalogowano'));
          
          if (_selectedIndex == 0) {
            // My Schedule Tab
            return const MyScheduleScreen();
          }
          
          if (_selectedIndex == 2) {
            // Attendance Tab
            return const AttendanceTab();
          }
          
          // Availability Tab
          return Column(
            children: [
              // Week Selector
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  border: Border(
                    bottom: BorderSide(color: Colors.blue.shade200),
                  ),
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
              
              // Availability Grid
              Expanded(
                child: shiftsAsync.when(
                  data: (shifts) {
                    if (shifts.isEmpty) {
                      return Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.info_outline, size: 64, color: Colors.grey.shade400),
                            const SizedBox(height: 16),
                            Text(
                              'Brak zdefiniowanych zmian',
                              style: GoogleFonts.inter(
                                fontSize: 16,
                                color: Colors.grey.shade600,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Skontaktuj się z menadżerem',
                              style: GoogleFonts.inter(
                                fontSize: 14,
                                color: Colors.grey.shade500,
                              ),
                            ),
                          ],
                        ),
                      );
                    }
                    
                    return AvailabilityGrid(
                      weekStart: _selectedWeekStart,
                      shifts: shifts,
                    );
                  },
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (error, stack) => Center(
                    child: Text('Błąd: $error'),
                  ),
                ),
              ),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Błąd: $error')),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.calendar_month),
            label: 'Mój Grafik',
          ),
          NavigationDestination(
            icon: Icon(Icons.event_available),
            label: 'Dostępność',
          ),
          NavigationDestination(
            icon: Icon(Icons.access_time),
            label: 'Obecność',
          ),
        ],
      ),
    );
  }
}
