import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class TeamTab extends ConsumerStatefulWidget {
  const TeamTab({super.key});

  @override
  ConsumerState<TeamTab> createState() => _TeamTabState();
}

class _TeamTabState extends ConsumerState<TeamTab> {
  List<TeamMember>? _users;
  List<JobRole>? _roles;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = ref.read(apiServiceProvider);
      final users = await api.getUsers();
      final roles = await api.getRoles();
      
      setState(() {
        _users = users.where((u) => u.isEmployee).toList(); // Only show employees
        _roles = roles;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Color _parseHexColor(String hex) {
    final hexCode = hex.replaceAll('#', '');
    return Color(int.parse('FF$hexCode', radix: 16));
  }

  void _showRoleDialog(TeamMember user) {
    final selectedRoles = Set<int>.from(user.jobRoleIds);
    
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text('Role dla ${user.fullName}'),
          content: SizedBox(
            width: 300,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: _roles!.map((role) => CheckboxListTile(
                title: Text(role.name),
                secondary: Container(
                  width: 24,
                  height: 24,
                  decoration: BoxDecoration(
                    color: _parseHexColor(role.colorHex),
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
                value: selectedRoles.contains(role.id),
                onChanged: (value) {
                  setDialogState(() {
                    if (value == true) {
                      selectedRoles.add(role.id);
                    } else {
                      selectedRoles.remove(role.id);
                    }
                  });
                },
              )).toList(),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Anuluj'),
            ),
            FilledButton(
              onPressed: () async {
                Navigator.pop(context);
                await _saveRoles(user.id, selectedRoles.toList());
              },
              child: const Text('Zapisz'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _saveRoles(String userId, List<int> roleIds) async {
    try {
      final api = ref.read(apiServiceProvider);
      await api.setUserRoles(userId, roleIds);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Role zapisane')),
        );
      }
      
      await _loadData(); // Refresh
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e')),
        );
      }
    }
  }

  void _showPasswordDialog(TeamMember user) {
    final newPasswordController = TextEditingController();
    final confirmPasswordController = TextEditingController();
    String? errorText;

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text('Zmień hasło: ${user.fullName}'),
          content: SizedBox(
            width: 300,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: newPasswordController,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: 'Nowe hasło',
                    prefixIcon: const Icon(Icons.lock),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: confirmPasswordController,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: 'Powtórz hasło',
                    prefixIcon: const Icon(Icons.lock_outline),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    errorText: errorText,
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Anuluj'),
            ),
            FilledButton(
              onPressed: () async {
                final newPass = newPasswordController.text;
                final confirmPass = confirmPasswordController.text;
                
                if (newPass.length < 6) {
                  setDialogState(() => errorText = 'Hasło musi mieć min. 6 znaków');
                  return;
                }
                if (newPass != confirmPass) {
                  setDialogState(() => errorText = 'Hasła nie są zgodne');
                  return;
                }
                
                Navigator.pop(context);
                await _resetPassword(user.id, newPass);
              },
              child: const Text('Zapisz'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _resetPassword(String userId, String newPassword) async {
    try {
      final api = ref.read(apiServiceProvider);
      await api.resetUserPassword(userId, newPassword);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Hasło zostało zmienione'),
            backgroundColor: Colors.green.shade600,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Błąd: $e'),
            backgroundColor: Colors.red.shade600,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Błąd: $_error'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadData,
              child: const Text('Ponów'),
            ),
          ],
        ),
      );
    }

    if (_users == null || _users!.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.people_outline, size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            Text(
              'Brak pracowników',
              style: GoogleFonts.inter(
                fontSize: 18,
                color: Colors.grey.shade600,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _users!.length,
        itemBuilder: (context, index) {
          final user = _users![index];
          final userRoles = _roles?.where((r) => user.jobRoleIds.contains(r.id)).toList() ?? [];

          return Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: Colors.indigo.shade100,
                child: Text(
                  user.fullName.isNotEmpty ? user.fullName[0].toUpperCase() : '?',
                  style: TextStyle(color: Colors.indigo.shade700),
                ),
              ),
              title: Text(
                user.fullName,
                style: GoogleFonts.inter(fontWeight: FontWeight.w600),
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('@${user.username}', style: TextStyle(color: Colors.grey.shade600)),
                  if (userRoles.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 4,
                      runSpacing: 4,
                      children: userRoles.map((role) => Chip(
                        label: Text(
                          role.name,
                          style: const TextStyle(fontSize: 12, color: Colors.white),
                        ),
                        backgroundColor: _parseHexColor(role.colorHex),
                        padding: EdgeInsets.zero,
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      )).toList(),
                    ),
                  ] else
                    Text(
                      'Brak przypisanych ról',
                      style: TextStyle(
                        fontSize: 12,
                        fontStyle: FontStyle.italic,
                        color: Colors.grey.shade500,
                      ),
                    ),
                ],
              ),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    icon: const Icon(Icons.lock_reset),
                    tooltip: 'Zmień hasło',
                    onPressed: () => _showPasswordDialog(user),
                  ),
                  IconButton(
                    icon: const Icon(Icons.edit),
                    tooltip: 'Edytuj role',
                    onPressed: () => _showRoleDialog(user),
                  ),
                ],
              ),
              onTap: () => _showRoleDialog(user),
            ),
          );
        },
      ),
    );
  }
}
