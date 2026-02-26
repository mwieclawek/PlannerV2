import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';
import '../../widgets/availability_grid.dart';
import 'my_schedule_screen.dart';
import 'attendance_tab.dart';
import 'employee_giveaway_tab.dart';
import 'leave_requests_tab.dart';
import '../../widgets/help_dialog.dart';
import '../../widgets/notification_bell.dart';

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

  DateTime get _selectedWeekEnd =>
      _selectedWeekStart.add(const Duration(days: 6));

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
      builder:
          (context) => StatefulBuilder(
            builder:
                (context, setDialogState) => AlertDialog(
                  title: const Text('Zmiana hasła'),
                  content: Form(
                    key: formKey,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        TextFormField(
                          controller: oldPasswordController,
                          decoration: const InputDecoration(
                            labelText: 'Stare hasło',
                          ),
                          obscureText: true,
                          validator:
                              (v) => v?.isEmpty == true ? 'Wymagane' : null,
                        ),
                        TextFormField(
                          controller: newPasswordController,
                          decoration: const InputDecoration(
                            labelText: 'Nowe hasło',
                          ),
                          obscureText: true,
                          validator:
                              (v) =>
                                  (v?.length ?? 0) < 6 ? 'Min. 6 znaków' : null,
                        ),
                        TextFormField(
                          controller: confirmPasswordController,
                          decoration: const InputDecoration(
                            labelText: 'Powtórz nowe hasło',
                          ),
                          obscureText: true,
                          validator:
                              (v) =>
                                  v != newPasswordController.text
                                      ? 'Hasła nie pasują'
                                      : null,
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
                      onPressed:
                          isLoading ? null : () => Navigator.pop(context),
                      child: const Text('Anuluj'),
                    ),
                    FilledButton(
                      onPressed:
                          isLoading
                              ? null
                              : () async {
                                if (formKey.currentState!.validate()) {
                                  setDialogState(() => isLoading = true);
                                  try {
                                    await ref
                                        .read(apiServiceProvider)
                                        .changePassword(
                                          oldPasswordController.text,
                                          newPasswordController.text,
                                        );
                                    if (mounted) {
                                      Navigator.pop(context);
                                      ScaffoldMessenger.of(
                                        context,
                                      ).showSnackBar(
                                        const SnackBar(
                                          content: Text(
                                            'Hasło zostało zmienione',
                                          ),
                                          backgroundColor: Colors.green,
                                        ),
                                      );
                                    }
                                  } catch (e) {
                                    setDialogState(() => isLoading = false);
                                    if (mounted) {
                                      ScaffoldMessenger.of(
                                        context,
                                      ).showSnackBar(
                                        SnackBar(
                                          content: Text('Błąd: $e'),
                                          backgroundColor:
                                              Theme.of(
                                                context,
                                              ).colorScheme.error,
                                        ),
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

  void _showGoogleCalendarDialog() async {
    // Check current status
    bool isConnected = false;
    bool isLoading = true;
    bool isSigningIn = false;
    String? error;

    showDialog(
      context: context,
      builder:
          (context) => StatefulBuilder(
            builder: (context, setDialogState) {
              // Load status on first build
              if (isLoading && !isSigningIn) {
                ref
                    .read(apiServiceProvider)
                    .getGoogleCalendarStatus()
                    .then((data) {
                      setDialogState(() {
                        isConnected = data['connected'] == true;
                        isLoading = false;
                      });
                    })
                    .catchError((e) {
                      // If status endpoint doesn't exist (404), treat as not connected
                      setDialogState(() {
                        isLoading = false;
                        isConnected = false;
                      });
                    });
              }

              return AlertDialog(
                title: Row(
                  children: [
                    Icon(
                      Icons.calendar_month,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                    const Text('Kalendarz Google'),
                  ],
                ),
                content: SizedBox(
                  width: 300,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (isLoading || isSigningIn) ...[
                        Center(
                          child: Column(
                            children: [
                              const CircularProgressIndicator(),
                              if (isSigningIn) ...[
                                const SizedBox(height: 12),
                                Text(
                                  'Logowanie przez Google...',
                                  style: TextStyle(
                                    fontSize: 13,
                                    color: Colors.grey.shade600,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ] else if (error != null) ...[
                        Text(
                          error!,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ] else if (isConnected) ...[
                        Row(
                          children: [
                            Icon(
                              Icons.check_circle,
                              color: Colors.green.shade600,
                              size: 20,
                            ),
                            const SizedBox(width: 8),
                            const Expanded(
                              child: Text('Kalendarz Google jest połączony'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Twoje zmiany są automatycznie synchronizowane z Kalendarzem Google.',
                          style: TextStyle(fontSize: 13, color: Colors.grey),
                        ),
                      ] else ...[
                        Row(
                          children: [
                            Icon(
                              Icons.link_off,
                              color: Colors.grey.shade500,
                              size: 20,
                            ),
                            const SizedBox(width: 8),
                            const Expanded(
                              child: Text(
                                'Kalendarz Google nie jest połączony',
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Połącz swoje konto Google, aby automatycznie dodawać zmiany do kalendarza.',
                          style: TextStyle(fontSize: 13, color: Colors.grey),
                        ),
                      ],
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Zamknij'),
                  ),
                  if (!isLoading && !isSigningIn && error == null)
                    isConnected
                        ? OutlinedButton.icon(
                          onPressed: () async {
                            setDialogState(() => isLoading = true);
                            try {
                              await ref
                                  .read(apiServiceProvider)
                                  .disconnectGoogleCalendar();
                              setDialogState(() {
                                isConnected = false;
                                isLoading = false;
                              });
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Kalendarz Google odłączony'),
                                    backgroundColor: Colors.orange,
                                  ),
                                );
                              }
                            } catch (e) {
                              setDialogState(() {
                                isLoading = false;
                                error = 'Błąd: $e';
                              });
                            }
                          },
                          icon: const Icon(Icons.link_off, size: 18),
                          label: const Text('Odłącz'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.red,
                          ),
                        )
                        : FilledButton.icon(
                          onPressed: () async {
                            setDialogState(() => isSigningIn = true);
                            try {
                              final googleSignIn = GoogleSignIn(
                                scopes: [
                                  'https://www.googleapis.com/auth/calendar.events',
                                ],
                                serverClientId:
                                    '357153331477-b6512tnr51gi4kslrh9f8tjndhdp74j7.apps.googleusercontent.com',
                              );

                              final account = await googleSignIn.signIn();
                              if (account == null) {
                                // User cancelled
                                setDialogState(() => isSigningIn = false);
                                return;
                              }

                              final auth = await account.authentication;
                              final authCode =
                                  auth.serverAuthCode ?? auth.accessToken;

                              if (authCode == null) {
                                setDialogState(() {
                                  isSigningIn = false;
                                  error =
                                      'Nie udało się uzyskać kodu autoryzacji od Google';
                                });
                                return;
                              }

                              // Send auth code to backend
                              await ref
                                  .read(apiServiceProvider)
                                  .connectGoogleCalendar(authCode);

                              setDialogState(() {
                                isSigningIn = false;
                                isConnected = true;
                              });

                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text(
                                      '✓ Kalendarz Google połączony pomyślnie',
                                    ),
                                    backgroundColor: Colors.green,
                                  ),
                                );
                              }
                            } catch (e) {
                              setDialogState(() {
                                isSigningIn = false;
                                error = 'Błąd logowania Google: $e';
                              });
                            }
                          },
                          icon: const Icon(Icons.link, size: 18),
                          label: const Text('Połącz z Google'),
                        ),
                  if (error != null && !isLoading)
                    TextButton(
                      onPressed: () {
                        setDialogState(() {
                          error = null;
                          isLoading = true;
                        });
                      },
                      child: const Text('Spróbuj ponownie'),
                    ),
                ],
              );
            },
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final userAsync = ref.watch(currentUserProvider);
    final shiftsAsync = ref.watch(shiftsProvider);

    String appBarTitle = 'Panel Pracownika';
    if (_selectedIndex == 0) appBarTitle = 'Mój Grafik';
    if (_selectedIndex == 1) appBarTitle = 'Dostępność';
    if (_selectedIndex == 2) appBarTitle = 'Obecność';
    if (_selectedIndex == 3) appBarTitle = 'Giełda';

    return Scaffold(
      appBar: AppBar(
        title: Text(
          appBarTitle,
          style: GoogleFonts.outfit(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Colors.white,
        actions: [
          const NotificationBell(),
          IconButton(
            icon: const Icon(Icons.help_outline),
            tooltip: 'Pomoc',
            onPressed: () {
              showDialog(context: context, builder: (_) => const HelpDialog());
            },
          ),
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'logout') {
                await ref.read(authProvider.notifier).logout();
              } else if (value == 'password') {
                _showChangePasswordDialog();
              } else if (value == 'google_calendar') {
                _showGoogleCalendarDialog();
              }
            },
            itemBuilder:
                (BuildContext context) => <PopupMenuEntry<String>>[
                  const PopupMenuItem<String>(
                    value: 'google_calendar',
                    child: Row(
                      children: [
                        Icon(Icons.calendar_month, color: Colors.grey),
                        SizedBox(width: 8),
                        Text('Kalendarz Google'),
                      ],
                    ),
                  ),
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

          if (_selectedIndex == 3) {
            // Giveaway Tab
            return const EmployeeGiveawayTab();
          }

          // Availability Tab (_selectedIndex == 1)
          return DefaultTabController(
            length: 2,
            child: Column(
              children: [
                const TabBar(
                  tabs: [
                    Tab(text: 'Dyspozycja'),
                    Tab(text: 'Wnioski urlopowe'),
                  ],
                ),
                Expanded(
                  child: TabBarView(
                    children: [
                      // Sub-tab 0: Dyspozycja
                      Column(
                        children: [
                          // Week Selector
                          Container(
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color:
                                  Theme.of(
                                    context,
                                  ).colorScheme.secondaryContainer,
                              border: Border(
                                bottom: BorderSide(
                                  color:
                                      Theme.of(
                                        context,
                                      ).colorScheme.outlineVariant,
                                ),
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
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      children: [
                                        Icon(
                                          Icons.info_outline,
                                          size: 64,
                                          color: Colors.grey.shade400,
                                        ),
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
                              loading:
                                  () => const Center(
                                    child: CircularProgressIndicator(),
                                  ),
                              error:
                                  (error, stack) =>
                                      Center(child: Text('Błąd: $error')),
                            ),
                          ),
                        ],
                      ),

                      // Sub-tab 1: Wnioski urlopowe
                      const LeaveRequestsTab(),
                    ],
                  ),
                ),
              ],
            ),
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
          NavigationDestination(icon: Icon(Icons.swap_horiz), label: 'Giełda'),
        ],
      ),
    );
  }
}
