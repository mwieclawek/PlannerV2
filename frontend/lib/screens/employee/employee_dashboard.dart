import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:intl/intl.dart';
import 'package:dio/dio.dart';
import '../../services/google_auth_stub.dart'
    if (dart.library.js_interop) '../../services/google_auth_web.dart';
import '../../providers/providers.dart';
import '../../widgets/availability_grid.dart';
import 'my_schedule_screen.dart';
import 'attendance_tab.dart';
import 'employee_giveaway_tab.dart';
import 'leave_requests_tab.dart';
import 'employee_operations_tab.dart';
import '../../widgets/help_dialog.dart';
import '../../widgets/notification_bell.dart';
import '../../widgets/hover_sidebar_scaffold.dart';
import '../../providers/module_provider.dart';
import '../../utils/api_error_handler.dart';

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

  Future<void> _showMyAccountDialog() async {
    final api = ref.read(apiServiceProvider);
    var user = await ref.read(authProvider.notifier).refreshUser() ??
        ref.read(currentUserProvider).valueOrNull;
    if (user == null || !mounted) return;

    final emailController = TextEditingController(text: user.email ?? '');
    bool isSaving = false;

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          final current = user!;
          final rolesText = current.jobRoleNames.isNotEmpty
              ? current.jobRoleNames.join(', ')
              : (current.jobRoleIds.isNotEmpty
                  ? 'Przypisane (${current.jobRoleIds.length})'
                  : 'Brak przypisanych ról');
          final rateText = current.hourlyRate != null && current.hourlyRate! > 0
              ? '${current.hourlyRate!.toStringAsFixed(2)} PLN / h'
              : 'Domyślna dla roli / nieokreślona';
          final targetHoursText = current.targetHoursPerMonth != null
              ? '${current.targetHoursPerMonth} h / mies.'
              : 'Brak limitu';
          final targetShiftsText = current.targetShiftsPerMonth != null
              ? '${current.targetShiftsPerMonth} zmian / mies.'
              : 'Brak limitu';

          Widget infoRow(IconData icon, String label, String value) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(icon, size: 18, color: Theme.of(ctx).colorScheme.primary),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          label,
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.grey.shade600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          value,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }

          return AlertDialog(
            title: Row(
              children: [
                Icon(Icons.account_circle, color: Theme.of(ctx).colorScheme.primary),
                const SizedBox(width: 8),
                const Text('Moje konto'),
              ],
            ),
            content: SizedBox(
              width: 420,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Dane w systemie',
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: Theme.of(ctx).colorScheme.primary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Theme.of(ctx).colorScheme.surfaceContainerLow,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: Theme.of(ctx).colorScheme.outlineVariant,
                        ),
                      ),
                      child: Column(
                        children: [
                          infoRow(Icons.badge_outlined, 'Imię i nazwisko', current.fullName),
                          const Divider(height: 8),
                          infoRow(Icons.person_outline, 'Login', current.username),
                          const Divider(height: 8),
                          infoRow(
                            Icons.storefront_outlined,
                            'Restauracja',
                            current.tenantName != null
                                ? '${current.tenantName} (${current.tenantSlug ?? "-"})'
                                : (current.tenantSlug ?? 'Domyślna'),
                          ),
                          const Divider(height: 8),
                          infoRow(Icons.work_outline, 'Stanowiska / Role', rolesText),
                          const Divider(height: 8),
                          infoRow(Icons.payments_outlined, 'Stawka godzinowa', rateText),
                          const Divider(height: 8),
                          infoRow(Icons.schedule_outlined, 'Cel godzinowy', targetHoursText),
                          const Divider(height: 8),
                          infoRow(Icons.event_note_outlined, 'Cel zmian', targetShiftsText),
                          const Divider(height: 8),
                          infoRow(
                            Icons.calendar_today_outlined,
                            'Konto utworzone',
                            DateFormat('dd.MM.yyyy').format(current.createdAt.toLocal()),
                          ),
                          const Divider(height: 8),
                          infoRow(
                            Icons.sync_outlined,
                            'Kalendarz Google',
                            current.isGoogleCalendarConnected ? 'Połączony' : 'Niepołączony',
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 18),
                    Text(
                      'Adres e-mail',
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: Theme.of(ctx).colorScheme.primary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    TextField(
                      controller: emailController,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(
                        labelText: 'Twój adres email',
                        hintText: 'np. jan.kowalski@example.com',
                        prefixIcon: Icon(Icons.email_outlined),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: FilledButton.tonalIcon(
                            onPressed: isSaving
                                ? null
                                : () async {
                                    setDialogState(() => isSaving = true);
                                    try {
                                      final updated = await api.updateMyProfile(
                                        email: emailController.text.trim(),
                                      );
                                      ref.invalidate(currentUserProvider);
                                      await ref.read(authProvider.notifier).refreshUser();
                                      setDialogState(() {
                                        user = updated;
                                        isSaving = false;
                                      });
                                      if (mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          const SnackBar(
                                            content: Text('Adres email został zaktualizowany'),
                                            backgroundColor: Colors.green,
                                          ),
                                        );
                                      }
                                    } catch (e) {
                                      setDialogState(() => isSaving = false);
                                      if (mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                            content: Text(
                                              'Błąd: ${ApiErrorHandler.extractMessage(e)}',
                                            ),
                                            backgroundColor: Colors.red,
                                          ),
                                        );
                                      }
                                    }
                                  },
                            icon: isSaving
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.save_outlined, size: 18),
                            label: const Text('Zapisz email'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton.icon(
                          onPressed: () {
                            Navigator.pop(ctx);
                            _showChangePasswordDialog();
                          },
                          icon: const Icon(Icons.lock_outline, size: 18),
                          label: const Text('Zmień hasło'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Zamknij'),
              ),
            ],
          );
        },
      ),
    );
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
                            helperText: 'Min. 8 znaków, cyfra i wielka litera',
                          ),
                          obscureText: true,
                          validator: ApiErrorHandler.validatePassword,
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
                                          content: Text(
                                            'Błąd: ${ApiErrorHandler.extractMessage(e)}',
                                          ),
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
                        if (!isConnected && data['message'] != null) {
                          error = data['message'];
                        }
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
                  if (!isLoading && !isSigningIn)
                    if (isConnected) ...[
                      OutlinedButton.icon(
                        onPressed: () async {
                          setDialogState(() => isLoading = true);
                          try {
                            await ref
                                .read(apiServiceProvider)
                                .disconnectGoogleCalendar();
                            setDialogState(() {
                              isConnected = false;
                              isLoading = false;
                              error = null;
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
                              error = 'Błąd: ${ApiErrorHandler.extractMessage(e)}';
                            });
                          }
                        },
                        icon: const Icon(Icons.link_off, size: 18),
                        label: const Text('Odłącz'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.red,
                        ),
                      ),
                      FilledButton.icon(
                        onPressed: () async {
                          setDialogState(() => isLoading = true);
                          try {
                            final res = await ref
                                .read(apiServiceProvider)
                                .syncGoogleCalendar();
                            setDialogState(() => isLoading = false);
                            final status = res['status'];
                            final count = res['synced'] ?? 0;
                            final total = res['total'] ?? 0;
                            final msg = res['message'];
                            final needsReauth = res['needs_reauth'] == true;

                            if (status == 'error' || needsReauth) {
                              setDialogState(() {
                                if (needsReauth) {
                                  isConnected = false;
                                }
                                error = msg ?? 'Błąd synchronizacji z Kalendarzem Google';
                              });
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(msg ?? 'Błąd synchronizacji z Kalendarzem Google'),
                                    backgroundColor: Colors.red,
                                  ),
                                );
                              }
                            } else if (count == 0 && total > 0) {
                              setDialogState(() {
                                error = msg ?? 'Nie udało się zsynchronizować żadnej z $total zmian';
                              });
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(msg ?? 'Nie udało się zsynchronizować żadnej z $total zmian z Kalendarzem Google'),
                                    backgroundColor: Colors.orange,
                                  ),
                                );
                              }
                            } else if (count == 0 && total == 0) {
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(msg ?? 'Brak opublikowanych zmian do zsynchronizowania'),
                                    backgroundColor: Colors.blueGrey,
                                  ),
                                );
                              }
                            } else {
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      '✓ Zsynchronizowano $count zmian z Kalendarzem Google',
                                    ),
                                    backgroundColor: Colors.green,
                                  ),
                                );
                              }
                            }
                          } catch (e) {
                            setDialogState(() {
                              isLoading = false;
                              error = 'Błąd synchronizacji: ${ApiErrorHandler.extractMessage(e)}';
                            });
                          }
                        },
                        icon: const Icon(Icons.sync, size: 18),
                        label: const Text('Synchronizuj teraz'),
                      ),
                    ] else
                      FilledButton.icon(
                        onPressed: () async {
                          setDialogState(() => isSigningIn = true);
                          try {
                            final googleSignIn = GoogleSignIn(
                              scopes: [
                                'https://www.googleapis.com/auth/calendar.events',
                              ],
                              forceCodeForRefreshToken: true,
                            );

                            String? authCode;
                            try {
                              // On Web, initialize plugin and request offline serverAuthCode (refresh_token)
                              authCode = await requestServerAuthCodeOnWeb(googleSignIn);
                            } catch (_) {
                              authCode = null;
                            }

                            if (authCode == null) {
                              final account = await googleSignIn.signIn();
                              if (account == null) {
                                // User cancelled
                                setDialogState(() => isSigningIn = false);
                                return;
                              }

                              final auth = await account.authentication;
                              authCode =
                                  account.serverAuthCode ?? auth.accessToken;
                            }

                            if (authCode == null) {
                              setDialogState(() {
                                isSigningIn = false;
                                error =
                                    'Nie udało się uzyskać kodu autoryzacji od Google';
                              });
                              return;
                            }

                              // Send auth code to backend
                              final linkRes = await ref
                                  .read(apiServiceProvider)
                                  .connectGoogleCalendar(authCode);

                              setDialogState(() {
                                isSigningIn = false;
                                isConnected = true;
                                error = null;
                              });

                              final synced = linkRes['synced'] ?? 0;
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      '✓ Kalendarz Google połączony. Zsynchronizowano $synced zmian.',
                                    ),
                                    backgroundColor: Colors.green,
                                  ),
                                );
                              }
                            } on DioException catch (e) {
                              setDialogState(() {
                                isSigningIn = false;
                                error = 'Błąd serwera: ${ApiErrorHandler.extractMessage(e)}';
                              });
                            } catch (e) {
                              setDialogState(() {
                                isSigningIn = false;
                                error = 'Błąd logowania Google: ${ApiErrorHandler.extractMessage(e)}';
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
    final openGiveawaysAsync = ref.watch(openGiveawaysCountProvider);
    final openGiveawaysCount = openGiveawaysAsync.valueOrNull ?? 0;

    String appBarTitle = 'Panel Pracownika';
    if (_selectedIndex == 0) appBarTitle = 'Home';
    if (_selectedIndex == 1) appBarTitle = 'Dostępność';
    if (_selectedIndex == 2) appBarTitle = 'Obecność';
    if (_selectedIndex == 3) appBarTitle = 'Giełda';
    if (_selectedIndex == 4) appBarTitle = 'Operacje';

    return HoverSidebarScaffold(
      appBar: AppBar(
        title: Text(
          appBarTitle,
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
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
              } else if (value == 'my_account') {
                _showMyAccountDialog();
              } else if (value == 'password') {
                _showChangePasswordDialog();
              } else if (value == 'google_calendar') {
                _showGoogleCalendarDialog();
              } else if (value == 'pos') {
                ref.read(moduleProvider.notifier).switchModule(AppModule.posKds);
              }
            },
            itemBuilder:
                (BuildContext context) {
              final posEnabled = ref.watch(posEnabledProvider).valueOrNull ?? false;
              return <PopupMenuEntry<String>>[
                if (posEnabled)
                  const PopupMenuItem<String>(
                    value: 'pos',
                    child: Row(
                      children: [
                        Icon(Icons.restaurant, color: Colors.grey),
                        SizedBox(width: 8),
                        Text('Moduł Restauracji/POS'),
                      ],
                    ),
                  ),
                const PopupMenuItem<String>(
                  value: 'my_account',
                  child: Row(
                    children: [
                      Icon(Icons.account_circle, color: Colors.grey),
                      SizedBox(width: 8),
                      Text('Moje konto'),
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
                  value: 'logout',
                  child: Row(
                    children: [
                      Icon(Icons.logout, color: Colors.grey),
                      SizedBox(width: 8),
                      Text('Wyloguj'),
                    ],
                  ),
                ),
              ];
            },
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
            // Home Tab (My Schedule + Unread Announcements + Missing Attendance)
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

          if (_selectedIndex == 4) {
            // Operations & Announcements Tab
            return const EmployeeOperationsTab();
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
      selectedIndex: _selectedIndex,
      onDestinationSelected: (index) {
        setState(() {
          _selectedIndex = index;
        });
      },
      destinations: [
        const HoverSidebarDestination(
          icon: Icon(Icons.home_outlined),
          selectedIcon: Icon(Icons.home),
          label: 'Home',
        ),
        const HoverSidebarDestination(
          icon: Icon(Icons.event_available_outlined),
          selectedIcon: Icon(Icons.event_available),
          label: 'Dostępność',
        ),
        const HoverSidebarDestination(
          icon: Icon(Icons.access_time),
          selectedIcon: Icon(Icons.watch_later),
          label: 'Obecność',
        ),
        HoverSidebarDestination(
          icon:
              openGiveawaysCount > 0
                  ? Badge(
                    label: Text(openGiveawaysCount.toString()),
                    child: const Icon(Icons.swap_horiz),
                  )
                  : const Icon(Icons.swap_horiz),
          selectedIcon:
              openGiveawaysCount > 0
                  ? Badge(
                    label: Text(openGiveawaysCount.toString()),
                    child: const Icon(Icons.swap_horiz),
                  )
                  : const Icon(Icons.swap_horiz),
          label: 'Giełda',
        ),
        const HoverSidebarDestination(
          icon: Icon(Icons.assignment_turned_in_outlined),
          selectedIcon: Icon(Icons.assignment_turned_in),
          label: 'Operacje',
        ),
      ],
    );
  }
}
