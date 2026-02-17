import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';
import '../../widgets/availability_grid.dart';
import 'my_schedule_screen.dart';
import 'attendance_tab.dart';
import '../../widgets/help_dialog.dart';

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

  void _showChangePasswordDialog() {
    final oldPasswordController = TextEditingController();
    final newPasswordController = TextEditingController();
    final confirmPasswordController = TextEditingController();
    final formKey = GlobalKey<FormState>();
    bool isLoading = false;

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Zmiana hasła'),
          content: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: oldPasswordController,
                  decoration: const InputDecoration(labelText: 'Stare hasło'),
                  obscureText: true,
                  validator: (v) => v?.isEmpty == true ? 'Wymagane' : null,
                ),
                TextFormField(
                  controller: newPasswordController,
                  decoration: const InputDecoration(labelText: 'Nowe hasło'),
                  obscureText: true,
                  validator: (v) => (v?.length ?? 0) < 6 ? 'Min. 6 znaków' : null,
                ),
                TextFormField(
                  controller: confirmPasswordController,
                  decoration: const InputDecoration(labelText: 'Powtórz nowe hasło'),
                  obscureText: true,
                  validator: (v) => v != newPasswordController.text ? 'Hasła nie pasują' : null,
                ),
                if (isLoading)
                  const Padding(
                    padding: EdgeInsets.only(top: 16),
                    child: CircularProgressIndicator(),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: isLoading ? null : () => Navigator.pop(context),
              child: const Text('Anuluj'),
            ),
            FilledButton(
              onPressed: isLoading ? null : () async {
                if (formKey.currentState!.validate()) {
                  setDialogState(() => isLoading = true);
                  try {
                    await ref.read(apiServiceProvider).changePassword(
                      oldPasswordController.text,
                      newPasswordController.text,
                    );
                    if (mounted) {
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Hasło zostało zmienione'), backgroundColor: Colors.green),
                      );
                    }
                  } catch (e) {
                    setDialogState(() => isLoading = false);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red),
                      );
                    }
                  }
                }
              },
              child: const Text('Zmień'),
            ),
          ],
        ),
      ),
    );
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
            icon: const Icon(Icons.help_outline),
            tooltip: 'Pomoc',
            onPressed: () {
              showDialog(
                context: context,
                builder: (_) => const HelpDialog(),
              );
            },
          ),
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'logout') {
                await ref.read(authProvider.notifier).logout();
              } else if (value == 'password') {
                _showChangePasswordDialog();
              }
            },
            itemBuilder: (BuildContext context) => <PopupMenuEntry<String>>[
              const PopupMenuItem<String>(
                value: 'password',
                child: Row(
                  children: [
                    Icon(Icons.lock, color: Colors.grey),
                    SizedBox(width: 8),
                    Text('Zmień hasło'),
                  ],
                ),
              ),
              const PopupMenuItem<String>(
                value: 'logout',
                child: Row(
                  children: [
                    Icon(Icons.logout, color: Colors.grey),
                    SizedBox(width: 8),
                    Text('Wyloguj'),
                  ],
                ),
              ),
            ],
            child: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Icon(Icons.person),
            ),
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
