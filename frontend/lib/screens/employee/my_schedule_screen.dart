import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class MyScheduleScreen extends ConsumerStatefulWidget {
  const MyScheduleScreen({super.key});

  @override
  ConsumerState<MyScheduleScreen> createState() => _MyScheduleScreenState();
}

class _MyScheduleScreenState extends ConsumerState<MyScheduleScreen> {
  DateTime _selectedWeekStart = _getMonday(DateTime.now());
  bool _isLoading = false;
  List<EmployeeScheduleEntry> _scheduleEntries = [];
  bool _showCoworkers = false;

  static DateTime _getMonday(DateTime date) {
    return date.subtract(Duration(days: date.weekday - 1));
  }

  DateTime get _selectedWeekEnd => _selectedWeekStart.add(const Duration(days: 6));

  @override
  void initState() {
    super.initState();
    _loadSchedule();
  }

  Future<void> _loadSchedule() async {
    setState(() => _isLoading = true);
    
    try {
      final schedules = await ref.read(apiServiceProvider).getEmployeeSchedule(
        _selectedWeekStart,
        _selectedWeekEnd,
      );
      
      setState(() {
        _scheduleEntries = schedules;
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

  void _previousWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.subtract(const Duration(days: 7));
    });
    _loadSchedule();
  }

  void _nextWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.add(const Duration(days: 7));
    });
    _loadSchedule();
  }

  @override
  Widget build(BuildContext context) {
    // NOTE: No Scaffold here - this is embedded inside EmployeeDashboard which has AppBar
    return _isLoading
        ? const Center(child: CircularProgressIndicator())
        : Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 900),
              child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  // Week Selector
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
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
                  ),
                  
                  const SizedBox(height: 16),
                  
                  // Schedule List
                  if (_scheduleEntries.isEmpty) ...[
                    Center(
                      child: Padding(
                        padding: const EdgeInsets.all(48),
                        child: Column(
                          children: [
                            Icon(
                              Icons.event_busy,
                              size: 64,
                              color: Colors.grey.shade400,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Brak przypisanych zmian',
                              style: GoogleFonts.outfit(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                                color: Colors.grey.shade600,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Grafik nie został jeszcze opublikowany',
                              style: GoogleFonts.inter(
                                fontSize: 14,
                                color: Colors.grey.shade500,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ] else ...[
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          _showCoworkers ? 'Cała załoga' : 'Twoje zmiany',
                          style: GoogleFonts.outfit(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        TextButton.icon(
                          onPressed: _loadSchedule,
                          icon: const Icon(Icons.refresh, size: 18),
                          label: const Text('Odśwież'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),

                    // View mode toggle
                    Center(
                      child: SegmentedButton<bool>(
                        segments: const [
                          ButtonSegment(
                            value: false,
                            label: Text('Moje zmiany'),
                            icon: Icon(Icons.person),
                          ),
                          ButtonSegment(
                            value: true,
                            label: Text('Cała załoga'),
                            icon: Icon(Icons.people),
                          ),
                        ],
                        selected: {_showCoworkers},
                        onSelectionChanged: (v) => setState(() => _showCoworkers = v.first),
                        style: SegmentedButton.styleFrom(
                          selectedBackgroundColor: Theme.of(context).colorScheme.primaryContainer,
                          selectedForegroundColor: Theme.of(context).colorScheme.onPrimaryContainer,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    
                    if (_showCoworkers) ...[
                      // Manager-style week view
                      _buildTeamWeekView(),
                    ] else ...[
                    // Group by date (original "Moje zmiany" view)
                    ...(_groupByDate(_scheduleEntries).entries.map((entry) {
                      final date = entry.key;
                      final shifts = entry.value;
                      final isToday = _isToday(date);
                      final isPast = _isPast(date);
                      
                      return Opacity(
                        opacity: isPast ? 0.6 : 1.0,
                        child: Card(
                          margin: const EdgeInsets.only(bottom: 12),
                          elevation: isToday ? 4 : 1,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                            side: isToday 
                                ? BorderSide(color: Theme.of(context).colorScheme.primary, width: 2)
                                : BorderSide.none,
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 12,
                                        vertical: 6,
                                      ),
                                      decoration: BoxDecoration(
                                        color: isToday ? Theme.of(context).colorScheme.secondary : Theme.of(context).colorScheme.primary,
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Text(
                                        isToday ? 'DZISIAJ' : DateFormat('EEE', 'pl_PL').format(date),
                                        style: GoogleFonts.inter(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 12,
                                        ),
                                      ),
                                    ),
                                    if (isToday) const SizedBox(width: 8),
                                    if (isToday)
                                      Icon(Icons.star, size: 16, color: Theme.of(context).colorScheme.secondary),
                                    const SizedBox(width: 12),
                                    Text(
                                      DateFormat('d MMMM yyyy', 'pl_PL').format(date),
                                      style: GoogleFonts.inter(
                                        fontSize: 16,
                                        fontWeight: FontWeight.w600,
                                        color: isPast ? Colors.grey.shade700 : null,
                                      ),
                                    ),
                                  ],
                                ),
                                const Divider(height: 24),
                                
                                // Shifts for this day
                                ...shifts.map((shift) => Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Container(
                                            padding: const EdgeInsets.all(12),
                                            decoration: BoxDecoration(
                                              color: isToday ? Theme.of(context).colorScheme.secondaryContainer : Theme.of(context).colorScheme.primaryContainer,
                                              borderRadius: BorderRadius.circular(8),
                                            ),
                                            child: Icon(
                                              Icons.access_time,
                                              color: isToday ? Theme.of(context).colorScheme.onSecondaryContainer : Theme.of(context).colorScheme.onPrimaryContainer,
                                              size: 24,
                                            ),
                                          ),
                                          const SizedBox(width: 16),
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Row(
                                                  children: [
                                                    Text(
                                                      shift.shiftName,
                                                      style: GoogleFonts.inter(
                                                        fontSize: 16,
                                                        fontWeight: FontWeight.w600,
                                                      ),
                                                    ),
                                                    if (shift.isOnGiveaway) ...[
                                                      const SizedBox(width: 8),
                                                      Container(
                                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                        decoration: BoxDecoration(
                                                          color: Colors.purple.shade100,
                                                          borderRadius: BorderRadius.circular(4),
                                                          border: Border.all(color: Colors.purple.shade300),
                                                        ),
                                                        child: Text(
                                                          'GIEŁDA',
                                                          style: GoogleFonts.inter(
                                                            fontSize: 10,
                                                            color: Colors.purple.shade800,
                                                            fontWeight: FontWeight.bold,
                                                          ),
                                                        ),
                                                      ),
                                                    ],
                                                  ],
                                                ),
                                                const SizedBox(height: 4),
                                                Row(
                                                  children: [
                                                    Icon(
                                                      Icons.schedule,
                                                      size: 14,
                                                      color: Colors.grey.shade600,
                                                    ),
                                                    const SizedBox(width: 4),
                                                    Text(
                                                      '${shift.startTime} - ${shift.endTime}',
                                                      style: GoogleFonts.inter(
                                                        fontSize: 14,
                                                        color: Colors.grey.shade600,
                                                      ),
                                                    ),
                                                    const SizedBox(width: 16),
                                                    Icon(
                                                      Icons.badge,
                                                      size: 14,
                                                      color: Colors.grey.shade600,
                                                    ),
                                                    const SizedBox(width: 4),
                                                    Text(
                                                      shift.roleName,
                                                      style: GoogleFonts.inter(
                                                        fontSize: 14,
                                                        color: Colors.grey.shade600,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ],
                                            ),
                                            ),
                                          ],
                                        ),
                                      if (!isPast) ...[
                                          const SizedBox(height: 8),
                                          SizedBox(
                                            width: double.infinity,
                                            child: shift.isOnGiveaway 
                                              ? OutlinedButton.icon(
                                                  onPressed: null, // Disabled
                                                  icon: const Icon(Icons.check_circle_outline, color: Colors.purple),
                                                  label: const Text('Wystawiono na giełdę', style: TextStyle(color: Colors.purple)),
                                                  style: OutlinedButton.styleFrom(
                                                    side: BorderSide(color: Colors.purple.shade200),
                                                  ),
                                                )
                                              : TextButton.icon(
                                                  onPressed: () => _showGiveawayConfirmation(shift),
                                                  icon: Icon(Icons.swap_horiz, color: Colors.grey.shade700),
                                                  label: Text(
                                                    'Oddaj zmianę',
                                                    style: GoogleFonts.inter(color: Colors.grey.shade700),
                                                  ),
                                                ),
                                          ),
                                        ],
                                      if (isToday) ...[
                                        const SizedBox(height: 12),
                                        SizedBox(
                                          width: double.infinity,
                                          child: OutlinedButton.icon(
                                            onPressed: () => _showRegisterPresenceDialog(shift),
                                            icon: const Icon(Icons.how_to_reg),
                                            label: const Text('Zarejestruj obecność'),
                                            style: OutlinedButton.styleFrom(
                                              foregroundColor: Theme.of(context).colorScheme.primary,
                                              side: BorderSide(color: Theme.of(context).colorScheme.primary),
                                              padding: const EdgeInsets.symmetric(vertical: 12),
                                            ),
                                          ),
                                        ),
                                      ],
                                   ],
                                  ),
                                )),
                              ],
                            ),
                          ),
                        ),
                      );
                    })),
                    ], // end else (Moje zmiany)
                  ],
                  
                  const SizedBox(height: 16),
                  
                  // Info Card
                  Card(
                    color: Theme.of(context).colorScheme.secondaryContainer.withOpacity(0.5),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          Icon(Icons.info_outline, color: Theme.of(context).colorScheme.onSecondaryContainer),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'Wyświetlane są tylko opublikowane grafiki. Jeśli nie widzisz zmian, skontaktuj się z managerem.',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: Theme.of(context).colorScheme.onSecondaryContainer,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );

  }


  Widget _buildTeamWeekView() {
    final colorScheme = Theme.of(context).colorScheme;
    final user = ref.read(authProvider).value;
    final currentUserName = user?.fullName ?? '';
    final days = List.generate(7, (i) => _selectedWeekStart.add(Duration(days: i)));
    final today = DateTime.now();

    // Build a flat list of all people per day+shift from the employee entries
    // Each EmployeeScheduleEntry is the current user's shift, with coworkers
    final grouped = _groupByDate(_scheduleEntries);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Week header
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: colorScheme.primaryContainer.withOpacity(0.3),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.date_range, size: 18, color: colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                '${DateFormat('d MMM', 'pl_PL').format(_selectedWeekStart)} – ${DateFormat('d MMM yyyy', 'pl_PL').format(days.last)}',
                style: GoogleFonts.inter(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: colorScheme.onSurface,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Day cards
        ...days.map((day) {
          final isToday = day.year == today.year && day.month == today.month && day.day == today.day;
          final dateKey = DateTime(day.year, day.month, day.day);
          final dayShifts = grouped[dateKey] ?? [];

          // Build list of all individual entries (user + coworkers)
          final List<_TeamEntry> allEntries = [];
          for (final shift in dayShifts) {
            // Current user entry
            allEntries.add(_TeamEntry(
              userName: currentUserName.isNotEmpty ? currentUserName : 'Ty',
              roleName: shift.roleName,
              shiftName: shift.shiftName,
              startTime: shift.startTime,
              endTime: shift.endTime,
              isCurrentUser: true,
            ));
            // Coworker entries
            for (final coworker in shift.coworkers) {
              allEntries.add(_TeamEntry(
                userName: coworker,
                roleName: shift.roleName,
                shiftName: shift.shiftName,
                startTime: shift.startTime,
                endTime: shift.endTime,
                isCurrentUser: false,
              ));
            }
          }
          allEntries.sort((a, b) => a.startTime.compareTo(b.startTime));

          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: isToday
                  ? Border.all(color: colorScheme.primary, width: 2)
                  : Border.all(color: colorScheme.outlineVariant.withOpacity(0.4)),
              color: isToday
                  ? colorScheme.primaryContainer.withOpacity(0.15)
                  : colorScheme.surface,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Day header
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  decoration: BoxDecoration(
                    color: isToday
                        ? colorScheme.primary.withOpacity(0.08)
                        : colorScheme.surfaceContainerLow,
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
                  ),
                  child: Row(
                    children: [
                      if (isToday) ...[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: colorScheme.primary,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            'DZIŚ',
                            style: GoogleFonts.inter(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: colorScheme.onPrimary,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                      ],
                      Text(
                        DateFormat('EEEE, d MMMM', 'pl_PL').format(day),
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: isToday ? FontWeight.bold : FontWeight.w600,
                          color: isToday ? colorScheme.primary : colorScheme.onSurface,
                        ),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: allEntries.isEmpty
                              ? Colors.grey.shade200
                              : colorScheme.primaryContainer,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '${allEntries.length} ${allEntries.length == 1 ? 'zmiana' : 'zmian'}',
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: allEntries.isEmpty
                                ? Colors.grey.shade600
                                : colorScheme.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // Entries
                if (allEntries.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      'Brak zaplanowanych zmian',
                      style: GoogleFonts.inter(fontSize: 13, color: Colors.grey.shade500),
                    ),
                  )
                else
                  ...allEntries.map((entry) {
                    final hue = (entry.roleName.hashCode % 360).abs().toDouble();
                    final eventColor = HSLColor.fromAHSL(1.0, hue, 0.55, 0.55).toColor();

                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      child: Row(
                        children: [
                          // Time
                          SizedBox(
                            width: 80,
                            child: Text(
                              '${entry.startTime.substring(0, 5)}–${entry.endTime.substring(0, 5)}',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                color: Colors.grey.shade600,
                              ),
                            ),
                          ),
                          // Color bar
                          Container(
                            width: 3,
                            height: 32,
                            decoration: BoxDecoration(
                              color: eventColor,
                              borderRadius: BorderRadius.circular(2),
                            ),
                          ),
                          const SizedBox(width: 10),
                          // Name + role
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  entry.userName,
                                  style: GoogleFonts.inter(
                                    fontSize: 13,
                                    fontWeight: entry.isCurrentUser ? FontWeight.w800 : FontWeight.w600,
                                    color: entry.isCurrentUser ? colorScheme.primary : null,
                                  ),
                                ),
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                      decoration: BoxDecoration(
                                        color: eventColor.withOpacity(0.12),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(
                                        entry.roleName,
                                        style: TextStyle(
                                          fontSize: 10,
                                          color: eventColor,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      entry.shiftName,
                                      style: GoogleFonts.inter(
                                        fontSize: 11,
                                        color: Colors.grey.shade500,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                const SizedBox(height: 4),
              ],
            ),
          );
        }),
      ],
    );
  }

  Map<DateTime, List<EmployeeScheduleEntry>> _groupByDate(List<EmployeeScheduleEntry> entries) {
    final Map<DateTime, List<EmployeeScheduleEntry>> grouped = {};
    
    for (var entry in entries) {
      final dateKey = DateTime(entry.date.year, entry.date.month, entry.date.day);
      if (!grouped.containsKey(dateKey)) {
        grouped[dateKey] = [];
      }
      grouped[dateKey]!.add(entry);
    }
    
    // Sort by date
    final sortedKeys = grouped.keys.toList()..sort();
    final sortedMap = <DateTime, List<EmployeeScheduleEntry>>{};
    for (var key in sortedKeys) {
      sortedMap[key] = grouped[key]!;
    }
    
    return sortedMap;
  }

  bool _isToday(DateTime date) {
    final now = DateTime.now();
    return date.year == now.year && date.month == now.month && date.day == now.day;
  }

  bool _isPast(DateTime date) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    return date.isBefore(today);
  }

  void _showRegisterPresenceDialog(EmployeeScheduleEntry shift) async {
    setState(() => _isLoading = true);
    try {
      final api = ref.read(apiServiceProvider);
      final defaults = await api.getAttendanceDefaults(shift.date);
      setState(() => _isLoading = false);
      
      if (!mounted) return;
      
      final checkInController = TextEditingController(text: defaults['check_in'] ?? shift.startTime);
      final checkOutController = TextEditingController(text: defaults['check_out'] ?? shift.endTime);

      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Zarejestruj obecność'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Zmiana: ${shift.shiftName}'),
              Text('Data: ${DateFormat('d MMMM yyyy', 'pl_PL').format(shift.date)}'),
              const SizedBox(height: 16),
              TextField(
                controller: checkInController,
                decoration: const InputDecoration(
                  labelText: 'Godzina rozpoczęcia',
                  prefixIcon: Icon(Icons.login),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: checkOutController,
                decoration: const InputDecoration(
                  labelText: 'Godzina zakończenia',
                  prefixIcon: Icon(Icons.logout),
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Anuluj'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(context);
                _submitAttendance(shift.date, checkInController.text, checkOutController.text);
              },
              child: const Text('Zapisz'),
            ),
          ],
        ),
      );
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd pobierania domyślnych wartości: $e')),
        );
      }
    }
  }

  Future<void> _submitAttendance(DateTime date, String checkIn, String checkOut) async {
    setState(() => _isLoading = true);
    try {
      await ref.read(apiServiceProvider).registerAttendance(date, checkIn, checkOut);
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✓ Obecność zarejestrowana'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd rejestracji: $e'), backgroundColor: Theme.of(context).colorScheme.error),
        );
      }
    }
  }


  void _showGiveawayConfirmation(EmployeeScheduleEntry shift) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Oddać zmianę?'),
        content: Text(
          'Czy na pewno chcesz oddać zmianę ${shift.shiftName} w dniu ${DateFormat('d MMMM', 'pl_PL').format(shift.date)}?\n\n'
          'Zmiana zostanie oznaczona jako dostępna dla innych pracowników. Musisz pracować, dopóki ktoś jej nie przejmie lub manager nie zatwierdzi zmiany.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(context);
              _submitGiveaway(shift.id);
            },
            child: const Text('Potwierdź oddanie'),
          ),
        ],
      ),
    );
  }

  Future<void> _submitGiveaway(String scheduleId) async {
    setState(() => _isLoading = true);
    try {
      await ref.read(apiServiceProvider).giveAwayShift(scheduleId);
      await _loadSchedule(); // Refresh to show "On Giveaway" status
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✓ Zmiana wystawiona na giełdę'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e'), backgroundColor: Theme.of(context).colorScheme.error),
        );
      }
    }
  }
}

class _TeamEntry {
  final String userName;
  final String roleName;
  final String shiftName;
  final String startTime;
  final String endTime;
  final bool isCurrentUser;

  _TeamEntry({
    required this.userName,
    required this.roleName,
    required this.shiftName,
    required this.startTime,
    required this.endTime,
    this.isCurrentUser = false,
  });
}
