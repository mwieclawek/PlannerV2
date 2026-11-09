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
  bool _isPublishing = false;
  bool _hasUnsavedChanges = false;
  Map<String, dynamic>? _lastResult;
  List<ScheduleEntry> _scheduleEntries = [];
  List<ScheduleEntry> _originalEntries = []; // For tracking changes
  List<StaffingWarning> _warnings = []; // Staffing warnings
  List<ShiftDefinition> _shifts = [];
  List<JobRole> _roles = [];
  List<TeamMember> _users = [];
  List<Map<String, dynamic>> _employeeHours = [];
  bool _isLoadingStats = false;
  int _localIdCounter = -1; // For generating temporary IDs
  bool _isFirstEdit = true; // To show info banner on first edit
  Map<String, dynamic>? _wfmPredictions;
  bool _isLoadingPredictions = false;
  Map<int, double> _shiftDriftHoursMap = {};
  double _overallDriftRatio = 1.0;

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

  DateTime get _selectedWeekEnd =>
      _selectedWeekStart.add(const Duration(days: 6));

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
      _warnings = [];
      _hasUnsavedChanges = false;
      _isFirstEdit = true;
      _lastResult = null;
    });
    _loadSchedule();
  }

  void _showUnsavedChangesWarning(VoidCallback onDiscard) {
    showDialog(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Niezapisane zmiany'),
            content: const Text(
              'Masz niezapisane zmiany w grafiku. Czy chcesz je odrzucić?',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Anuluj'),
              ),
              FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: Theme.of(ctx).colorScheme.tertiary,
                ),
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

  Future<void> _loadEmployeeHours() async {
    setState(() => _isLoadingStats = true);
    try {
      final api = ref.read(apiServiceProvider);
      // Load stats for the month of the selected week start
      final stats = await api.getEmployeeHours(
        _selectedWeekStart.month,
        _selectedWeekStart.year,
      );
      setState(() {
        _employeeHours = stats;
        _isLoadingStats = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _isLoadingStats = false);
      }
    }
  }

  Future<void> _loadWfmPredictions() async {
    setState(() => _isLoadingPredictions = true);
    try {
      final api = ref.read(apiServiceProvider);
      final data = await api.getWfmPredictions(
        _selectedWeekStart,
        _selectedWeekEnd,
      );
      if (!mounted) return;
      final simData = data['labor_cost_simulation'] as Map<String, dynamic>?;
      final rawDriftMap =
          simData?['shift_drift_hours_map'] as Map<String, dynamic>? ?? {};
      final parsedDriftMap = <int, double>{};
      for (final entry in rawDriftMap.entries) {
        final k = int.tryParse(entry.key);
        final v = (entry.value as num?)?.toDouble();
        if (k != null && v != null) {
          parsedDriftMap[k] = v;
        }
      }
      final ratio =
          (simData?['overall_drift_ratio'] as num?)?.toDouble() ?? 1.0;
      setState(() {
        _wfmPredictions = data;
        _shiftDriftHoursMap = parsedDriftMap;
        _overallDriftRatio = ratio >= 1.0 ? ratio : 1.0;
        _isLoadingPredictions = false;
      });
    } catch (_) {
      if (mounted) {
        setState(() => _isLoadingPredictions = false);
      }
    }
  }

  Future<void> _loadSchedule() async {
    _loadEmployeeHours();
    _loadWfmPredictions();
    try {
      final api = ref.read(apiServiceProvider);
      final schedules = await api.getManagerSchedule(
        _selectedWeekStart,
        _selectedWeekEnd,
      );
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
      // Schedule loading failed, but still try to load metadata for generation
      try {
        final api = ref.read(apiServiceProvider);
        final shifts = await api.getShifts();
        final roles = await api.getRoles();
        final users = await api.getUsers();
        setState(() {
          _scheduleEntries = [];
          _shifts = shifts;
          _roles = roles;
          _users = users.where((u) => u.isEmployee).toList();
        });
      } catch (_) {
        // Complete failure - clear everything
        setState(() {
          _scheduleEntries = [];
          _shifts = [];
          _roles = [];
          _users = [];
        });
      }
    }
  }

  void _showAddAssignmentDialog(DateTime date, int shiftId) async {
    String? selectedUserId;
    int? selectedRoleId;

    final shift = _shifts.firstWhere((s) => s.id == shiftId);

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    List<AvailableEmployee> availableEmployees = [];
    try {
      final api = ref.read(apiServiceProvider);
      availableEmployees = await api.getAvailableEmployeesForShift(
        date,
        shiftId,
      );
    } catch (e) {
      if (mounted) {
        Navigator.pop(context); // pop loading
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Błąd: $e')));
      }
      return;
    }

    if (!mounted) return;
    Navigator.pop(context); // pop loading

    // Group employees
    final preferred =
        availableEmployees
            .where((e) => e.availabilityStatus == 'PREFERRED')
            .toList();
    final available =
        availableEmployees
            .where(
              (e) => ['AVAILABLE', 'UNKNOWN'].contains(e.availabilityStatus),
            )
            .toList();
    final unavailableButSelectable =
        availableEmployees
            .where((e) => e.availabilityStatus == 'UNAVAILABLE')
            .toList();
    final alreadyScheduled =
        availableEmployees
            .where(
              (e) => [
                'ALREADY_SCHEDULED_THIS',
                'ALREADY_SCHEDULED_OTHER',
              ].contains(e.availabilityStatus),
            )
            .toList();

    showDialog(
      context: context,
      builder:
          (context) => StatefulBuilder(
            builder:
                (context, setDialogState) => AlertDialog(
                  title: const Text('Dodaj przypisanie'),
                  content: SizedBox(
                    width: 400,
                    height: 500,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          '${DateFormat('EEEE, d MMM', 'pl_PL').format(date)} - ${shift.name}',
                          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 16),
                        Expanded(
                          child: Container(
                            decoration: BoxDecoration(
                              border: Border.all(
                                color:
                                    Theme.of(
                                      context,
                                    ).colorScheme.outlineVariant,
                              ),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: ListView(
                              padding: const EdgeInsets.all(8),
                              children: [
                                if (preferred.isNotEmpty) ...[
                                  _buildSectionHeader(
                                    'Chcą pracować',
                                    preferred.length,
                                    Colors.green,
                                  ),
                                  ...preferred.map(
                                    (e) => _buildEmployeeTile(
                                      e,
                                      selectedUserId,
                                      (id) => setDialogState(
                                        () => selectedUserId = id,
                                      ),
                                      context,
                                    ),
                                  ),
                                ],
                                if (available.isNotEmpty) ...[
                                  const SizedBox(height: 8),
                                  _buildSectionHeader(
                                    'Neutralni / Dostępni',
                                    available.length,
                                    Colors.blue,
                                  ),
                                  ...available.map(
                                    (e) => _buildEmployeeTile(
                                      e,
                                      selectedUserId,
                                      (id) => setDialogState(
                                        () => selectedUserId = id,
                                      ),
                                      context,
                                    ),
                                  ),
                                ],
                                if (unavailableButSelectable.isNotEmpty) ...[
                                  const SizedBox(height: 8),
                                  _buildSectionHeader(
                                    'Niedostępni',
                                    unavailableButSelectable.length,
                                    Colors.orange,
                                  ),
                                  ...unavailableButSelectable.map(
                                    (e) => _buildEmployeeTile(
                                      e,
                                      selectedUserId,
                                      (id) => setDialogState(
                                        () => selectedUserId = id,
                                      ),
                                      context,
                                      isSelectable: true,
                                      showWarning: true,
                                    ),
                                  ),
                                ],
                                if (alreadyScheduled.isNotEmpty) ...[
                                  const SizedBox(height: 8),
                                  _buildSectionHeader(
                                    'Mają już zmianę',
                                    alreadyScheduled.length,
                                    Colors.red,
                                  ),
                                  ...alreadyScheduled.map(
                                    (e) => _buildEmployeeTile(
                                      e,
                                      selectedUserId,
                                      (id) {},
                                      context,
                                      isSelectable: false,
                                      showWarning: true,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        DropdownButtonFormField<int>(
                          decoration: InputDecoration(
                            labelText: 'Rola',
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                          value: selectedRoleId,
                          items:
                              _roles
                                  .map(
                                    (r) => DropdownMenuItem(
                                      value: r.id,
                                      child: Text(r.name),
                                    ),
                                  )
                                  .toList(),
                          onChanged:
                              (v) => setDialogState(() => selectedRoleId = v),
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
                      onPressed:
                          (selectedUserId != null && selectedRoleId != null)
                              ? () {
                                Navigator.pop(context);
                                _addLocalAssignment(
                                  date,
                                  shiftId,
                                  selectedUserId!,
                                  selectedRoleId!,
                                );
                              }
                              : null,
                      child: const Text('Dodaj'),
                    ),
                  ],
                ),
          ),
    );
  }

  Widget _buildSectionHeader(String title, int count, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
      child: Row(
        children: [
          Icon(Icons.circle, size: 12, color: color),
          const SizedBox(width: 8),
          Text(
            '$title ($count)',
            style: GoogleFonts.inter(
              fontWeight: FontWeight.bold,
              fontSize: 13,
              color: Colors.grey.shade700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmployeeTile(
    AvailableEmployee emp,
    String? selectedId,
    Function(String) onSelect,
    BuildContext context, {
    bool isSelectable = true,
    bool showWarning = false,
  }) {
    final isSelected = emp.userId == selectedId;
    final hoursText =
        emp.targetHours != null
            ? '${emp.hoursThisMonth}/${emp.targetHours}h'
            : '${emp.hoursThisMonth}h';

    final overTarget =
        emp.targetHours != null && emp.hoursThisMonth >= emp.targetHours!;

    return Opacity(
      opacity: isSelectable ? 1.0 : 0.5,
      child: InkWell(
        onTap: isSelectable ? () => onSelect(emp.userId) : null,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 2),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color:
                isSelected
                    ? Theme.of(
                      context,
                    ).colorScheme.primaryContainer.withOpacity(0.5)
                    : Colors.transparent,
            border: Border.all(
              color:
                  isSelected
                      ? Theme.of(context).colorScheme.primary
                      : Colors.transparent,
              width: 2,
            ),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              if (emp.availabilityStatus == 'PREFERRED')
                const Icon(Icons.star, size: 16, color: Colors.amber)
              else if (showWarning)
                const Icon(Icons.block, size: 16, color: Colors.red),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      emp.fullName,
                      style: GoogleFonts.inter(
                        fontWeight:
                            isSelected ? FontWeight.bold : FontWeight.w500,
                        decoration:
                            !isSelectable ? TextDecoration.lineThrough : null,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 4,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        ...emp.jobRoles.map(
                          (r) => Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 4,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Color(
                                int.parse(r.colorHex.replaceFirst('#', '0xFF')),
                              ).withOpacity(0.2),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              r.name,
                              style: GoogleFonts.inter(
                                fontSize: 10,
                                color: Color(
                                  int.parse(
                                    r.colorHex.replaceFirst('#', '0xFF'),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '•  $hoursText',
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            color:
                                overTarget
                                    ? Colors.orange.shade800
                                    : Colors.grey.shade600,
                            fontWeight:
                                overTarget
                                    ? FontWeight.bold
                                    : FontWeight.normal,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _addLocalAssignment(
    DateTime date,
    int shiftId,
    String userId,
    int roleId,
  ) {
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
      startTime: shift.startTime,
      endTime: shift.endTime,
    );

    // Show info banner on first edit
    if (_isFirstEdit && _originalEntries.isNotEmpty) {
      _isFirstEdit = false;
      showDialog(
        context: context,
        builder:
            (ctx) => AlertDialog(
              title: Row(
                children: [
                  Icon(
                    Icons.info_outline,
                    color: Theme.of(ctx).colorScheme.primary,
                  ),
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
          backgroundColor: Theme.of(context).colorScheme.primary,
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
      builder:
          (context) => AlertDialog(
            title: const Text('Edytuj przypisanie'),
            content: SizedBox(
              width: 300,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    DateFormat('EEEE, d MMM', 'pl_PL').format(entry.date),
                    style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 8),
                  Text('Pracownik: ${entry.userName}'),
                  Text('Rola: ${entry.roleName}'),
                ],
              ),
            ),
            actions: [
              TextButton.icon(
                icon: const Icon(Icons.history, size: 16),
                label: const Text('Historia zmian'),
                onPressed: () {
                  Navigator.pop(context);
                  _showAuditLogDialog(entry);
                },
              ),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Zamknij'),
              ),
              FilledButton.tonal(
                style: FilledButton.styleFrom(
                  backgroundColor: Theme.of(context).colorScheme.errorContainer,
                ),
                onPressed: () {
                  Navigator.pop(context);
                  _removeLocalAssignment(entry.id);
                },
                child: Text(
                  'Usuń',
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            ],
          ),
    );
  }

  Future<void> _showAuditLogDialog(ScheduleEntry entry) async {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            const Icon(Icons.history, size: 22),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Historia: ${entry.userName} (${DateFormat('d MMM', 'pl_PL').format(entry.date)})',
                style: const TextStyle(fontSize: 16),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        content: SizedBox(
          width: 450,
          child: FutureBuilder<List<Map<String, dynamic>>>(
            future: ref.read(apiServiceProvider).getShiftAuditLog(entry.id),
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(
                  child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()),
                );
              }
              if (snapshot.hasError) {
                return Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text('Błąd pobierania historii: ${snapshot.error}', style: const TextStyle(color: Colors.red)),
                );
              }
              final logs = snapshot.data ?? [];
              if (logs.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: Text('Brak wpisów w historii dla tej zmiany')),
                );
              }
              return ListView.separated(
                shrinkWrap: true,
                itemCount: logs.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, idx) {
                  final log = logs[idx];
                  final action = log['action'] ?? 'UNKNOWN';
                  final author = log['changed_by_user_name'] ?? 'System';
                  final createdStr = log['created_at'] != null
                      ? DateFormat('d MMM yyyy HH:mm', 'pl_PL').format(DateTime.parse(log['created_at']))
                      : '';
                  final oldVal = log['old_value'];
                  final newVal = log['new_value'];

                  Color badgeColor = Colors.blue.shade100;
                  Color textColor = Colors.blue.shade900;
                  if (action == 'DELETED') {
                    badgeColor = Colors.red.shade100;
                    textColor = Colors.red.shade900;
                  } else if (action == 'CREATED') {
                    badgeColor = Colors.green.shade100;
                    textColor = Colors.green.shade900;
                  } else if (action == 'SWAPPED') {
                    badgeColor = Colors.purple.shade100;
                    textColor = Colors.purple.shade900;
                  }

                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(color: badgeColor, borderRadius: BorderRadius.circular(4)),
                              child: Text(action, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: textColor)),
                            ),
                            const Spacer(),
                            Text(createdStr, style: const TextStyle(fontSize: 11, color: Colors.grey)),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text('Zmienione przez: $author', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
                        if (oldVal != null || newVal != null)
                          Text('${oldVal ?? "brak"} → ${newVal ?? "brak"}', style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                      ],
                    ),
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
          backgroundColor: Theme.of(context).colorScheme.tertiary,
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
      _updateUnsavedChanges(false);
      await _loadSchedule(); // Auto-refresh to ensure data consistency

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
          SnackBar(
            content: Text('Błąd zapisu: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }

  Future<void> _publishSchedule() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Publikacja Grafiku'),
        content: const Text(
          'Czy na pewno chcesz opublikować grafik na ten tydzień? '
          'Pracownicy zobaczą swoje zmiany i otrzymają powiadomienia, a grafik zostanie zsynchronizowany z Google Calendar.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Opublikuj'),
          ),
        ],
      ),
    );
    if (confirm != true) return;

    setState(() => _isPublishing = true);
    try {
      final api = ref.read(apiServiceProvider);
      final res = await api.publishSchedule(_selectedWeekStart, _selectedWeekEnd);
      final count = res['count'] ?? 0;
      await _loadSchedule();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✓ Opublikowano grafik ($count zmian). Powiadomienia zostały wysłane.'),
            backgroundColor: Colors.teal.shade700,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Błąd publikacji grafiku: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isPublishing = false);
      }
    }
  }

  Map<String, String> _computeShiftWarnings() {
    final Map<String, String> warnings = {};

    // Group schedules by user
    final Map<String, List<ScheduleEntry>> byUser = {};
    for (final s in _scheduleEntries) {
      byUser.putIfAbsent(s.userId, () => []).add(s);
    }

    final Map<String, TeamMember> userMap = {for (final u in _users) u.id: u};

    // Calculate monthly hours per user from _employeeHours
    final Map<String, double> userMonthHours = {};
    for (final stat in _employeeHours) {
      final uid = stat['user_id'] as String?;
      final hrs = (stat['total_hours'] as num?)?.toDouble() ?? 0.0;
      if (uid != null) userMonthHours[uid] = hrs;
    }

    for (final entry in byUser.entries) {
      final uid = entry.key;
      final userShifts = entry.value;
      final user = userMap[uid];

      // Sort user shifts chronologically
      userShifts.sort((a, b) {
        final c = a.date.compareTo(b.date);
        if (c != 0) return c;
        return a.startTime.compareTo(b.startTime);
      });

      // 1. Check 11-hour daily rest between consecutive shifts ("Clopening")
      for (int i = 0; i < userShifts.length - 1; i++) {
        final curr = userShifts[i];
        final next = userShifts[i + 1];

        final currParts = curr.startTime.split(':');
        final currEndParts = curr.endTime.split(':');
        final nextParts = next.startTime.split(':');

        if (currParts.length == 2 && currEndParts.length == 2 && nextParts.length == 2) {
          final currStart = DateTime(
            curr.date.year,
            curr.date.month,
            curr.date.day,
            int.tryParse(currParts[0]) ?? 0,
            int.tryParse(currParts[1]) ?? 0,
          );
          var currEnd = DateTime(
            curr.date.year,
            curr.date.month,
            curr.date.day,
            int.tryParse(currEndParts[0]) ?? 0,
            int.tryParse(currEndParts[1]) ?? 0,
          );
          if (currEnd.isBefore(currStart) || currEnd.isAtSameMomentAs(currStart)) {
            currEnd = currEnd.add(const Duration(days: 1));
          }

          final nextStart = DateTime(
            next.date.year,
            next.date.month,
            next.date.day,
            int.tryParse(nextParts[0]) ?? 0,
            int.tryParse(nextParts[1]) ?? 0,
          );

          if (nextStart.isAfter(currEnd)) {
            final restHours = nextStart.difference(currEnd).inMinutes / 60.0;
            if (restHours < 11.0) {
              const msg = 'Naruszenie normy odpoczynku dobowego (< 11h)';
              warnings[curr.id] = msg;
              warnings[next.id] = msg;
            }
          }
        }
      }

      // 2. Check monthly target hours limit
      if (user != null && user.targetHoursPerMonth != null) {
        final totalHrs = userMonthHours[uid] ?? 0.0;
        if (totalHrs > user.targetHoursPerMonth!) {
          for (final s in userShifts) {
            final existing = warnings[s.id];
            final targetMsg =
                'Przekroczono miesięczny cel godzin (${totalHrs.toStringAsFixed(1)}/${user.targetHoursPerMonth}h)';
            warnings[s.id] = existing != null ? '$existing\n$targetMsg' : targetMsg;
          }
        }
      }
    }

    return warnings;
  }

  Future<void> _generateSchedule() async {
    // Warning if unsaved changes
    if (_hasUnsavedChanges) {
      final proceed = await showDialog<bool>(
        context: context,
        builder:
            (ctx) => AlertDialog(
              title: const Text('Uwaga'),
              content: const Text(
                'Wygenerowanie nowego grafiku usunie Twoje obecne zmiany. Kontynuować?',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx, false),
                  child: const Text('Anuluj'),
                ),
                FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: Theme.of(ctx).colorScheme.tertiary,
                  ),
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
      final api = ref.read(apiServiceProvider);

      // Ensure we have shifts, roles, users loaded (required for display)
      if (_shifts.isEmpty || _roles.isEmpty || _users.isEmpty) {
        final shifts = await api.getShifts();
        final roles = await api.getRoles();
        final users = await api.getUsers();
        setState(() {
          _shifts = shifts;
          _roles = roles;
          _users = users.where((u) => u.isEmployee).toList();
        });
      }

      final result = await api.generateSchedule(
        _selectedWeekStart,
        _selectedWeekEnd,
      );

      final status = result['status'];

      if (status == 'success') {
        // Parse schedules directly from result (draft mode doesn't save to DB)
        final List<dynamic> schedulesJson = result['schedules'] ?? [];
        final List<ScheduleEntry> generatedEntries = [];

        for (final s in schedulesJson) {
          // Find matching user, role, shift names
          final userId = s['user_id']?.toString() ?? '';
          final roleId = s['role_id'] as int? ?? 0;
          final shiftDefId = s['shift_def_id'] as int? ?? 0;

          final user = _users.firstWhere(
            (u) => u.id == userId,
            orElse:
                () => TeamMember(
                  id: userId,
                  username: '',
                  fullName: 'Unknown',
                  roleSystem: 'EMPLOYEE',
                  jobRoleIds: [],
                ),
          );
          final role = _roles.firstWhere(
            (r) => r.id == roleId,
            orElse:
                () => JobRole(id: roleId, name: 'Unknown', colorHex: '#888888'),
          );
          final shift = _shifts.firstWhere(
            (sh) => sh.id == shiftDefId,
            orElse:
                () => ShiftDefinition(
                  id: shiftDefId,
                  name: 'Unknown',
                  startTime: '00:00',
                  endTime: '00:00',
                ),
          );

          generatedEntries.add(
            ScheduleEntry(
              id: s['id']?.toString() ?? 'gen_${generatedEntries.length}',
              date: DateTime.parse(s['date'].toString()),
              shiftDefId: shiftDefId,
              userId: userId,
              roleId: roleId,
              isPublished: false,
              userName: user.fullName,
              roleName: role.name,
              shiftName: shift.name,
              startTime: shift.startTime,
              endTime: shift.endTime,
            ),
          );
        }

        // Parse warnings from result
        final List<dynamic> warningsJson = result['warnings'] ?? [];
        final List<StaffingWarning> parsedWarnings =
            warningsJson
                .map((w) => StaffingWarning.fromJson(w as Map<String, dynamic>))
                .toList();

        setState(() {
          _scheduleEntries = generatedEntries;
          _originalEntries = List.from(generatedEntries);
          _warnings = parsedWarnings;
          _lastResult = result;
          _isGenerating = false;
          _hasUnsavedChanges = true; // Mark as unsaved since it's a draft
          _isFirstEdit = true;
        });

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                '✓ Wygenerowano grafik (${result['count']} przypisań)',
              ),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        setState(() {
          _lastResult = result;
          _isGenerating = false;
        });

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                '⚠ Nie udało się wygenerować grafiku - sprawdź wymagania i dostępność',
              ),
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
          );
        }
      }
    } catch (e) {
      setState(() => _isGenerating = false);
      if (mounted) {
        // Enhanced error handling
        String errorMessage = 'Wystąpił nieoczekiwany błąd.';
        if (e.toString().contains('400')) {
          errorMessage =
              'Nie znaleziono rozwiązania dla podanych wymagań. Spróbuj dodać więcej pracowników lub zmniejszyć wymagania.';
        } else if (e.toString().contains('timeout')) {
          errorMessage = 'Przekroczono czas oczekiwania na solver.';
        } else {
          errorMessage = 'Błąd generowania: $e';
        }

        showDialog(
          context: context,
          builder:
              (ctx) => AlertDialog(
                title: const Text('Błąd Generowania'),
                content: Text(errorMessage),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('OK'),
                  ),
                ],
              ),
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
                      icon:
                          _isGenerating
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
                        _isGenerating
                            ? 'Generowanie...'
                            : 'Generuj Grafik (AI)',
                        style: const TextStyle(fontSize: 16),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Theme.of(context).colorScheme.primary,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                  if (_isGenerating) ...[
                    const SizedBox(height: 12),
                    const LinearProgressIndicator(minHeight: 4),
                    const SizedBox(height: 8),
                    Text(
                      'Przetwarzanie może potrwać do 30 sekund...',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: Colors.grey.shade600,
                        fontStyle: FontStyle.italic,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                  if (_hasUnsavedChanges) ...[
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: _isSaving ? null : _saveChanges,
                        icon:
                            _isSaving
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
                          backgroundColor:
                              Theme.of(context).colorScheme.secondary,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                    ),
                  ],
                  if (_scheduleEntries.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed:
                            _isPublishing || _isSaving ? null : _publishSchedule,
                        icon:
                            _isPublishing
                                ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                                : const Icon(Icons.send_rounded),
                        label: Text(
                          _isPublishing ? 'Publikowanie...' : 'Opublikuj grafik',
                          style: const TextStyle(fontSize: 16),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.teal.shade700,
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

          const SizedBox(height: 16),

          // Expandable Panel: Analityka i Predykcja WFM (AI Worker)
          _buildWfmAnalyticsPanel(context),

          const SizedBox(height: 12),

          // Live Bar: Symulator Kosztu Tygodnia (Live Labor Cost)
          _buildLiveLaborCostBar(context),

          const SizedBox(height: 20),

          // Results / Schedule Display
          if (_scheduleEntries.isNotEmpty && _shifts.isNotEmpty) ...[
            ScheduleViewer(
              schedules: _scheduleEntries,
              shifts: _shifts,
              roles: _roles,
              weekStart: _selectedWeekStart,
              warnings: _warnings,
              shiftWarnings: _computeShiftWarnings(),
              onEmptyCellTap: _showAddAssignmentDialog,
              onAssignmentTap: _showEditAssignmentDialog,
            ),
          ] else if (_lastResult != null &&
              _lastResult!['status'] != 'success') ...[
            Text(
              'Wyniki',
              style: GoogleFonts.outfit(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
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
                          color: Theme.of(context).colorScheme.error,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Niewykonalne',
                          style: GoogleFonts.inter(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Theme.of(context).colorScheme.error,
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
                        color: Theme.of(
                          context,
                        ).colorScheme.errorContainer.withOpacity(0.3),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: Theme.of(context).colorScheme.errorContainer,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Możliwe przyczyny:',
                            style: GoogleFonts.inter(
                              fontWeight: FontWeight.w600,
                              color:
                                  Theme.of(
                                    context,
                                  ).colorScheme.onErrorContainer,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '• Za mało pracowników z odpowiednimi rolami\n'
                            '• Zbyt wiele osób niedostępnych\n'
                            '• Wymagania przekraczają dostępność',
                            style: GoogleFonts.inter(
                              fontSize: 13,
                              color:
                                  Theme.of(
                                    context,
                                  ).colorScheme.onErrorContainer,
                            ),
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
            color: Theme.of(
              context,
            ).colorScheme.secondaryContainer.withOpacity(0.4),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.info_outline,
                        color:
                            Theme.of(context).colorScheme.onSecondaryContainer,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Jak to działa?',
                        style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color:
                              Theme.of(
                                context,
                              ).colorScheme.onSecondaryContainer,
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
                      color: Theme.of(context).colorScheme.onSecondaryContainer,
                    ),
                  ),
                ],
              ),
            ),
          ),

          if (_isLoadingStats)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: CircularProgressIndicator(),
              ),
            )
          else if (_employeeHours.isNotEmpty)
            _buildStatsPanel(),
        ],
      ),
    );
  }

  Widget _buildStatsPanel() {
    return Card(
      margin: const EdgeInsets.only(top: 24),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.bar_chart, color: Colors.indigo.shade700),
                const SizedBox(width: 8),
                Text(
                  'Podsumowanie miesiąca (${DateFormat('MMMM', 'pl_PL').format(_selectedWeekStart)})',
                  style: GoogleFonts.outfit(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.indigo.shade900,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _employeeHours.length,
              separatorBuilder:
                  (ctx, i) => Divider(color: Colors.grey.shade200),
              itemBuilder:
                  (ctx, i) => _buildEmployeeStatItem(_employeeHours[i]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmployeeStatItem(Map<String, dynamic> stat) {
    final hasAvailability =
        stat['has_submitted_availability'] as bool? ?? false;
    final totalHours = (stat['total_hours'] as num?)?.toDouble() ?? 0.0;
    final shiftsCount = stat['shift_count'] as int? ?? 0;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          CircleAvatar(
            radius: 16,
            backgroundColor:
                hasAvailability ? Colors.green.shade100 : Colors.grey.shade200,
            child: Icon(
              hasAvailability ? Icons.check : Icons.question_mark,
              size: 16,
              color:
                  hasAvailability
                      ? Colors.green.shade700
                      : Colors.grey.shade500,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  stat['user_name'] ?? 'Unknown',
                  style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                ),
                Text(
                  hasAvailability ? 'Dostępność złożona' : 'Brak dostępności',
                  style: TextStyle(
                    fontSize: 12,
                    color:
                        hasAvailability
                            ? Colors.green.shade700
                            : Colors.grey.shade600,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${totalHours.toStringAsFixed(1)} h',
                style: GoogleFonts.inter(
                  fontWeight: FontWeight.bold,
                  fontSize: 15,
                ),
              ),
              Text(
                '$shiftsCount zmian',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: Colors.grey.shade600,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  WFM Workforce Prediction & Live Labor Cost Simulator Helpers
  // ═══════════════════════════════════════════════════════════════════════════

  double _calcShiftDurationHours(String startTime, String endTime) {
    final startParts = startTime.split(':');
    final endParts = endTime.split(':');
    if (startParts.length < 2 || endParts.length < 2) return 8.0;
    final sh = int.tryParse(startParts[0]) ?? 0;
    final sm = int.tryParse(startParts[1]) ?? 0;
    final eh = int.tryParse(endParts[0]) ?? 0;
    final em = int.tryParse(endParts[1]) ?? 0;
    int startMinutes = sh * 60 + sm;
    int endMinutes = eh * 60 + em;
    if (endMinutes <= startMinutes) {
      endMinutes += 24 * 60;
    }
    return (endMinutes - startMinutes) / 60.0;
  }

  double _resolveEffectiveHourlyRate(
    TeamMember? user,
    int roleId,
    Map<int, JobRole> roleMap,
  ) {
    if (user != null && user.hourlyRate != null && user.hourlyRate! > 0) {
      return user.hourlyRate!;
    }
    final assignedRole = roleMap[roleId];
    if (assignedRole != null &&
        assignedRole.hourlyRate != null &&
        assignedRole.hourlyRate! > 0) {
      return assignedRole.hourlyRate!;
    }
    if (user != null) {
      for (final rid in user.jobRoleIds) {
        final r = roleMap[rid];
        if (r != null && r.hourlyRate != null && r.hourlyRate! > 0) {
          return r.hourlyRate!;
        }
      }
    }
    return 0.0;
  }

  Map<String, dynamic> _computeLiveLaborCostData() {
    final userMap = {for (final u in _users) u.id: u};
    final roleMap = {for (final r in _roles) r.id: r};
    final shiftMap = {for (final s in _shifts) s.id: s};

    double totalPlannedHours = 0.0;
    double totalProjectedHours = 0.0;
    double estimatedPlannedCost = 0.0;
    double projectedCostWithDrift = 0.0;

    final Map<int, Map<String, dynamic>> roleBreakdown = {
      for (final r in _roles)
        r.id: {
          'role_id': r.id,
          'role_name': r.name,
          'color_hex': r.colorHex,
          'planned_hours': 0.0,
          'planned_cost': 0.0,
          'projected_cost_with_drift': 0.0,
          'shifts_count': 0,
        },
    };

    const polishShortDays = ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Ndz'];
    final List<Map<String, dynamic>> dailyCosts = List.generate(7, (idx) {
      final d = _selectedWeekStart.add(Duration(days: idx));
      return {
        'date': d,
        'date_key': DateFormat('yyyy-MM-dd').format(d),
        'day_label': '${polishShortDays[idx]} ${DateFormat('dd.MM').format(d)}',
        'planned_hours': 0.0,
        'planned_cost': 0.0,
        'projected_cost_with_drift': 0.0,
        'shifts_count': 0,
        'is_most_expensive': false,
      };
    });
    final dailyByKey = {
      for (final item in dailyCosts) item['date_key'] as String: item,
    };

    for (final entry in _scheduleEntries) {
      final shift = shiftMap[entry.shiftDefId];
      final startStr = shift?.startTime ?? entry.startTime;
      final endStr = shift?.endTime ?? entry.endTime;
      final plannedHrs = _calcShiftDurationHours(startStr, endStr);

      double driftHrs = _shiftDriftHoursMap[entry.shiftDefId] ?? 0.0;
      if (driftHrs == 0.0 && _overallDriftRatio > 1.0) {
        driftHrs = plannedHrs * (_overallDriftRatio - 1.0);
      }
      final projectedHrs = plannedHrs + driftHrs;

      final user = userMap[entry.userId];
      final rate = _resolveEffectiveHourlyRate(user, entry.roleId, roleMap);

      final pCost = plannedHrs * rate;
      final projCost = projectedHrs * rate;

      totalPlannedHours += plannedHrs;
      totalProjectedHours += projectedHrs;
      estimatedPlannedCost += pCost;
      projectedCostWithDrift += projCost;

      final rStat = roleBreakdown.putIfAbsent(
        entry.roleId,
        () => {
          'role_id': entry.roleId,
          'role_name': entry.roleName,
          'color_hex': '#607D8B',
          'planned_hours': 0.0,
          'planned_cost': 0.0,
          'projected_cost_with_drift': 0.0,
          'shifts_count': 0,
        },
      );
      rStat['planned_hours'] = (rStat['planned_hours'] as double) + plannedHrs;
      rStat['planned_cost'] = (rStat['planned_cost'] as double) + pCost;
      rStat['projected_cost_with_drift'] =
          (rStat['projected_cost_with_drift'] as double) + projCost;
      rStat['shifts_count'] = (rStat['shifts_count'] as int) + 1;

      final dKey = DateFormat('yyyy-MM-dd').format(entry.date);
      final dStat = dailyByKey[dKey];
      if (dStat != null) {
        dStat['planned_hours'] =
            (dStat['planned_hours'] as double) + plannedHrs;
        dStat['planned_cost'] = (dStat['planned_cost'] as double) + pCost;
        dStat['projected_cost_with_drift'] =
            (dStat['projected_cost_with_drift'] as double) + projCost;
        dStat['shifts_count'] = (dStat['shifts_count'] as int) + 1;
      }
    }

    double maxDayCost = 0.0;
    for (final dStat in dailyCosts) {
      final c = dStat['planned_cost'] as double;
      if (c > maxDayCost) maxDayCost = c;
    }
    if (maxDayCost > 0) {
      for (final dStat in dailyCosts) {
        final c = dStat['planned_cost'] as double;
        if ((c - maxDayCost).abs() < 0.01) {
          dStat['is_most_expensive'] = true;
        }
      }
    }

    final avgHourlyCost =
        totalPlannedHours > 0 ? estimatedPlannedCost / totalPlannedHours : 0.0;

    final sortedRoles = roleBreakdown.values.toList()
      ..sort(
        (a, b) => (b['planned_hours'] as double).compareTo(
          a['planned_hours'] as double,
        ),
      );

    return {
      'total_planned_hours': totalPlannedHours,
      'total_projected_hours': totalProjectedHours,
      'estimated_planned_cost': estimatedPlannedCost,
      'projected_cost_with_drift': projectedCostWithDrift,
      'avg_hourly_cost': avgHourlyCost,
      'roles': sortedRoles,
      'daily': dailyCosts,
    };
  }

  Widget _buildLiveLaborCostBar(BuildContext context) {
    final sim = _computeLiveLaborCostData();
    final totalHours = sim['total_planned_hours'] as double;
    final plannedCost = sim['estimated_planned_cost'] as double;
    final projectedCost = sim['projected_cost_with_drift'] as double;
    final avgRate = sim['avg_hourly_cost'] as double;
    final rolesList = sim['roles'] as List<Map<String, dynamic>>;
    final dailyList = sim['daily'] as List<Map<String, dynamic>>;
    final driftDelta = projectedCost - plannedCost;

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.indigo.shade100),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.payments_outlined, color: Colors.indigo.shade700),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Symulator Kosztu Tygodnia (Live Labor Cost)',
                    style: GoogleFonts.outfit(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                      color: Colors.indigo.shade900,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.green.shade200),
                  ),
                  child: Text(
                    'LIVE',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: Colors.green.shade800,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 10,
              children: [
                _buildCostMetricBadge(
                  label: 'Zaplanowane godziny w tygodniu',
                  value: '${totalHours.toStringAsFixed(1)} h',
                  icon: Icons.schedule,
                  color: Colors.blue.shade800,
                  bgColor: Colors.blue.shade50,
                ),
                _buildCostMetricBadge(
                  label: 'Szacowany koszt grafiku (Plan)',
                  value: '${plannedCost.toStringAsFixed(2)} PLN',
                  icon: Icons.account_balance_wallet_outlined,
                  color: Colors.indigo.shade800,
                  bgColor: Colors.indigo.shade50,
                ),
                _buildCostMetricBadge(
                  label: 'Prognozowany koszt z uwzględnieniem dryfu obecności',
                  value:
                      '${projectedCost.toStringAsFixed(2)} PLN${driftDelta > 0.01 ? " (+${driftDelta.toStringAsFixed(2)} PLN)" : ""}',
                  icon: Icons.trending_up,
                  color:
                      driftDelta > 0.01
                          ? Colors.deepOrange.shade800
                          : Colors.teal.shade800,
                  bgColor:
                      driftDelta > 0.01
                          ? Colors.deepOrange.shade50
                          : Colors.teal.shade50,
                ),
                _buildCostMetricBadge(
                  label: 'Średni koszt roboczogodziny',
                  value: '${avgRate.toStringAsFixed(2)} PLN/h',
                  icon: Icons.speed,
                  color: Colors.purple.shade800,
                  bgColor: Colors.purple.shade50,
                ),
              ],
            ),
            if (rolesList.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'Podział godzin i kosztów wg ról:',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey.shade700,
                ),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children:
                    rolesList.map((r) {
                      final rHours = r['planned_hours'] as double;
                      final rCost = r['planned_cost'] as double;
                      final rHex = (r['color_hex'] as String?) ?? '#607D8B';
                      Color roleColor = Colors.blueGrey;
                      try {
                        roleColor = Color(
                          int.parse(rHex.replaceFirst('#', '0xFF')),
                        );
                      } catch (_) {}
                      return Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 5,
                        ),
                        decoration: BoxDecoration(
                          color: roleColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: roleColor.withValues(alpha: 0.4),
                          ),
                        ),
                        child: Text(
                          '${r['role_name']}: ${rHours.toStringAsFixed(1)} h (${rCost.toStringAsFixed(0)} PLN)',
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: roleColor,
                          ),
                        ),
                      );
                    }).toList(),
              ),
            ],
            const SizedBox(height: 12),
            Text(
              'Koszt w podziale na dni tygodnia (podświetlono najdroższe dni):',
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade700,
              ),
            ),
            const SizedBox(height: 6),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children:
                    dailyList.map((d) {
                      final isMax = d['is_most_expensive'] == true;
                      final dHours = d['planned_hours'] as double;
                      final dCost = d['planned_cost'] as double;
                      return Container(
                        margin: const EdgeInsets.only(right: 8),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color:
                              isMax
                                  ? Colors.amber.shade100
                                  : Colors.grey.shade100,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color:
                                isMax
                                    ? Colors.deepOrange.shade400
                                    : Colors.grey.shade300,
                            width: isMax ? 1.8 : 1.0,
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                if (isMax) ...[
                                  Icon(
                                    Icons.local_fire_department,
                                    size: 14,
                                    color: Colors.deepOrange.shade700,
                                  ),
                                  const SizedBox(width: 4),
                                ],
                                Text(
                                  d['day_label'] as String,
                                  style: GoogleFonts.inter(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color:
                                        isMax
                                            ? Colors.deepOrange.shade900
                                            : Colors.grey.shade800,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text(
                              '${dCost.toStringAsFixed(0)} PLN',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color:
                                    isMax
                                        ? Colors.deepOrange.shade900
                                        : Colors.black87,
                              ),
                            ),
                            Text(
                              '${dHours.toStringAsFixed(1)} h',
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                color: Colors.grey.shade700,
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCostMetricBadge({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
    required Color bgColor,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  color: Colors.grey.shade700,
                ),
              ),
              Text(
                value,
                style: GoogleFonts.inter(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildWfmAnalyticsPanel(BuildContext context) {
    final bottleneckForecast =
        _wfmPredictions?['bottleneck_forecast'] as Map<String, dynamic>?;
    final bottlenecks =
        (bottleneckForecast?['bottlenecks'] as List?)
            ?.cast<Map<String, dynamic>>() ??
        [];
    final targetRisks =
        (bottleneckForecast?['employee_target_risks'] as List?)
            ?.cast<Map<String, dynamic>>()
            .where((r) => (r['risk_level'] ?? 'LOW') != 'LOW')
            .toList() ??
        [];

    final driftData =
        _wfmPredictions?['attendance_drift'] as Map<String, dynamic>?;
    final driftingShifts =
        (driftData?['drifting_shifts'] as List?)
            ?.cast<Map<String, dynamic>>() ??
        [];
    final monthlyProj =
        driftData?['monthly_projection'] as Map<String, dynamic>?;

    final stabilityData =
        _wfmPredictions?['shift_stability'] as Map<String, dynamic>?;
    final hotspots =
        (stabilityData?['hotspots'] as List?)?.cast<Map<String, dynamic>>() ??
        [];

    final totalAlerts =
        bottlenecks.length + driftingShifts.length + targetRisks.length;

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color:
              totalAlerts > 0 ? Colors.amber.shade400 : Colors.blueGrey.shade100,
        ),
      ),
      child: ExpansionTile(
        leading: Icon(
          Icons.psychology_outlined,
          color:
              totalAlerts > 0
                  ? Colors.deepOrange.shade700
                  : Colors.indigo.shade700,
        ),
        title: Text(
          'Analityka i Predykcja WFM (AI Worker)',
          style: GoogleFonts.outfit(
            fontSize: 17,
            fontWeight: FontWeight.bold,
          ),
        ),
        subtitle:
            _isLoadingPredictions
                ? const Text('Przeliczanie predykcji kadrowych WFM...')
                : Text(
                  'Wąskie gardła: ${bottlenecks.length} • Dryf zmian: ${driftingShifts.length} • Ryzyka etatowe: ${targetRisks.length}',
                  style: GoogleFonts.inter(fontSize: 12),
                ),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          const Divider(),
          // 1. Bottlenecks
          Row(
            children: [
              Icon(
                Icons.warning_amber_rounded,
                size: 18,
                color: Colors.red.shade700,
              ),
              const SizedBox(width: 6),
              Text(
                '1. Wąskie gardła dyspozycyjności i urlopów (Tydzień / Miesiąc)',
                style: GoogleFonts.inter(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          if (bottlenecks.isEmpty)
            Text(
              'Brak wykrytych wąskich gardeł obsadowych w nadchodzącym okresie.',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: Colors.green.shade700,
              ),
            )
          else
            ...bottlenecks.take(8).map(
              (b) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      b['severity'] == 'CRITICAL'
                          ? Icons.error_outline
                          : Icons.info_outline,
                      size: 15,
                      color:
                          b['severity'] == 'CRITICAL'
                              ? Colors.red.shade700
                              : Colors.orange.shade800,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        b['message']?.toString() ?? '',
                        style: GoogleFonts.inter(fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 12),

          // 2. Attendance Drift
          Row(
            children: [
              Icon(Icons.more_time, size: 18, color: Colors.deepOrange.shade700),
              const SizedBox(width: 6),
              Text(
                '2. Predykcja dryfu godzinowego i nadgodzin (Schedule vs. Attendance)',
                style: GoogleFonts.inter(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          if (monthlyProj != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text(
                'Prognoza na koniec miesiąca: Plan ${monthlyProj['planned_hours']}h (${monthlyProj['planned_cost']} PLN) → '
                'Realne wykonanie z dryfem: ${monthlyProj['projected_actual_hours']}h (${monthlyProj['projected_actual_cost']} PLN)',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Colors.indigo.shade900,
                ),
              ),
            ),
          if (driftingShifts.isEmpty)
            Text(
              'Brak zmian regularnie przekraczających planowany czas zakończenia.',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: Colors.grey.shade700,
              ),
            )
          else
            ...driftingShifts.map(
              (ds) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(
                  '• ${ds['message']}',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: Colors.deepOrange.shade900,
                  ),
                ),
              ),
            ),
          const SizedBox(height: 12),

          // 3. Employee Monthly Target Risks
          Row(
            children: [
              Icon(
                Icons.manage_accounts_outlined,
                size: 18,
                color: Colors.purple.shade700,
              ),
              const SizedBox(width: 6),
              Text(
                '3. Ryzyko niewyrobienia lub przekroczenia celów miesięcznych',
                style: GoogleFonts.inter(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          if (targetRisks.isEmpty)
            Text(
              'Wszyscy pracownicy są na dobrej drodze do wyrobienia celów miesięcznych.',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: Colors.green.shade700,
              ),
            )
          else
            ...targetRisks.map(
              (tr) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(
                  '• ${tr['message']}',
                  style: GoogleFonts.inter(fontSize: 12),
                ),
              ),
            ),
          const SizedBox(height: 12),

          // 4. Shift Stability / Giveaways
          Row(
            children: [
              Icon(Icons.swap_horiz, size: 18, color: Colors.teal.shade700),
              const SizedBox(width: 6),
              Text(
                '4. Analiza stabilności zmian (Giełda wymian / Rotacja)',
                style: GoogleFonts.inter(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          if (hotspots.isEmpty)
            Text(
              'Brak podwyższonej rotacji na zmianach w badanym okresie.',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: Colors.grey.shade700,
              ),
            )
          else
            ...hotspots.take(5).map(
              (hs) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(
                  '• ${hs['message']}',
                  style: GoogleFonts.inter(fontSize: 12),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
