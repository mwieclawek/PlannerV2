import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';
import 'employee_detail_dialog.dart';

class TeamTab extends ConsumerStatefulWidget {
  const TeamTab({super.key});

  @override
  ConsumerState<TeamTab> createState() => _TeamTabState();
}

class _TeamTabState extends ConsumerState<TeamTab> {
  List<TeamMember>? _users;
  List<JobRole>? _roles;
  bool _isLoading = true;
  bool _showInactive = false;
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
      final users = await api.getUsers(includeInactive: _showInactive);
      final roles = await api.getRoles();
      
      setState(() {
        _users = users.where((u) => u.isEmployee).toList();
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

  Future<void> _toggleUserActive(TeamMember user) async {
    final newActive = !user.isActive;
    final actionText = newActive ? 'aktywowany' : 'dezaktywowany';
    try {
      final api = ref.read(apiServiceProvider);
      await api.updateUser(user.id, isActive: newActive);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${user.fullName} został $actionText'),
            backgroundColor: newActive ? Colors.green : Theme.of(context).colorScheme.tertiary,
          ),
        );
      }
      await _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red),
        );
      }
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

  void _showPreferencesDialog(TeamMember user) {
    final hoursController = TextEditingController(text: user.targetHoursPerMonth?.toString() ?? '');
    final shiftsController = TextEditingController(text: user.targetShiftsPerMonth?.toString() ?? '');

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Preferencje: ${user.fullName}'),
        content: SizedBox(
          width: 300,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
               TextField(
                controller: hoursController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Docelowa liczba godzin / m-c',
                  prefixIcon: const Icon(Icons.timer),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: shiftsController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Docelowa liczba zmian / m-c',
                  prefixIcon: const Icon(Icons.calendar_view_day),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Anuluj')),
          FilledButton(
            onPressed: () async {
              Navigator.pop(context);
              await _savePreferences(
                user.id, 
                int.tryParse(hoursController.text), 
                int.tryParse(shiftsController.text)
              );
            },
            child: const Text('Zapisz'),
          ),
        ],
      ),
    );
  }

  Future<void> _savePreferences(String userId, int? targetHours, int? targetShifts) async {
    try {
      final api = ref.read(apiServiceProvider);
      await api.updateUser(userId, targetHoursPerMonth: targetHours, targetShiftsPerMonth: targetShifts);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Preferencje zapisane'), backgroundColor: Colors.green),
        );
      }
      
      await _loadData(); // Refresh to see updated targets if needed or just for consistency
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red),
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
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    Widget content;

    if (_isLoading) {
      content = const Center(child: CircularProgressIndicator());
    } else if (_error != null) {
      content = Center(
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
    } else if (_users == null || _users!.isEmpty) {
      content = Center(
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
    } else {
      content = RefreshIndicator(
        onRefresh: _loadData,
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: _users!.length,
          itemBuilder: (context, index) {
            final user = _users![index];
            final userRoles = _roles?.where((r) => user.jobRoleIds.contains(r.id)).toList() ?? [];

            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              color: user.isActive ? null : Colors.grey.shade100,
              child: Opacity(
                opacity: user.isActive ? 1.0 : 0.6,
                child: ListTile(
                leading: Stack(
                  children: [
                    CircleAvatar(
                      backgroundColor: user.isActive ? Theme.of(context).colorScheme.primaryContainer : Colors.grey.shade300,
                      child: Text(
                        user.fullName.isNotEmpty ? user.fullName[0].toUpperCase() : '?',
                        style: TextStyle(color: user.isActive ? Theme.of(context).colorScheme.onPrimaryContainer : Colors.grey.shade600),
                      ),
                    ),
                    if (!user.isActive)
                      Positioned(
                        right: 0, bottom: 0,
                        child: Container(
                          width: 12, height: 12,
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.error,
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 1.5),
                          ),
                        ),
                      ),
                  ],
                ),
                title: Row(
                  children: [
                    Expanded(
                      child: Text(
                        user.fullName,
                        style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                      ),
                    ),
                    if (!user.isActive)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.errorContainer,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: Theme.of(context).colorScheme.error.withOpacity(0.5)),
                        ),
                        child: Text(
                          'NIEAKTYWNY',
                          style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Theme.of(context).colorScheme.error),
                        ),
                      ),
                  ],
                ),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('@${user.username}', style: TextStyle(color: Colors.grey.shade600)),
                    
                    // Next Shift Display
                    if (user.nextShift != null && user.isActive) ...[
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(Icons.calendar_today, size: 14, color: Theme.of(context).colorScheme.primary),
                          const SizedBox(width: 4),
                          Text(
                            'Następna: ${user.nextShift!.shiftName} (${user.nextShift!.roleName})',
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: Theme.of(context).colorScheme.primary,
                            ),
                          ),
                        ],
                      ),
                      Text(
                        '${user.nextShift!.date.day}.${user.nextShift!.date.month}  ${user.nextShift!.startTime} - ${user.nextShift!.endTime}',
                        style: GoogleFonts.inter(fontSize: 12, color: Colors.grey.shade700),
                      ),
                    ] else if (user.isActive) ...[
                       const SizedBox(height: 4),
                       Text('Brak nadchodzących zmian', style: TextStyle(fontSize: 12, color: Colors.grey.shade500, fontStyle: FontStyle.italic)),
                    ],

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
                    ],
                  ],
                ),
                trailing: PopupMenuButton<String>(
                  icon: const Icon(Icons.more_vert, color: Colors.grey),
                  onSelected: (value) {
                    switch (value) {
                      case 'details':
                        showDialog(
                          context: context,
                          builder: (context) => EmployeeDetailDialog(
                            user: user,
                            onEdit: () => _showPreferencesDialog(user),
                            onEditRoles: () => _showRoleDialog(user),
                            onResetPassword: () => _showPasswordDialog(user),
                          ),
                        );
                        break;
                      case 'toggle_active':
                        _toggleUserActive(user);
                        break;
                    }
                  },
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: 'details',
                      child: ListTile(
                        leading: Icon(Icons.info_outline),
                        title: Text('Szczegóły'),
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                    PopupMenuItem(
                      value: 'toggle_active',
                      child: ListTile(
                        leading: Icon(
                          user.isActive ? Icons.person_off : Icons.person,
                          color: user.isActive ? Theme.of(context).colorScheme.tertiary : Colors.green,
                        ),
                        title: Text(user.isActive ? 'Dezaktywuj' : 'Aktywuj'),
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                  ],
                ),
                onTap: () {
                  showDialog(
                    context: context,
                    builder: (context) => EmployeeDetailDialog(
                      user: user,
                      onEdit: () => _showPreferencesDialog(user),
                      onEditRoles: () => _showRoleDialog(user),
                      onResetPassword: () => _showPasswordDialog(user),
                    ),
                  );
                },
              ),
              ),
            );
          },
        ),
      );
    }

    return Scaffold(
      body: Column(
        children: [
          // Show inactive toggle
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Row(
              children: [
                Icon(Icons.filter_list, size: 18, color: Colors.grey.shade600),
                const SizedBox(width: 8),
                Text('Pokaż nieaktywnych', style: GoogleFonts.inter(fontSize: 13)),
                const SizedBox(width: 8),
                Switch(
                  value: _showInactive,
                  onChanged: (v) {
                    setState(() => _showInactive = v);
                    _loadData();
                  },
                ),
              ],
            ),
          ),
          Expanded(child: content),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddUserDialog,
        child: const Icon(Icons.person_add),
      ),
    );
  }

  void _showAddUserDialog() {
    final formKey = GlobalKey<FormState>();
    final usernameController = TextEditingController();
    final passwordController = TextEditingController();
    final fullNameController = TextEditingController();
    final emailController = TextEditingController();
    final hoursController = TextEditingController();
    final shiftsController = TextEditingController();
    String roleSystem = 'EMPLOYEE';
    bool isLoading = false;

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Dodaj pracownika'),
          content: SizedBox(
            width: 400,
            child: Form(
              key: formKey,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                     TextFormField(
                      controller: usernameController,
                      decoration: const InputDecoration(labelText: 'Login *'),
                      validator: (v) => v != null && v.length >= 3 ? null : 'Min. 3 znaki',
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: passwordController,
                      decoration: const InputDecoration(labelText: 'Hasło *'),
                      obscureText: true,
                      validator: (v) => v != null && v.length >= 6 ? null : 'Min. 6 znaków',
                    ),
                     const SizedBox(height: 16),
                     TextFormField(
                      controller: fullNameController,
                      decoration: const InputDecoration(labelText: 'Pełna nazwa *'),
                      validator: (v) => v != null && v.isNotEmpty ? null : 'Wymagane',
                    ),
                     const SizedBox(height: 16),
                     TextFormField(
                      controller: emailController,
                      decoration: const InputDecoration(labelText: 'Email'),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      value: roleSystem,
                      decoration: const InputDecoration(labelText: 'Rola systemowa'),
                      items: const [
                        DropdownMenuItem(value: 'EMPLOYEE', child: Text('Pracownik')),
                        DropdownMenuItem(value: 'MANAGER', child: Text('Manager')),
                      ],
                      onChanged: (v) => setDialogState(() => roleSystem = v!),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: hoursController,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(labelText: 'Cel Godzin'),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: TextFormField(
                            controller: shiftsController,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(labelText: 'Cel Zmian'),
                          ),
                        ),
                      ],
                    ),
                    if (isLoading)
                      const Padding(
                        padding: EdgeInsets.only(top: 16.0),
                        child: Center(child: CircularProgressIndicator()),
                      ),
                  ],
                ),
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: isLoading ? null : () => Navigator.pop(context),
              child: const Text('Anuluj'),
            ),
            FilledButton(
              onPressed: isLoading ? null : () async {
                if (!formKey.currentState!.validate()) return;
                
                setDialogState(() => isLoading = true);
                
                try {
                  final api = ref.read(apiServiceProvider);
                  await api.createUser(
                    username: usernameController.text,
                    password: passwordController.text,
                    fullName: fullNameController.text,
                    roleSystem: roleSystem,
                    email: emailController.text.isNotEmpty ? emailController.text : null,
                    targetHoursPerMonth: int.tryParse(hoursController.text),
                    targetShiftsPerMonth: int.tryParse(shiftsController.text),
                  );
                  
                  if (context.mounted) {
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Dodano pracownika'), backgroundColor: Colors.green),
                    );
                    _loadData();
                  }
                } catch (e) {
                   if (context.mounted) {
                      setDialogState(() => isLoading = false);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Błąd: $e'), backgroundColor: Theme.of(context).colorScheme.error),
                      );
                   }
                }
              },
              child: const Text('Dodaj'),
            ),
          ],
        ),
      ),
    );
  }
}
