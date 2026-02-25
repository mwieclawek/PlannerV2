import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/providers.dart';
import 'setup_tab.dart';
import 'scheduler_wrapper_tab.dart';
import 'home_tab.dart';
import 'team_tab.dart';
import 'attendance_approval_tab.dart';

import '../../widgets/qr_config_dialog.dart';
import '../../widgets/help_dialog.dart';

class ManagerDashboard extends ConsumerStatefulWidget {
  const ManagerDashboard({super.key});

  @override
  ConsumerState<ManagerDashboard> createState() => _ManagerDashboardState();
}

class _ManagerDashboardState extends ConsumerState<ManagerDashboard> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    final userAsync = ref.watch(authProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Panel Managera',
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.help_outline),
            tooltip: 'Pomoc',
            onPressed: () {
              showDialog(context: context, builder: (_) => const HelpDialog());
            },
          ),
          IconButton(
            icon: const Icon(Icons.qr_code_2),
            tooltip: 'Udostępnij konfigurację',
            onPressed: () {
              showDialog(
                context: context,
                builder: (context) => const QrConfigDialog(),
              );
            },
          ),
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

          return IndexedStack(
            index: _selectedIndex,
            children: const [
              HomeTab(),
              SetupTab(),
              SchedulerWrapperTab(),
              AttendanceApprovalTab(),
              TeamTab(),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Błąd: $error')),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) async {
          // If leaving Grafik tab (index 2) and has unsaved changes, show warning
          if (_selectedIndex == 2 && index != 2) {
            final hasUnsaved = ref.read(hasUnsavedScheduleChangesProvider);
            if (hasUnsaved) {
              final proceed = await showDialog<bool>(
                context: context,
                builder:
                    (ctx) => AlertDialog(
                      title: const Text('Niezapisane zmiany'),
                      content: const Text(
                        'Masz niezapisane zmiany w grafiku. Czy chcesz je odrzucić?',
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(ctx, false),
                          child: const Text('Anuluj'),
                        ),
                        FilledButton(
                          style: FilledButton.styleFrom(
                            backgroundColor: Colors.orange,
                          ),
                          onPressed: () => Navigator.pop(ctx, true),
                          child: const Text('Odrzuć zmiany'),
                        ),
                      ],
                    ),
              );
              if (proceed != true) return;
              ref.read(hasUnsavedScheduleChangesProvider.notifier).state =
                  false;
            }
          }
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Konfiguracja',
          ),
          NavigationDestination(
            icon: Icon(Icons.calendar_month_outlined),
            selectedIcon: Icon(Icons.calendar_month),
            label: 'Grafik',
          ),
          NavigationDestination(
            icon: Icon(Icons.fact_check_outlined),
            selectedIcon: Icon(Icons.fact_check),
            label: 'Obecności',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outlined),
            selectedIcon: Icon(Icons.people),
            label: 'Zespół',
          ),
        ],
      ),
    );
  }
}
