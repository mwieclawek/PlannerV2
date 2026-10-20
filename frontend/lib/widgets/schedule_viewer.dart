import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../models/models.dart';

class ScheduleViewer extends StatefulWidget {
  final List<ScheduleEntry> schedules;
  final List<ShiftDefinition> shifts;
  final List<JobRole> roles;
  final DateTime weekStart;
  final List<StaffingWarning> warnings;
  final Map<String, String> shiftWarnings;
  final void Function(DateTime date, int shiftId)? onEmptyCellTap;
  final void Function(ScheduleEntry entry)? onAssignmentTap;
  final bool initialEmployeeView;

  const ScheduleViewer({
    super.key,
    required this.schedules,
    required this.shifts,
    required this.roles,
    required this.weekStart,
    this.warnings = const [],
    this.shiftWarnings = const {},
    this.onEmptyCellTap,
    this.onAssignmentTap,
    this.initialEmployeeView = false,
  });

  @override
  State<ScheduleViewer> createState() => _ScheduleViewerState();
}

class _ScheduleViewerState extends State<ScheduleViewer> {
  late bool _byEmployeeView;
  String? _selectedEmployeeId; // null = all employees

  @override
  void initState() {
    super.initState();
    _byEmployeeView = widget.initialEmployeeView;
  }

  Color _getRoleColor(int roleId) {
    final role = widget.roles.where((r) => r.id == roleId).firstOrNull;
    if (role == null) return Colors.grey;
    final hexCode = role.colorHex.replaceAll('#', '');
    return Color(int.parse('FF$hexCode', radix: 16));
  }

  DateTime get weekEnd => widget.weekStart.add(const Duration(days: 6));

  List<DateTime> _getWeekDays() {
    return List.generate(7, (i) => widget.weekStart.add(Duration(days: i)));
  }

  List<ScheduleEntry> _getSchedulesForDayAndShift(DateTime date, int shiftId) {
    return widget.schedules.where((s) {
      return s.date.year == date.year &&
          s.date.month == date.month &&
          s.date.day == date.day &&
          s.shiftDefId == shiftId;
    }).toList();
  }

  List<StaffingWarning> _getWarningsForDayAndShift(DateTime date, int shiftId) {
    return widget.warnings.where((w) {
      return w.date.year == date.year &&
          w.date.month == date.month &&
          w.date.day == date.day &&
          w.shiftDefId == shiftId;
    }).toList();
  }

  List<ScheduleEntry> _getSchedulesForEmployeeAndDay(
    String userId,
    DateTime date,
  ) {
    final list =
        widget.schedules.where((s) {
          return s.userId == userId &&
              s.date.year == date.year &&
              s.date.month == date.month &&
              s.date.day == date.day;
        }).toList();
    list.sort((a, b) => a.startTime.compareTo(b.startTime));
    return list;
  }

