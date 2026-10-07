import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../providers/providers.dart';
import '../services/sysadmin_service.dart';

class SysAdminDashboardScreen extends ConsumerStatefulWidget {
  const SysAdminDashboardScreen({super.key});

  @override
  ConsumerState<SysAdminDashboardScreen> createState() =>
      _SysAdminDashboardScreenState();
}

class _SysAdminDashboardScreenState
    extends ConsumerState<SysAdminDashboardScreen> {
  List<Map<String, dynamic>> _restaurants = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadRestaurants();
  }

  Future<void> _loadRestaurants() async {
    setState(() => _isLoading = true);
    try {
      final service = ref.read(sysAdminServiceProvider);
      final data = await service.getRestaurants();
      setState(() {
        _restaurants = data;
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
              } on DioException catch (e) {
                if (mounted) {
                  final msg = e.response?.data?['detail'] ?? e.message;
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Błąd: $msg')),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Błąd: $e')),
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
              } on DioException catch (e) {
                if (mounted) {
                  final msg = e.response?.data?['detail'] ?? e.message;
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Błąd: $msg')),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Błąd: $e')),
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
            onPressed: _loadRestaurants,
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
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _restaurants.length,
              padding: const EdgeInsets.all(16),
              itemBuilder: (context, index) {
                final r = _restaurants[index];
                final isActive = r['is_active'] == true;
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
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
                        Align(
                          alignment: Alignment.centerRight,
                          child: OutlinedButton.icon(
                            icon: const Icon(Icons.person_add),
                            label: const Text('Dodaj pierwszego managera'),
                            onPressed: () => _showAddManagerDialog(r['id'], r['name']),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddRestaurantDialog,
        icon: const Icon(Icons.add),
        label: const Text('Dodaj Restaurację'),
        backgroundColor: Colors.purple.shade800,
        foregroundColor: Colors.white,
      ),
    );
  }
}
