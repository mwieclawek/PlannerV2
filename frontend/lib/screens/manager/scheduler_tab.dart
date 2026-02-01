import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';
import '../../widgets/schedule_viewer.dart';

class SchedulerTab extends ConsumerStatefulWidget {
  const SchedulerTab({super.key});

  @override
  ConsumerState<SchedulerTab> createState() => _SchedulerTabState();
}

class _SchedulerTabState extends ConsumerState<SchedulerTab> {
  DateTime _selectedWeekStart = _getMonday(DateTime.now());
  bool _isGenerating = false;
  bool _isSaving = false;
  bool _hasUnsavedChanges = false;
  Map<String, dynamic>? _lastResult;
  List<ScheduleEntry> _scheduleEntries = [];
  List<ScheduleEntry> _originalEntries = []; // For tracking changes
  List<ShiftDefinition> _shifts = [];
  List<JobRole> _roles = [];
  List<TeamMember> _users = [];
  int _localIdCounter = -1; // For generating temporary IDs
  bool _isFirstEdit = true; // To show info banner on first edit

  static DateTime _getMonday(DateTime date) {
    return date.subtract(Duration(days: date.weekday - 1));
  }

  void _updateUnsavedChanges(bool value) {
    _hasUnsavedChanges = value;
    // Sync with global provider for tab switch warning
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        ref.read(hasUnsavedScheduleChangesProvider.notifier).state = value;
      }
    });
  }

  DateTime get _selectedWeekEnd => _selectedWeekStart.add(const Duration(days: 6));

  void _previousWeek() {
    if (_hasUnsavedChanges) {
      _showUnsavedChangesWarning(() {
        _changeWeek(-7);
      });
    } else {
      _changeWeek(-7);
    }
  }

  void _nextWeek() {
    if (_hasUnsavedChanges) {
      _showUnsavedChangesWarning(() {
        _changeWeek(7);
      });
    } else {
      _changeWeek(7);
    }
  }

  void _changeWeek(int days) {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.add(Duration(days: days));
      _scheduleEntries = [];
      _originalEntries = [];
      _hasUnsavedChanges = false;
      _isFirstEdit = true;
      _lastResult = null;
    });
    _loadSchedule();
  }

  void _showUnsavedChangesWarning(VoidCallback onDiscard) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Niezapisane zmiany'),
        content: const Text('Masz niezapisane zmiany w grafiku. Czy chcesz je odrzucić?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Anuluj')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.orange),
            onPressed: () {
              Navigator.pop(ctx);
              onDiscard();
            },
            child: const Text('Odrzuć zmiany'),
          ),
        ],
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _loadSchedule();
  }

  Future<void> _loadSchedule() async {
    try {
      final api = ref.read(apiServiceProvider);
      final schedules = await api.getManagerSchedule(_selectedWeekStart, _selectedWeekEnd);
      final shifts = await api.getShifts();
      final roles = await api.getRoles();
      final users = await api.getUsers();
      
      setState(() {
        _scheduleEntries = schedules;
        _originalEntries = List.from(schedules);
        _shifts = shifts;
        _roles = roles;
        _users = users.where((u) => u.isEmployee).toList();
        _hasUnsavedChanges = false;
        _isFirstEdit = true;
        if (schedules.isNotEmpty) {
          _lastResult = {'status': 'success', 'count': schedules.length};
        }
      });
    } catch (e) {
      // Silently fail - no schedule exists yet
      setState(() {
        _scheduleEntries = [];
        _shifts = [];
        _roles = [];
        _users = [];
      });
    }
  }

  void _showAddAssignmentDialog(DateTime date, int shiftId) {
    String? selectedUserId;
    int? selectedRoleId;

    final shift = _shifts.firstWhere((s) => s.id == shiftId);

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text('Dodaj przypisanie'),
          content: SizedBox(
            width: 300,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${DateFormat('EEEE, d MMM', 'pl_PL').format(date)} - ${shift.name}',
                  style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  decoration: InputDecoration(
                    labelText: 'Pracownik',
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  value: selectedUserId,
                  items: _users.map((u) => DropdownMenuItem(
                    value: u.id,
                    child: Text(u.fullName),
                  )).toList(),
                  onChanged: (v) => setDialogState(() => selectedUserId = v),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<int>(
                  decoration: InputDecoration(
                    labelText: 'Rola',
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  value: selectedRoleId,
                  items: _roles.map((r) => DropdownMenuItem(
                    value: r.id,
                    child: Text(r.name),
                  )).toList(),
                  onChanged: (v) => setDialogState(() => selectedRoleId = v),
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
              onPressed: (selectedUserId != null && selectedRoleId != null)
                  ? () {
                      Navigator.pop(context);
                      _addLocalAssignment(date, shiftId, selectedUserId!, selectedRoleId!);
                    }
                  : null,
              child: const Text('Dodaj'),
            ),
          ],
        ),
      ),
    );
  }

  void _addLocalAssignment(DateTime date, int shiftId, String userId, int roleId) {
    final user = _users.firstWhere((u) => u.id == userId);
    final role = _roles.firstWhere((r) => r.id == roleId);
    final shift = _shifts.firstWhere((s) => s.id == shiftId);
    
    final newEntry = ScheduleEntry(
      id: 'local_${_localIdCounter--}',
      date: date,
      shiftDefId: shiftId,
      userId: userId,
      roleId: roleId,
      isPublished: false,
      userName: user.fullName,
      roleName: role.name,
      shiftName: shift.name,
    );
    
    // Show info banner on first edit
    if (_isFirstEdit && _originalEntries.isNotEmpty) {
      _isFirstEdit = false;
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Row(
            children: [
              Icon(Icons.info_outline, color: Colors.blue.shade600),
              const SizedBox(width: 8),
              const Text('Informacja'),
            ],
          ),
          content: const Text(
            'Edytujesz wygenerowany grafik.\n\n'
            '• Kliknij "Zapisz zmiany" aby zachować edycje\n'
            '• Ponowne wygenerowanie grafiku usunie Twoje zmiany\n'
            '• Możesz dodać wielu pracowników do tej samej zmiany',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Rozumiem'),
            ),
          ],
        ),
      );
    }
    
    setState(() {
      _scheduleEntries.add(newEntry);
      _hasUnsavedChanges = true;
    });
    _updateUnsavedChanges(true);
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Przypisanie dodane (zapisz aby zachować)'),
          backgroundColor: Colors.blue.shade600,
          action: SnackBarAction(
            label: 'Zapisz',
            textColor: Colors.white,
            onPressed: _saveChanges,
          ),
        ),
      );
    }
  }

  void _showEditAssignmentDialog(ScheduleEntry entry) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Edytuj przypisanie'),
        content: SizedBox(
          width: 300,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${DateFormat('EEEE, d MMM', 'pl_PL').format(entry.date)}',
                style: GoogleFonts.inter(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              Text('Pracownik: ${entry.userName}'),
              Text('Rola: ${entry.roleName}'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Zamknij'),
          ),
          FilledButton.tonal(
            style: FilledButton.styleFrom(backgroundColor: Colors.red.shade100),
            onPressed: () {
              Navigator.pop(context);
              _removeLocalAssignment(entry.id);
            },
            child: Text('Usuń', style: TextStyle(color: Colors.red.shade700)),
          ),
        ],
      ),
    );
  }

  void _removeLocalAssignment(String scheduleId) {
    setState(() {
      _scheduleEntries.removeWhere((e) => e.id == scheduleId);
      _hasUnsavedChanges = true;
    });
    _updateUnsavedChanges(true);
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Przypisanie usunięte (zapisz aby zachować)'),
          backgroundColor: Colors.orange.shade600,
          action: SnackBarAction(
            label: 'Zapisz',
            textColor: Colors.white,
            onPressed: _saveChanges,
          ),
        ),
      );
    }
  }

  Future<void> _saveChanges() async {
    if (!_hasUnsavedChanges) return;
    
    setState(() => _isSaving = true);
    
    try {
      final api = ref.read(apiServiceProvider);
      await api.saveBatchSchedule(
        _selectedWeekStart,
        _selectedWeekEnd,
        _scheduleEntries,
      );
      
      setState(() {
        _isSaving = false;
        _hasUnsavedChanges = false;
        _originalEntries = List.from(_scheduleEntries);
      });
      _updateUnsavedChanges(false);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('✓ Zmiany zapisane'),
            backgroundColor: Colors.green.shade600,
          ),
        );
      }
    } catch (e) {
      setState(() => _isSaving = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd zapisu: $e'), backgroundColor: Colors.red.shade600),
        );
      }
    }
  }

  Future<void> _generateSchedule() async {
    // Warning if unsaved changes
    if (_hasUnsavedChanges) {
      final proceed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Uwaga'),
          content: const Text('Wygenerowanie nowego grafiku usunie Twoje obecne zmiany. Kontynuować?'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Anuluj')),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Colors.orange),
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Kontynuuj'),
            ),
          ],
        ),
      );
      if (proceed != true) return;
    }
    
    setState(() => _isGenerating = true);

    try {
      final result = await ref.read(apiServiceProvider).generateSchedule(
            _selectedWeekStart,
            _selectedWeekEnd,
          );

      setState(() {
        _lastResult = result;
        _isGenerating = false;
      });

      // Reload the schedule to display it
      await _loadSchedule();

      if (mounted) {
        final status = result['status'];
        if (status == 'success') {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('✓ Wygenerowano grafik (${result['count']} przypisań)'),
              backgroundColor: Colors.green,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('⚠ Nie udało się wygenerować grafiku - sprawdź wymagania i dostępność'),
              backgroundColor: Colors.orange,
            ),
          );
        }
      }
    } catch (e) {
      setState(() => _isGenerating = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Generator Grafiku',
            style: GoogleFonts.outfit(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          
          // Week Selector
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Row(
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
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton.icon(
                      onPressed: _isGenerating ? null : _generateSchedule,
                      icon: _isGenerating
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Icon(Icons.auto_awesome),
                      label: Text(
                        _isGenerating ? 'Generowanie...' : 'Generuj Grafik (AI)',
                        style: const TextStyle(fontSize: 16),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.indigo.shade700,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                  if (_hasUnsavedChanges) ...[
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: _isSaving ? null : _saveChanges,
                        icon: _isSaving
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.save),
                        label: Text(
                          _isSaving ? 'Zapisywanie...' : 'Zapisz zmiany',
                          style: const TextStyle(fontSize: 16),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.green.shade600,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 24),
          
          // Results / Schedule Display
          if (_scheduleEntries.isNotEmpty && _shifts.isNotEmpty) ...[
            ScheduleViewer(
              schedules: _scheduleEntries,
              shifts: _shifts,
              roles: _roles,
              weekStart: _selectedWeekStart,
              onEmptyCellTap: _showAddAssignmentDialog,
              onAssignmentTap: _showEditAssignmentDialog,
            ),
          ] else if (_lastResult != null && _lastResult!['status'] != 'success') ...[
            Text(
              'Wyniki',
              style: GoogleFonts.outfit(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.warning,
                          color: Colors.orange,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Niewykonalne',
                          style: GoogleFonts.inter(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Liczba przypisań: ${_lastResult!['count']}',
                      style: GoogleFonts.inter(fontSize: 14),
                    ),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.orange.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.orange.shade200),
                        ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Możliwe przyczyny:',
                            style: GoogleFonts.inter(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '• Za mało pracowników z odpowiednimi rolami\n'
                            '• Zbyt wiele osób niedostępnych\n'
                            '• Wymagania przekraczają dostępność',
                            style: GoogleFonts.inter(fontSize: 13),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ] else ...[
            Center(
              child: Column(
                children: [
                  Icon(
                    Icons.calendar_today,
                    size: 64,
                    color: Colors.grey.shade400,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Wybierz tydzień i wygeneruj grafik',
                    style: GoogleFonts.inter(
                      fontSize: 16,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
            ),
          ],
          
          const SizedBox(height: 24),
          
          // Instructions
          Card(
            color: Colors.blue.shade50,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.info_outline, color: Colors.blue.shade700),
                      const SizedBox(width: 8),
                      Text(
                        'Jak to działa?',
                        style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.blue.shade900,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    '1. Upewnij się, że zdefiniowałeś role i zmiany w zakładce "Konfiguracja"\n'
                    '2. Ustaw wymagania obsadowe (ile osób potrzebujesz na każdej zmianie)\n'
                    '3. Poczekaj aż pracownicy wypełnią swoją dostępność\n'
                    '4. Kliknij "Generuj Grafik" - algorytm Google OR-Tools automatycznie przypisze pracowników',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      color: Colors.blue.shade900,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
