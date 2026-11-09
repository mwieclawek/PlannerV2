import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/providers.dart';
import '../../utils/api_error_handler.dart';

class SysAdminDashboardScreen extends ConsumerStatefulWidget {
  const SysAdminDashboardScreen({super.key});

  @override
  ConsumerState<SysAdminDashboardScreen> createState() =>
      _SysAdminDashboardScreenState();
}

class _SysAdminDashboardScreenState extends ConsumerState<SysAdminDashboardScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // State: Restaurants
  List<Map<String, dynamic>> _restaurants = [];
  bool _isLoadingRestaurants = true;

  // State: Logs
  List<Map<String, dynamic>> _logs = [];
  bool _isLoadingLogs = false;
  int _totalLogsCount = 0;
  int? _selectedLogRestaurantId; // null = Wszystkie, 0 = Systemowe, >0 = Konkretna
  String _selectedLogLevel = 'ALL';
  String _selectedLogCategory = 'ALL';
  final TextEditingController _logSearchCtrl = TextEditingController();
  final Set<int> _expandedLogIndices = {};
  int _logOffset = 0;
  final int _logLimit = 150;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (_tabController.index == 1 && _logs.isEmpty && !_isLoadingLogs) {
        _loadLogs();
      }
      setState(() {});
    });
    _loadRestaurants();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _logSearchCtrl.dispose();
    super.dispose();
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  //  RESTOCK / RESTAURANTS LOGIC
  // ═══════════════════════════════════════════════════════════════════════════════

  Future<void> _loadRestaurants() async {
    setState(() => _isLoadingRestaurants = true);
    try {
      final service = ref.read(sysAdminServiceProvider);
      final data = await service.getRestaurants();
      setState(() {
        _restaurants = data;
        _isLoadingRestaurants = false;
      });
    } catch (e) {
      setState(() => _isLoadingRestaurants = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd ładowania: $e')),
        );
      }
    }
  }

  Future<void> _toggleStatus(int id, bool currentStatus) async {
    try {
      final service = ref.read(sysAdminServiceProvider);
      await service.updateRestaurantStatus(id, !currentStatus);
      await _loadRestaurants();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd zmiany statusu: $e')),
        );
      }
    }
  }

  void _showAddRestaurantDialog() {
    final nameCtrl = TextEditingController();
    final slugCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Dodaj Restaurację'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtrl,
              decoration: const InputDecoration(labelText: 'Nazwa (np. Bella Italia)'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: slugCtrl,
              decoration: const InputDecoration(
                labelText: 'Login ID / Subdomena (np. bella-italia)',
                helperText: 'Tylko małe litery, cyfry i myślniki',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Anuluj'),
          ),
          ElevatedButton(
            onPressed: () async {
              if (nameCtrl.text.trim().isEmpty || slugCtrl.text.trim().isEmpty) {
                return;
              }
              try {
                final service = ref.read(sysAdminServiceProvider);
                await service.createRestaurant(
                    nameCtrl.text.trim(), slugCtrl.text.trim());
                if (mounted) {
                  Navigator.pop(ctx);
                  _loadRestaurants();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Utworzono restaurację')),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Błąd: ${ApiErrorHandler.extractMessage(e)}')),
                  );
                }
              }
            },
            child: const Text('Dodaj'),
          ),
        ],
      ),
    );
  }

  void _showAddManagerDialog(int restaurantId, String restaurantName) {
    final emailCtrl = TextEditingController();
    final firstNameCtrl = TextEditingController();
    final lastNameCtrl = TextEditingController();
    final passwordCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Dodaj managera\n($restaurantName)'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: emailCtrl,
                decoration: const InputDecoration(labelText: 'E-mail'),
                keyboardType: TextInputType.emailAddress,
              ),
              const SizedBox(height: 8),
              TextField(
                controller: firstNameCtrl,
                decoration: const InputDecoration(labelText: 'Imię'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: lastNameCtrl,
                decoration: const InputDecoration(labelText: 'Nazwisko'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: passwordCtrl,
                decoration: const InputDecoration(
                  labelText: 'Hasło',
                  helperText: 'Min. 8 znaków, cyfra i wielka litera',
                ),
                obscureText: true,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Anuluj'),
          ),
          ElevatedButton(
            onPressed: () async {
              final passError = ApiErrorHandler.validatePassword(passwordCtrl.text);
              if (passError != null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Błąd: $passError')),
                );
                return;
              }
              try {
                final service = ref.read(sysAdminServiceProvider);
                final result = await service.createManager(
                  restaurantId,
                  emailCtrl.text.trim(),
                  firstNameCtrl.text.trim(),
                  lastNameCtrl.text.trim(),
                  passwordCtrl.text,
                );
                if (mounted) {
                  Navigator.pop(ctx);
                  _loadRestaurants();
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                        content: Text(
                            result['message'] ?? 'Zapisano pomyślnie')),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Błąd: ${ApiErrorHandler.extractMessage(e)}')),
                  );
                }
              }
            },
            child: const Text('Dodaj'),
          ),
        ],
      ),
    );
  }

  void _showEditRestaurantDialog(int restaurantId, String currentName, String currentSlug) {
    final nameCtrl = TextEditingController(text: currentName);
    final slugCtrl = TextEditingController(text: currentSlug);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edytuj restaurację'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtrl,
              decoration: const InputDecoration(labelText: 'Nazwa (np. Moja Restauracja)'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: slugCtrl,
              decoration: const InputDecoration(labelText: 'Login ID (np. moja-rest)'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Anuluj'),
          ),
          ElevatedButton(
            onPressed: () async {
              try {
                final service = ref.read(sysAdminServiceProvider);
                await service.updateRestaurant(
                  restaurantId,
                  name: nameCtrl.text.trim(),
                  loginId: slugCtrl.text.trim(),
                );
                if (mounted) {
                  Navigator.pop(ctx);
                  _loadRestaurants();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Zaktualizowano restaurację')),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Błąd: ${ApiErrorHandler.extractMessage(e)}')),
                  );
                }
              }
            },
            child: const Text('Zapisz'),
          ),
        ],
      ),
    );
  }

  void _showUsersDialog(int restaurantId, String restaurantName) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Użytkownicy ($restaurantName)'),
        content: SizedBox(
          width: double.maxFinite,
          height: 400,
          child: FutureBuilder<List<Map<String, dynamic>>>(
            future: ref.read(sysAdminServiceProvider).getRestaurantUsers(restaurantId),
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return Center(child: Text('Błąd: ${snapshot.error}'));
              }
              final users = snapshot.data ?? [];
              if (users.isEmpty) return const Center(child: Text('Brak użytkowników.'));
              
              return ListView.builder(
                itemCount: users.length,
                itemBuilder: (context, index) {
                  final user = users[index];
                  final role = (user['role_system'] ?? '').toString().toLowerCase();
                  final isManager = role == 'manager' || role == 'admin';
                  return ListTile(
                    leading: Icon(isManager ? Icons.admin_panel_settings : Icons.person),
                    title: Text('${user['full_name']} (${user['username']})'),
                    subtitle: Text(user['email'] ?? 'Brak email'),
                    trailing: isManager
                        ? IconButton(
                            icon: const Icon(Icons.lock_reset),
                            tooltip: 'Zresetuj hasło',
                            onPressed: () => _showResetPasswordDialog(user['id'], user['username']),
                          )
                        : null,
                  );
                },
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Zamknij'),
          ),
        ],
      ),
    );
  }

  void _showResetPasswordDialog(String userId, String username) {
    final passCtrl = TextEditingController();
    String? errorText;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: Text('Zresetuj hasło ($username)'),
          content: TextField(
            controller: passCtrl,
            decoration: InputDecoration(
              labelText: 'Nowe hasło',
              helperText: 'Min. 8 znaków, cyfra i wielka litera',
              errorText: errorText,
            ),
            obscureText: true,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Anuluj'),
            ),
            ElevatedButton(
              onPressed: () async {
                final validationError = ApiErrorHandler.validatePassword(passCtrl.text);
                if (validationError != null) {
                  setDialogState(() => errorText = validationError);
                  return;
                }
                try {
                  final service = ref.read(sysAdminServiceProvider);
                  await service.resetUserPassword(userId, passCtrl.text);
                  if (ctx.mounted) {
                    Navigator.pop(ctx);
                  }
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Hasło zostało zmienione')),
                    );
                  }
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Błąd: ${ApiErrorHandler.extractMessage(e)}')),
                    );
                  }
                }
              },
              child: const Text('Zapisz'),
            ),
          ],
        ),
      ),
    );
  }

  void _openLogsForRestaurant(int restaurantId) {
    setState(() {
      _selectedLogRestaurantId = restaurantId;
    });
    _tabController.animateTo(1);
    _loadLogs(resetOffset: true);
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  //  LOGS LOGIC & VIEWER
  // ═══════════════════════════════════════════════════════════════════════════════

  Future<void> _loadLogs({bool resetOffset = true}) async {
    if (resetOffset) {
      _logOffset = 0;
      _expandedLogIndices.clear();
    }
    setState(() => _isLoadingLogs = true);
    try {
      final service = ref.read(sysAdminServiceProvider);
      final data = await service.getLogs(
        restaurantId: _selectedLogRestaurantId,
        level: _selectedLogLevel,
        category: _selectedLogCategory,
        search: _logSearchCtrl.text.trim(),
        limit: _logLimit,
        offset: _logOffset,
      );
      final newItems = List<Map<String, dynamic>>.from(data['items'] ?? []);
      setState(() {
        if (resetOffset) {
          _logs = newItems;
        } else {
          _logs.addAll(newItems);
        }
        _totalLogsCount = data['total'] ?? _logs.length;
        _isLoadingLogs = false;
      });
    } catch (e) {
      setState(() => _isLoadingLogs = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd ładowania logów: ${ApiErrorHandler.extractMessage(e)}')),
        );
      }
    }
  }

  void _confirmClearLogs() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Colors.red),
            SizedBox(width: 8),
            Text('Wyczyścić plik logów?'),
          ],
        ),
        content: const Text(
          'Czy na pewno chcesz wyczyścić bieżący plik logów systemowych? '
          'Wszystkie dotychczasowe wpisy zostaną usunięte. Operacja jest nieodwracalna.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Anuluj'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red.shade700,
              foregroundColor: Colors.white,
            ),
            onPressed: () async {
              try {
                Navigator.pop(ctx);
                final service = ref.read(sysAdminServiceProvider);
                await service.clearLogs();
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Plik logów został wyczyszczony')),
                  );
                  _loadLogs(resetOffset: true);
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Błąd: ${ApiErrorHandler.extractMessage(e)}')),
                  );
                }
              }
            },
            child: const Text('Wyczyść'),
          ),
        ],
      ),
    );
  }

  Color _getLevelColor(String level) {
    switch (level.toUpperCase()) {
      case 'ERROR':
      case 'CRITICAL':
        return Colors.red.shade700;
      case 'WARNING':
      case 'WARN':
        return Colors.orange.shade800;
      case 'INFO':
        return Colors.blue.shade700;
      case 'DEBUG':
        return Colors.blueGrey;
      default:
        return Colors.grey.shade700;
    }
  }

  Color _getLevelBgColor(String level) {
    switch (level.toUpperCase()) {
      case 'ERROR':
      case 'CRITICAL':
        return Colors.red.shade50;
      case 'WARNING':
      case 'WARN':
        return Colors.orange.shade50;
      case 'INFO':
        return Colors.blue.shade50;
      case 'DEBUG':
        return Colors.blueGrey.shade50;
      default:
        return Colors.grey.shade50;
    }
  }

  Color _getCategoryColor(String category) {
    switch (category.toUpperCase()) {
      case 'ANOMALY':
        return Colors.red.shade800;
      case 'DEFICIT':
        return Colors.amber.shade900;
      case 'SOLVER':
      case 'SOLVER WORKER':
        return Colors.purple.shade700;
      case 'SCHEDULE':
        return Colors.blueGrey.shade800;
      case 'AVAILABILITY':
        return Colors.green.shade800;
      case 'SHIFT_SWAP':
      case 'SWAP':
        return Colors.deepPurple.shade700;
      case 'LEAVE':
        return Colors.cyan.shade800;
      case 'ATTENDANCE':
        return Colors.teal.shade700;
      case 'AUTH':
        return Colors.indigo.shade700;
      case 'PUSH':
        return Colors.pink.shade700;
      case 'GCAL':
        return Colors.lightBlue.shade800;
      case 'POS':
        return Colors.orange.shade900;
      case 'CONFIG':
        return Colors.brown.shade700;
      default:
        return Colors.grey.shade800;
    }
  }

  String _getCategoryLabel(String category) {
    switch (category.toUpperCase()) {
      case 'ANOMALY':
        return 'ANOMALIA';
      case 'DEFICIT':
        return 'DEFICYTY';
      case 'SOLVER':
      case 'SOLVER WORKER':
        return 'SOLVER';
      case 'SCHEDULE':
        return 'GRAFIK';
      case 'AVAILABILITY':
        return 'DYSPOZYCYJNOŚĆ';
      case 'SHIFT_SWAP':
      case 'SWAP':
        return 'WYMIANA ZMIAN';
      case 'LEAVE':
        return 'URLOPY';
      case 'ATTENDANCE':
        return 'OBECNOŚĆ';
      case 'AUTH':
        return 'AUTH';
      case 'PUSH':
        return 'PUSH';
      case 'GCAL':
        return 'GOOGLE CAL';
      case 'POS':
        return 'POS';
      case 'CONFIG':
        return 'KONFIGURACJA';
      case 'SYSTEM':
        return 'SYSTEM';
      default:
        return category.toUpperCase();
    }
  }

  Widget _buildDetailsSection(dynamic details) {
    if (details == null) return const SizedBox.shrink();
    if (details is Map) {
      final entries = details.entries
          .where((e) => e.value != null && e.value.toString().trim().isNotEmpty)
          .toList();
      if (entries.isEmpty) return const SizedBox.shrink();
      return Container(
        margin: const EdgeInsets.only(top: 6),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.grey.shade50,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: Colors.grey.shade200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: entries.map((entry) {
            final key = entry.key.toString();
            final val = entry.value;
            String formattedValue;
            if (val is Map || val is List) {
              formattedValue = val.toString();
            } else {
              formattedValue = val.toString();
            }
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: RichText(
                text: TextSpan(
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey.shade900,
                    fontFamily: 'monospace',
                  ),
                  children: [
                    TextSpan(
                      text: '$key: ',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.purple.shade900,
                      ),
                    ),
                    TextSpan(text: formattedValue),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      );
    }
    final text = details.toString().trim();
    if (text.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: SelectableText(
        text,
        style: TextStyle(
          fontSize: 12,
          fontFamily: 'monospace',
          color: Colors.grey.shade800,
        ),
      ),
    );
  }

  Widget _buildRestaurantsTab() {
    if (_isLoadingRestaurants) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_restaurants.isEmpty) {
      return const Center(child: Text('Brak zarejestrowanych restauracji.'));
    }

    return ListView.builder(
      itemCount: _restaurants.length,
      padding: const EdgeInsets.all(16),
      itemBuilder: (context, index) {
        final r = _restaurants[index];
        final isActive = r['is_active'] == true;
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        '${r['name']} (ID: ${r['id']})',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.edit, size: 20),
                      onPressed: () => _showEditRestaurantDialog(r['id'], r['name'], r['slug']),
                      tooltip: 'Edytuj restaurację',
                    ),
                    Switch(
                      value: isActive,
                      onChanged: (val) => _toggleStatus(r['id'], isActive),
                      activeColor: Colors.purple,
                    ),
                  ],
                ),
                Text(
                  'Login ID: ${r['slug']}',
                  style: TextStyle(color: Colors.grey.shade700),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(Icons.people, size: 16, color: Colors.grey.shade600),
                    const SizedBox(width: 4),
                    Text('${r['user_count']} użytkowników'),
                    const SizedBox(width: 16),
                    Icon(Icons.admin_panel_settings,
                        size: 16, color: Colors.grey.shade600),
                    const SizedBox(width: 4),
                    Text('${r['manager_count']} managerów'),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  alignment: WrapAlignment.end,
                  children: [
                    OutlinedButton.icon(
                      icon: const Icon(Icons.receipt_long, size: 18),
                      label: const Text('Logi'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.purple.shade800,
                      ),
                      onPressed: () => _openLogsForRestaurant(r['id']),
                    ),
                    OutlinedButton.icon(
                      icon: const Icon(Icons.people, size: 18),
                      label: const Text('Użytkownicy'),
                      onPressed: () => _showUsersDialog(r['id'], r['name']),
                    ),
                    OutlinedButton.icon(
                      icon: const Icon(Icons.person_add, size: 18),
                      label: const Text('Dodaj managera'),
                      onPressed: () => _showAddManagerDialog(r['id'], r['name']),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildLogsTab() {
    return Column(
      children: [
        // Filter Header Panel
        Card(
          margin: const EdgeInsets.fromLTRB(12, 12, 12, 6),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Row 1: Restaurant Selector & Search Bar
                Row(
                  children: [
                    // Restaurant Dropdown
                    Expanded(
                      flex: 4,
                      child: InputDecorator(
                        decoration: InputDecoration(
                          labelText: 'Restauracja',
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                          prefixIcon: const Icon(Icons.storefront, size: 20),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<int?>(
                            isExpanded: true,
                            value: _selectedLogRestaurantId,
                            items: [
                              const DropdownMenuItem<int?>(
                                value: null,
                                child: Text('Wszystkie restauracje', style: TextStyle(fontWeight: FontWeight.bold)),
                              ),
                              const DropdownMenuItem<int?>(
                                value: 0,
                                child: Text('Systemowe / Bez tenanta'),
                              ),
                              ..._restaurants.map((r) => DropdownMenuItem<int?>(
                                    value: r['id'],
                                    child: Text('${r['name']} (ID: ${r['id']})'),
                                  )),
                            ],
                            onChanged: (val) {
                              setState(() => _selectedLogRestaurantId = val);
                              _loadLogs(resetOffset: true);
                            },
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    // Search Bar
                    Expanded(
                      flex: 5,
                      child: TextField(
                        controller: _logSearchCtrl,
                        decoration: InputDecoration(
                          hintText: 'Szukaj w logach...',
                          prefixIcon: const Icon(Icons.search, size: 20),
                          suffixIcon: _logSearchCtrl.text.isNotEmpty
                              ? IconButton(
                                  icon: const Icon(Icons.clear, size: 18),
                                  onPressed: () {
                                    _logSearchCtrl.clear();
                                    _loadLogs(resetOffset: true);
                                  },
                                )
                              : null,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        onSubmitted: (_) => _loadLogs(resetOffset: true),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),

                // Row 2: Level Filter Chips & Action Buttons
                Row(
                  children: [
                    Expanded(
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: [
                            const Text('Poziom: ', style: TextStyle(fontWeight: FontWeight.w600)),
                            const SizedBox(width: 6),
                            for (final lvl in ['ALL', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'DEBUG']) ...[
                              Padding(
                                padding: const EdgeInsets.only(right: 6),
                                child: ChoiceChip(
                                  label: Text(
                                    lvl == 'ALL' ? 'WSZYSTKIE' : lvl,
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold,
                                      color: _selectedLogLevel == lvl
                                          ? Colors.white
                                          : _getLevelColor(lvl),
                                    ),
                                  ),
                                  selected: _selectedLogLevel == lvl,
                                  selectedColor: lvl == 'ALL' ? Colors.purple.shade800 : _getLevelColor(lvl),
                                  backgroundColor: _getLevelBgColor(lvl),
                                  onSelected: (selected) {
                                    if (selected) {
                                      setState(() => _selectedLogLevel = lvl);
                                      _loadLogs(resetOffset: true);
                                    }
                                  },
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                    // Refresh & Clear Logs Actions
                    IconButton(
                      icon: const Icon(Icons.refresh),
                      tooltip: 'Odśwież logi',
                      onPressed: () => _loadLogs(resetOffset: true),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.red),
                      tooltip: 'Wyczyść plik logów',
                      onPressed: _confirmClearLogs,
                    ),
                  ],
                ),

                const SizedBox(height: 8),

                // Row 3: Quick Category & Anomaly Tag Chips (independent of search bar)
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      const Text('Kategoria: ', style: TextStyle(fontWeight: FontWeight.w600)),
                      const SizedBox(width: 6),
                      for (final qf in [
                        {'label': 'Wszystkie zdarzenia', 'tag': 'ALL'},
                        {'label': 'ANOMALIE', 'tag': 'ANOMALY'},
                        {'label': 'SOLVER', 'tag': 'SOLVER'},
                        {'label': 'DEFICYTY', 'tag': 'DEFICIT'},
                        {'label': 'GRAFIK', 'tag': 'SCHEDULE'},
                        {'label': 'DYSPOZYCYJNOŚĆ', 'tag': 'AVAILABILITY'},
                        {'label': 'WYMIANA ZMIAN', 'tag': 'SHIFT_SWAP'},
                        {'label': 'URLOPY', 'tag': 'LEAVE'},
                        {'label': 'OBECNOŚĆ', 'tag': 'ATTENDANCE'},
                        {'label': 'LOGOWANIA (AUTH)', 'tag': 'AUTH'},
                        {'label': 'POWIADOMIENIA (PUSH)', 'tag': 'PUSH'},
                        {'label': 'GOOGLE CALENDAR', 'tag': 'GCAL'},
                        {'label': 'POS', 'tag': 'POS'},
                        {'label': 'KONFIGURACJA', 'tag': 'CONFIG'},
                        {'label': 'SYSTEM', 'tag': 'SYSTEM'},
                      ]) ...[
                        Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: ChoiceChip(
                            label: Text(
                              qf['label']!,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: _selectedLogCategory == qf['tag']!
                                    ? Colors.white
                                    : (qf['tag'] == 'ANOMALY' ? Colors.red.shade900 : Colors.purple.shade900),
                              ),
                            ),
                            selected: _selectedLogCategory == qf['tag']!,
                            selectedColor: qf['tag'] == 'ANOMALY' ? Colors.red.shade700 : Colors.purple.shade800,
                            backgroundColor: qf['tag'] == 'ANOMALY' ? Colors.red.shade50 : Colors.purple.shade50,
                            side: BorderSide(
                              color: qf['tag'] == 'ANOMALY' ? Colors.red.shade300 : Colors.purple.shade200,
                            ),
                            onSelected: (selected) {
                              if (selected) {
                                setState(() {
                                  _selectedLogCategory = qf['tag']!;
                                });
                                _loadLogs(resetOffset: true);
                              }
                            },
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),

        // Subheader: Summary / Counts
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Wpisy: ${_logs.length} z $_totalLogsCount'
                '${_selectedLogRestaurantId != null ? " • Filtrowane po ID: $_selectedLogRestaurantId" : ""}'
                '${_selectedLogCategory != "ALL" ? " • Kategoria: ${_getCategoryLabel(_selectedLogCategory)}" : ""}',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade700, fontWeight: FontWeight.w600),
              ),
              if (_selectedLogRestaurantId != null ||
                  _selectedLogLevel != 'ALL' ||
                  _selectedLogCategory != 'ALL' ||
                  _logSearchCtrl.text.isNotEmpty)
                InkWell(
                  onTap: () {
                    setState(() {
                      _selectedLogRestaurantId = null;
                      _selectedLogLevel = 'ALL';
                      _selectedLogCategory = 'ALL';
                      _logSearchCtrl.clear();
                    });
                    _loadLogs(resetOffset: true);
                  },
                  child: const Text(
                    'Wyczyść filtry',
                    style: TextStyle(fontSize: 12, color: Colors.purple, fontWeight: FontWeight.bold),
                  ),
                ),
            ],
          ),
        ),

        // Log Items List
        Expanded(
          child: _isLoadingLogs && _logs.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : _logs.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.search_off, size: 64, color: Colors.grey.shade400),
                          const SizedBox(height: 12),
                          Text(
                            'Brak logów dla wybranych kryteriów.',
                            style: TextStyle(color: Colors.grey.shade600, fontSize: 16),
                          ),
                          const SizedBox(height: 8),
                          OutlinedButton.icon(
                            icon: const Icon(Icons.refresh),
                            label: const Text('Odśwież'),
                            onPressed: () => _loadLogs(resetOffset: true),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      itemCount: _logs.length + (_logs.length < _totalLogsCount ? 1 : 0),
                      padding: const EdgeInsets.fromLTRB(12, 4, 12, 16),
                      itemBuilder: (context, index) {
                        if (index == _logs.length) {
                          return Center(
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: ElevatedButton.icon(
                                icon: const Icon(Icons.expand_more),
                                label: const Text('Załaduj starsze logi'),
                                onPressed: () {
                                  _logOffset += _logLimit;
                                  _loadLogs(resetOffset: false);
                                },
                              ),
                            ),
                          );
                        }

                        final item = _logs[index];
                        final level = (item['level'] ?? 'INFO').toString().toUpperCase();
                        final color = _getLevelColor(level);
                        final timestamp = (item['timestamp'] ?? '').toString();
                        final loggerName = (item['logger'] ?? '').toString();
                        final category = (item['category'] ?? 'SYSTEM').toString().toUpperCase();
                        final eventTitle = (item['event_title'] ?? item['message'] ?? '').toString();
                        final details = item['details'];
                        final rawTraceback = item['traceback'];
                        final traceback = rawTraceback != null && rawTraceback.toString().trim().isNotEmpty
                            ? rawTraceback.toString().trim()
                            : null;
                        final hasTraceback = traceback != null;
                        final tracebackLines = hasTraceback ? traceback.split('\n') : <String>[];

                        final tenantId = item['tenant_id'];
                        final tenantName = item['tenant_name'] ?? item['restaurant_name'];
                        final actorName = item['actor_name'];
                        final isExpanded = _expandedLogIndices.contains(index);

                        final isAnomaly = category == 'ANOMALY' ||
                            eventTitle.contains('ANOMALY') ||
                            eventTitle.contains('REST VIOLATION');

                        return Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          elevation: isAnomaly ? 2 : 1,
                          color: isAnomaly ? Colors.red.shade50.withValues(alpha: 0.4) : null,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                            side: BorderSide(
                              color: isAnomaly ? Colors.red.shade600 : color.withValues(alpha: 0.3),
                              width: isAnomaly ? 1.5 : 1,
                            ),
                          ),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(8),
                            onTap: hasTraceback
                                ? () {
                                    setState(() {
                                      if (isExpanded) {
                                        _expandedLogIndices.remove(index);
                                      } else {
                                        _expandedLogIndices.add(index);
                                      }
                                    });
                                  }
                                : null,
                            child: Padding(
                              padding: const EdgeInsets.all(10),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // Top row: Level Badge, Timestamp, Restaurant Badge, Category Badge, Actor Badge, Copy button
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Wrap(
                                          spacing: 6,
                                          runSpacing: 4,
                                          crossAxisAlignment: WrapCrossAlignment.center,
                                          children: [
                                            // Level badge
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: color,
                                                borderRadius: BorderRadius.circular(4),
                                              ),
                                              child: Text(
                                                level,
                                                style: const TextStyle(
                                                  color: Colors.white,
                                                  fontSize: 10,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                            ),
                                            // Timestamp
                                            Text(
                                              timestamp,
                                              style: TextStyle(
                                                fontSize: 12,
                                                color: Colors.grey.shade600,
                                                fontFamily: 'monospace',
                                              ),
                                            ),
                                            // Restaurant Badge
                                            if (tenantId != null)
                                              Container(
                                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                decoration: BoxDecoration(
                                                  color: Colors.purple.shade50,
                                                  border: Border.all(color: Colors.purple.shade200),
                                                  borderRadius: BorderRadius.circular(4),
                                                ),
                                                child: Text(
                                                  tenantName != null
                                                      ? '$tenantName (ID: $tenantId)'
                                                      : 'Restauracja ID: $tenantId',
                                                  style: TextStyle(
                                                    fontSize: 11,
                                                    color: Colors.purple.shade900,
                                                    fontWeight: FontWeight.w600,
                                                  ),
                                                ),
                                              )
                                            else
                                              Container(
                                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                decoration: BoxDecoration(
                                                  color: Colors.grey.shade200,
                                                  borderRadius: BorderRadius.circular(4),
                                                ),
                                                child: Text(
                                                  'System / Ogólne',
                                                  style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
                                                ),
                                              ),
                                            // Category Badge
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: _getCategoryColor(category),
                                                borderRadius: BorderRadius.circular(4),
                                              ),
                                              child: Text(
                                                _getCategoryLabel(category),
                                                style: const TextStyle(
                                                  color: Colors.white,
                                                  fontSize: 10,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                            ),
                                            // Actor Badge
                                            if (actorName != null && actorName.toString().trim().isNotEmpty)
                                              Container(
                                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                decoration: BoxDecoration(
                                                  color: Colors.teal.shade50,
                                                  border: Border.all(color: Colors.teal.shade200),
                                                  borderRadius: BorderRadius.circular(4),
                                                ),
                                                child: Row(
                                                  mainAxisSize: MainAxisSize.min,
                                                  children: [
                                                    Icon(Icons.person_outline, size: 12, color: Colors.teal.shade900),
                                                    const SizedBox(width: 3),
                                                    Text(
                                                      actorName.toString(),
                                                      style: TextStyle(
                                                        fontSize: 11,
                                                        color: Colors.teal.shade900,
                                                        fontWeight: FontWeight.w600,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                          ],
                                        ),
                                      ),
                                      // Copy to clipboard button
                                      IconButton(
                                        icon: const Icon(Icons.copy, size: 16),
                                        tooltip: 'Kopiuj wpis',
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        onPressed: () {
                                          final fullText = '[$timestamp] [$level] [$category] '
                                              '[tenant:${tenantId ?? '-'}] '
                                              '${actorName != null ? "[actor:$actorName] " : ""}'
                                              '$eventTitle '
                                              '${details != null ? "| details: $details " : ""}'
                                              '${hasTraceback ? "\n$traceback" : ""}';
                                          Clipboard.setData(ClipboardData(text: fullText));
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            const SnackBar(
                                              content: Text('Skopiowano wpis logu do schowka'),
                                              duration: Duration(seconds: 1),
                                            ),
                                          );
                                        },
                                      ),
                                    ],
                                  ),

                                  const SizedBox(height: 8),

                                  // Bold Event Title
                                  SelectableText(
                                    eventTitle,
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.bold,
                                      color: level == 'ERROR' || level == 'CRITICAL'
                                          ? Colors.red.shade900
                                          : Colors.grey.shade900,
                                    ),
                                  ),

                                  // Details Key-Value Section
                                  _buildDetailsSection(details),

                                  // Logger name subtitle (subtle)
                                  if (loggerName.isNotEmpty)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 4),
                                      child: Text(
                                        'Źródło: $loggerName',
                                        style: TextStyle(
                                          fontSize: 10,
                                          color: Colors.grey.shade500,
                                        ),
                                      ),
                                    ),

                                  // Traceback section ONLY when a real exception traceback exists
                                  if (hasTraceback) ...[
                                    if (isExpanded)
                                      Container(
                                        width: double.infinity,
                                        margin: const EdgeInsets.only(top: 6),
                                        padding: const EdgeInsets.all(8),
                                        decoration: BoxDecoration(
                                          color: Colors.red.shade50,
                                          borderRadius: BorderRadius.circular(6),
                                          border: Border.all(color: Colors.red.shade200),
                                        ),
                                        child: SelectableText(
                                          traceback,
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontFamily: 'monospace',
                                            color: Colors.red.shade900,
                                          ),
                                        ),
                                      ),
                                    Padding(
                                      padding: const EdgeInsets.only(top: 4),
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.end,
                                        children: [
                                          Text(
                                            isExpanded
                                                ? 'Zwiń traceback'
                                                : 'Pokaż pełny traceback (${tracebackLines.length} linii)',
                                            style: TextStyle(
                                              fontSize: 11,
                                              color: Colors.red.shade800,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                          Icon(
                                            isExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                                            size: 16,
                                            color: Colors.red.shade800,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  //  BUILD METHOD
  // ═══════════════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SuperAdmin Dashboard'),
        backgroundColor: Colors.purple.shade800,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              if (_tabController.index == 0) {
                _loadRestaurants();
              } else {
                _loadLogs(resetOffset: true);
              }
            },
            tooltip: 'Odśwież',
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () {
              ref.read(authProvider.notifier).logout();
            },
            tooltip: 'Wyloguj',
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          indicatorWeight: 3,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white70,
          tabs: const [
            Tab(
              icon: Icon(Icons.storefront),
              text: 'Restauracje',
            ),
            Tab(
              icon: Icon(Icons.receipt_long),
              text: 'Logi systemowe',
            ),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildRestaurantsTab(),
          _buildLogsTab(),
        ],
      ),
      floatingActionButton: _tabController.index == 0
          ? FloatingActionButton.extended(
              onPressed: _showAddRestaurantDialog,
              icon: const Icon(Icons.add),
              label: const Text('Dodaj Restaurację'),
              backgroundColor: Colors.purple.shade800,
              foregroundColor: Colors.white,
            )
          : null,
    );
  }
}