  List<({String userId, String userName})> _getUniqueEmployees() {
    final map = <String, String>{};
    for (final s in widget.schedules) {
      map[s.userId] = s.userName;
    }
    final list =
        map.entries
            .map((e) => (userId: e.key, userName: e.value))
            .toList()
          ..sort((a, b) => a.userName.compareTo(b.userName));
    return list;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.schedules.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Center(
            child: Column(
              children: [
                Icon(
                  Icons.calendar_today,
                  size: 48,
                  color: Colors.grey.shade400,
                ),
                const SizedBox(height: 16),
                Text(
                  'Brak wygenerowanego grafiku',
                  style: GoogleFonts.inter(
                    fontSize: 16,
                    color: Colors.grey.shade600,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final weekDays = _getWeekDays();
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Grafik',
                      style: GoogleFonts.outfit(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${DateFormat('d MMM', 'pl_PL').format(widget.weekStart)} - ${DateFormat('d MMM yyyy', 'pl_PL').format(weekEnd)}',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
                SegmentedButton<bool>(
                  segments: const [
                    ButtonSegment<bool>(
                      value: false,
                      icon: Icon(Icons.access_time, size: 16),
                      label: Text('Wg zmian'),
                    ),
                    ButtonSegment<bool>(
                      value: true,
                      icon: Icon(Icons.people_alt_outlined, size: 16),
                      label: Text('Wg pracowników'),
                    ),
                  ],
                  selected: {_byEmployeeView},
                  onSelectionChanged: (selection) {
                    setState(() {
                      _byEmployeeView = selection.first;
                    });
                  },
                  style: SegmentedButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                    selectedBackgroundColor: colorScheme.primaryContainer,
                    selectedForegroundColor: colorScheme.onPrimaryContainer,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (_byEmployeeView)
              _buildEmployeeColumnsView(context, weekDays)
            else
              _buildShiftRowsView(context, weekDays),
          ],
        ),
      ),
    );
  }

  Widget _buildEmployeeColumnsView(
    BuildContext context,
    List<DateTime> weekDays,
  ) {
    final employees = _getUniqueEmployees();
    final colorScheme = Theme.of(context).colorScheme;
    if (_selectedEmployeeId != null &&
        !employees.any((e) => e.userId == _selectedEmployeeId)) {
      _selectedEmployeeId = null;
    }

    final visibleEmployees =
        _selectedEmployeeId == null
            ? employees
            : employees
                .where((e) => e.userId == _selectedEmployeeId)
                .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Employee tabs / chips
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  label: Text('Wszyscy (${employees.length})'),
                  selected: _selectedEmployeeId == null,
                  onSelected: (_) {
                    setState(() => _selectedEmployeeId = null);
                  },
                ),
              ),
              ...employees.map(
                (emp) => Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    avatar: CircleAvatar(
                      backgroundColor: colorScheme.primaryContainer,
                      child: Text(
                        emp.userName.isNotEmpty
                            ? emp.userName[0].toUpperCase()
                            : '?',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: colorScheme.onPrimaryContainer,
                        ),
                      ),
                    ),
                    label: Text(emp.userName),
                    selected: _selectedEmployeeId == emp.userId,
                    onSelected: (selected) {
                      setState(() {
                        _selectedEmployeeId = selected ? emp.userId : null;
                      });
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row: Pracownik + 7 days of the week as columns
              Row(
                children: [
                  SizedBox(
                    width: 150,
                    child: Text(
                      'Pracownik',
                      style: GoogleFonts.inter(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  ...weekDays.map(
                    (day) => SizedBox(
                      width: 150,
                      child: Center(
                        child: Column(
                          children: [
                            Text(
                              DateFormat('EEEE', 'pl_PL').format(day),
                              style: GoogleFonts.inter(
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                              ),
                            ),
                            Text(
                              DateFormat('d MMM', 'pl_PL').format(day),
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                color: Colors.grey.shade600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const Divider(height: 24),
              // Rows for each employee
              ...visibleEmployees.map((emp) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 150,
                        child: Padding(
                          padding: const EdgeInsets.only(top: 6, right: 8),
                          child: Row(
                            children: [
                              CircleAvatar(
                                radius: 14,
                                backgroundColor: colorScheme.primaryContainer,
                                child: Text(
                                  emp.userName.isNotEmpty
                                      ? emp.userName[0].toUpperCase()
                                      : '?',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: colorScheme.onPrimaryContainer,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  emp.userName,
                                  style: GoogleFonts.inter(
                                    fontWeight: FontWeight.w600,
                                    fontSize: 13,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      ...weekDays.map((day) {
                        final empShifts = _getSchedulesForEmployeeAndDay(
                          emp.userId,
                          day,
                        );
                        return SizedBox(
                          width: 150,
                          child: Container(
                            margin: const EdgeInsets.symmetric(horizontal: 4),
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color:
                                  empShifts.isEmpty
                                      ? colorScheme.surfaceContainerLow
                                      : colorScheme.primaryContainer.withValues(
                                        alpha: 0.25,
                                      ),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color:
                                    empShifts.isEmpty
                                        ? colorScheme.outlineVariant
                                        : colorScheme.primary.withValues(
                                          alpha: 0.45,
                                        ),
                              ),
                            ),
                            child:
                                empShifts.isEmpty
                                    ? Center(
                                      child: Text(
                                        'Wolne',
                                        style: GoogleFonts.inter(
                                          color: Colors.grey.shade400,
                                          fontSize: 11,
                                        ),
                                      ),
                                    )
                                    : Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children:
                                          empShifts.map((s) {
                                            final roleColor = _getRoleColor(
                                              s.roleId,
                                            );
                                            final startShort =
                                                s.startTime.length >= 5
                                                    ? s.startTime.substring(
                                                      0,
                                                      5,
                                                    )
                                                    : s.startTime;
                                            final endShort =
                                                s.endTime.length >= 5
                                                    ? s.endTime.substring(0, 5)
                                                    : s.endTime;
                                            return GestureDetector(
                                              onTap:
                                                  widget.onAssignmentTap != null
                                                      ? () => widget
                                                          .onAssignmentTap!(s)
                                                      : null,
                                              child: Container(
                                                width: double.infinity,
                                                margin: const EdgeInsets.only(
                                                  bottom: 4,
                                                ),
                                                padding:
                                                    const EdgeInsets.symmetric(
                                                      horizontal: 6,
                                                      vertical: 4,
                                                    ),
                                                decoration: BoxDecoration(
                                                  color: Colors.white,
                                                  borderRadius:
                                                      BorderRadius.circular(6),
                                                  border: Border.all(
                                                    color: roleColor.withValues(
                                                      alpha: 0.5,
                                                    ),
                                                  ),
                                                ),
                                                child: Column(
                                                  crossAxisAlignment:
                                                      CrossAxisAlignment.start,
                                                  children: [
                                                    Text(
                                                      s.shiftName,
                                                      style: GoogleFonts.inter(
                                                        fontSize: 12,
                                                        fontWeight:
                                                            FontWeight.bold,
                                                      ),
                                                      overflow:
                                                          TextOverflow.ellipsis,
                                                    ),
                                                    Text(
                                                      '$startShort - $endShort',
                                                      style: GoogleFonts.inter(
                                                        fontSize: 11,
                                                        color:
                                                            Colors
                                                                .grey
                                                                .shade700,
                                                      ),
                                                    ),
                                                    const SizedBox(height: 3),
                                                    Wrap(
                                                      spacing: 4,
                                                      runSpacing: 2,
                                                      children: [
                                                        Container(
                                                          padding:
                                                              const EdgeInsets.symmetric(
                                                                horizontal: 6,
                                                                vertical: 1,
                                                              ),
                                                          decoration:
                                                              BoxDecoration(
                                                                color:
                                                                    roleColor,
                                                                borderRadius:
                                                                    BorderRadius.circular(
                                                                      4,
                                                                    ),
                                                              ),
                                                          child: Text(
                                                            s.roleName,
                                                            style:
                                                                GoogleFonts.inter(
                                                                  fontSize: 9,
                                                                  color:
                                                                      Colors
                                                                          .white,
                                                                  fontWeight:
                                                                      FontWeight
                                                                          .w600,
                                                                ),
                                                          ),
                                                        ),
                                                        if (s.isOnGiveaway)
                                                          Container(
                                                            padding:
                                                                const EdgeInsets.symmetric(
                                                                  horizontal: 4,
                                                                  vertical: 1,
                                                                ),
                                                            decoration: BoxDecoration(
                                                              color:
                                                                  Colors
                                                                      .purple
                                                                      .shade100,
                                                              borderRadius:
                                                                  BorderRadius.circular(
                                                                    4,
                                                                  ),
                                                            ),
                                                            child: Text(
                                                              'Giełda',
                                                              style: TextStyle(
                                                                fontSize: 8,
                                                                color:
                                                                    Colors
                                                                        .purple
                                                                        .shade800,
                                                                fontWeight:
                                                                    FontWeight
                                                                        .bold,
                                                              ),
                                                            ),
                                                          ),
                                                        if (!s.isPublished)
                                                          Container(
                                                            padding:
                                                                const EdgeInsets.symmetric(
                                                                  horizontal: 4,
                                                                  vertical: 1,
                                                                ),
                                                            decoration: BoxDecoration(
                                                              color:
                                                                  Colors
                                                                      .amber
                                                                      .shade100,
                                                              borderRadius:
                                                                  BorderRadius.circular(
                                                                    4,
                                                                  ),
                                                            ),
                                                            child: Text(
                                                              'Szkic',
                                                              style: TextStyle(
                                                                fontSize: 8,
                                                                color:
                                                                    Colors
                                                                        .amber
                                                                        .shade900,
                                                                fontWeight:
                                                                    FontWeight
                                                                        .bold,
                                                              ),
                                                            ),
                                                          ),
                                                      ],
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            );
                                          }).toList(),
                                    ),
                          ),
                        );
                      }),
                    ],
                  ),
                );
              }),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildShiftRowsView(BuildContext context, List<DateTime> weekDays) {
    final effectiveShifts =
        widget.shifts.isNotEmpty
            ? widget.shifts
            : {
              for (final s in widget.schedules)
                s.shiftDefId: ShiftDefinition(
                  id: s.shiftDefId,
                  name: s.shiftName,
                  startTime: s.startTime,
                  endTime: s.endTime,
                ),
            }.values.toList();

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row with days
          Row(
            children: [
              SizedBox(
                width: 120,
                child: Text(
                  'Zmiana',
                  style: GoogleFonts.inter(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
              ),
              ...weekDays.map(
                (day) => SizedBox(
                  width: 150,
                  child: Center(
                    child: Column(
                      children: [
                        Text(
                          DateFormat('EEEE', 'pl_PL').format(day),
                          style: GoogleFonts.inter(
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                        Text(
                          DateFormat('d MMM', 'pl_PL').format(day),
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            color: Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),

          const Divider(height: 24),

          // Rows for each shift
          ...(effectiveShifts.map(
            (shift) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 120,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          shift.name,
                          style: GoogleFonts.inter(
                            fontWeight: FontWeight.w600,
                            fontSize: 14,
                          ),
                        ),
                        Text(
                          '${shift.startTime} - ${shift.endTime}',
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            color: Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Cells for each day
                  ...weekDays.map((day) {
                    final daySchedules = _getSchedulesForDayAndShift(
                      day,
                      shift.id,
                    );
                    final dayWarnings = _getWarningsForDayAndShift(
                      day,
                      shift.id,
                    );
                    final hasWarnings = dayWarnings.isNotEmpty;

                    return GestureDetector(
                      onTap:
                          daySchedules.isEmpty
                              ? (widget.onEmptyCellTap != null
                                  ? () => widget.onEmptyCellTap!(day, shift.id)
                                  : null)
                              : null,
                      child: SizedBox(
                        width: 150,
                        child: Container(
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color:
                                hasWarnings
                                    ? Theme.of(context)
                                        .colorScheme
                                        .errorContainer
                                        .withValues(alpha: 0.5)
                                    : (daySchedules.isEmpty
                                        ? Theme.of(
                                          context,
                                        ).colorScheme.surfaceContainerLow
                                        : Theme.of(context)
                                            .colorScheme
                                            .primaryContainer
                                            .withValues(alpha: 0.3)),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color:
                                  hasWarnings
                                      ? Theme.of(context).colorScheme.error
                                      : (daySchedules.isEmpty
                                          ? Theme.of(
                                            context,
                                          ).colorScheme.outlineVariant
                                          : Theme.of(context)
                                              .colorScheme
                                              .primary
                                              .withValues(alpha: 0.5)),
                              width: hasWarnings ? 1.5 : 1,
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Show warnings at the top of the cell
                              if (hasWarnings)
                                ...dayWarnings.map(
                                  (warning) => Container(
                                    margin: const EdgeInsets.only(bottom: 4),
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 6,
                                      vertical: 3,
                                    ),
                                    decoration: BoxDecoration(
                                      color: Colors.orange.shade100,
                                      borderRadius: BorderRadius.circular(4),
                                      border: Border.all(
                                        color: Colors.orange.shade300,
                                      ),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(
                                          Icons.warning_amber_rounded,
                                          size: 12,
                                          color: Colors.orange.shade800,
                                        ),
                                        const SizedBox(width: 4),
                                        Flexible(
                                          child: Text(
                                            'Brakuje: ${warning.roleName} (${warning.missing})',
                                            style: GoogleFonts.inter(
                                              fontSize: 9,
                                              fontWeight: FontWeight.w600,
                                              color: Colors.orange.shade900,
                                            ),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              // Show assignments or empty state
                              if (daySchedules.isEmpty && !hasWarnings)
                                Center(
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      if (widget.onEmptyCellTap != null)
                                        Icon(
                                          Icons.add,
                                          size: 16,
                                          color: Colors.grey.shade400,
                                        ),
                                      Text(
                                        widget.onEmptyCellTap != null
                                            ? 'Dodaj'
                                            : '-',
                                        style: GoogleFonts.inter(
                                          color: Colors.grey.shade400,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ],
                                  ),
                                )
                              else if (daySchedules.isEmpty && hasWarnings)
                                Center(
                                  child: GestureDetector(
                                    onTap:
                                        widget.onEmptyCellTap != null
                                            ? () => widget.onEmptyCellTap!(
                                              day,
                                              shift.id,
                                            )
                                            : null,
                                    child: Container(
                                      margin: const EdgeInsets.only(top: 4),
                                      padding: const EdgeInsets.symmetric(
                                        vertical: 4,
                                        horizontal: 8,
                                      ),
                                      decoration: BoxDecoration(
                                        color: Colors.orange.shade100,
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(
                                            Icons.add,
                                            size: 12,
                                            color: Colors.orange.shade700,
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            'Dodaj',
                                            style: GoogleFonts.inter(
                                              fontSize: 10,
                                              color: Colors.orange.shade700,
                                              fontWeight: FontWeight.w500,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                )
                              else ...[
                                ...daySchedules.map((schedule) {
                                  return GestureDetector(
                                    onTap:
                                        widget.onAssignmentTap != null
                                            ? () => widget.onAssignmentTap!(
                                              schedule,
                                            )
                                            : null,
                                    child: Padding(
                                      padding: const EdgeInsets.only(bottom: 4),
                                      child: Row(
                                        children: [
                                          Icon(
                                            Icons.person,
                                            size: 14,
                                            color:
                                                Theme.of(
                                                  context,
                                                ).colorScheme.primary,
                                          ),
                                          const SizedBox(width: 4),
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                  schedule.userName,
                                                  style: GoogleFonts.inter(
                                                    fontSize: 12,
                                                    fontWeight: FontWeight.w600,
                                                  ),
                                                  overflow:
                                                      TextOverflow.ellipsis,
                                                ),
                                                const SizedBox(height: 2),
                                                Row(
                                                  children: [
                                                    Container(
                                                      padding:
                                                          const EdgeInsets.symmetric(
                                                            horizontal: 6,
                                                            vertical: 2,
                                                          ),
                                                      decoration: BoxDecoration(
                                                        color: _getRoleColor(
                                                          schedule.roleId,
                                                        ),
                                                        borderRadius:
                                                            BorderRadius.circular(
                                                              4,
                                                            ),
                                                      ),
                                                      child: Text(
                                                        schedule.roleName,
                                                        style:
                                                            GoogleFonts.inter(
                                                              fontSize: 9,
                                                              color:
                                                                  Colors.white,
                                                              fontWeight:
                                                                  FontWeight
                                                                      .w500,
                                                            ),
                                                        overflow:
                                                            TextOverflow
                                                                .ellipsis,
                                                      ),
                                                    ),
                                                    if (schedule
                                                        .isOnGiveaway) ...[
                                                      const SizedBox(width: 4),
                                                      Container(
                                                        padding:
                                                            const EdgeInsets.symmetric(
                                                              horizontal: 4,
                                                              vertical: 2,
                                                            ),
                                                        decoration: BoxDecoration(
                                                          color:
                                                              Colors
                                                                  .purple
                                                                  .shade100,
                                                          borderRadius:
                                                              BorderRadius.circular(
                                                                4,
                                                              ),
                                                          border: Border.all(
                                                            color:
                                                                Colors
                                                                    .purple
                                                                    .shade300,
                                                          ),
                                                        ),
                                                        child: Text(
                                                          'Giełda',
                                                          style:
                                                              GoogleFonts.inter(
                                                                fontSize: 8,
                                                                color:
                                                                    Colors
                                                                        .purple
                                                                        .shade800,
                                                                fontWeight:
                                                                    FontWeight
                                                                        .bold,
                                                              ),
                                                        ),
                                                      ),
                                                    ],
                                                    if (!schedule
                                                        .isPublished) ...[
                                                      const SizedBox(width: 4),
                                                      Container(
                                                        padding:
                                                            const EdgeInsets.symmetric(
                                                              horizontal: 4,
                                                              vertical: 2,
                                                            ),
                                                        decoration: BoxDecoration(
                                                          color:
                                                              Colors
                                                                  .amber
                                                                  .shade100,
                                                          borderRadius:
                                                              BorderRadius.circular(
                                                                4,
                                                              ),
                                                          border: Border.all(
                                                            color:
                                                                Colors
                                                                    .amber
                                                                    .shade400,
                                                          ),
                                                        ),
                                                        child: Text(
                                                          'Szkic',
                                                          style:
                                                              GoogleFonts.inter(
                                                                fontSize: 8,
                                                                color:
                                                                    Colors
                                                                        .amber
                                                                        .shade900,
                                                                fontWeight:
                                                                    FontWeight
                                                                        .bold,
                                                              ),
                                                        ),
                                                      ),
                                                    ],
                                                    if (widget.shiftWarnings
                                                        .containsKey(
                                                          schedule.id,
                                                        )) ...[
                                                      const SizedBox(width: 4),
                                                      Tooltip(
                                                        message:
                                                            widget
                                                                .shiftWarnings[schedule
                                                                .id]!,
                                                        child: Icon(
                                                          Icons
                                                              .warning_amber_rounded,
                                                          size: 14,
                                                          color:
                                                              Colors
                                                                  .amber
                                                                  .shade900,
                                                        ),
                                                      ),
                                                    ],
                                                  ],
                                                ),
                                              ],
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  );
                                }),
                                // Add more staff button
                                if (widget.onEmptyCellTap != null)
                                  GestureDetector(
                                    onTap:
                                        () => widget.onEmptyCellTap!(
                                          day,
                                          shift.id,
                                        ),
                                    child: Container(
                                      margin: const EdgeInsets.only(top: 4),
                                      padding: const EdgeInsets.symmetric(
                                        vertical: 4,
                                        horizontal: 8,
                                      ),
                                      decoration: BoxDecoration(
                                        color:
                                            hasWarnings
                                                ? Theme.of(
                                                  context,
                                                ).colorScheme.errorContainer
                                                : Theme.of(
                                                  context,
                                                ).colorScheme.primaryContainer,
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(
                                            Icons.add,
                                            size: 12,
                                            color:
                                                hasWarnings
                                                    ? Theme.of(
                                                      context,
                                                    ).colorScheme.error
                                                    : Theme.of(
                                                      context,
                                                    ).colorScheme.primary,
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            'Dodaj',
                                            style: GoogleFonts.inter(
                                              fontSize: 10,
                                              color:
                                                  hasWarnings
                                                      ? Theme.of(
                                                        context,
                                                      ).colorScheme.error
                                                      : Theme.of(
                                                        context,
                                                      ).colorScheme.primary,
                                              fontWeight: FontWeight.w500,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
          )),
        ],
      ),
    );
  }
}
