import re

with open('frontend/lib/screens/sysadmin/sysadmin_dashboard.dart', 'r', encoding='utf-8') as f:
    content = f.read()

edit_dialog = '''
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
                    SnackBar(content: Text('Błąd: $e')),
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
                  final isManager = user['role_system'] == 'manager' || user['role_system'] == 'admin';
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
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(f'Zresetuj hasło ({username})'.replace('f', '')),
        content: TextField(
          controller: passCtrl,
          decoration: const InputDecoration(labelText: 'Nowe hasło'),
          obscureText: true,
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
                await service.resetUserPassword(userId, passCtrl.text);
                if (mounted) {
                  Navigator.pop(ctx);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Hasło zostało zmienione')),
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
            child: const Text('Zapisz'),
          ),
        ],
      ),
    );
  }
'''

content = content.replace('Widget build(BuildContext context) {', edit_dialog + '\n  @override\n  Widget build(BuildContext context) {')

card_replacement = '''
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
                              icon: const Icon(Icons.edit),
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
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            OutlinedButton.icon(
                              icon: const Icon(Icons.people),
                              label: const Text('Użytkownicy'),
                              onPressed: () => _showUsersDialog(r['id'], r['name']),
                            ),
                            const SizedBox(width: 8),
                            OutlinedButton.icon(
                              icon: const Icon(Icons.person_add),
                              label: const Text('Dodaj managera'),
                              onPressed: () => _showAddManagerDialog(r['id'], r['name']),
                            ),
                          ],
                        ),
'''

content = re.sub(
    r'Row\(\s*mainAxisAlignment: MainAxisAlignment\.spaceBetween,\s*children: \[\s*Expanded\(.*?\),\s*\],.*?\),', 
    card_replacement.strip(), 
    content, 
    flags=re.DOTALL
)

with open('frontend/lib/screens/sysadmin/sysadmin_dashboard.dart', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sysadmin_dashboard.dart")
