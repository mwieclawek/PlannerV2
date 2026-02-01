import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../models/models.dart';

class ScheduleViewer extends StatelessWidget {
  final List<ScheduleEntry> schedules;
  final List<ShiftDefinition> shifts;
  final List<JobRole> roles;
  final DateTime weekStart;
  final void Function(DateTime date, int shiftId)? onEmptyCellTap;
  final void Function(ScheduleEntry entry)? onAssignmentTap;

  const ScheduleViewer({
    super.key,
    required this.schedules,
    required this.shifts,
    required this.roles,
    required this.weekStart,
    this.onEmptyCellTap,
    this.onAssignmentTap,
  });

  Color _getRoleColor(int roleId) {
    final role = roles.where((r) => r.id == roleId).firstOrNull;
    if (role == null) return Colors.grey;
    final hexCode = role.colorHex.replaceAll('#', '');
    return Color(int.parse('FF$hexCode', radix: 16));
  }

  DateTime get weekEnd => weekStart.add(const Duration(days: 6));

  List<DateTime> _getWeekDays() {
    return List.generate(7, (i) => weekStart.add(Duration(days: i)));
  }

  List<ScheduleEntry> _getSchedulesForDayAndShift(DateTime date, int shiftId) {
    return schedules.where((s) {
      return s.date.year == date.year &&
          s.date.month == date.month &&
          s.date.day == date.day &&
          s.shiftDefId == shiftId;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    if (schedules.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Center(
            child: Column(
              children: [
                Icon(Icons.calendar_today, size: 48, color: Colors.grey.shade400),
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

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Grafik',
              style: GoogleFonts.outfit(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '${DateFormat('d MMM', 'pl_PL').format(weekStart)} - ${DateFormat('d MMM yyyy', 'pl_PL').format(weekEnd)}',
              style: GoogleFonts.inter(
                fontSize: 14,
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 16),
            
            SingleChildScrollView(
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
                      ...weekDays.map((day) => SizedBox(
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
                      )),
                    ],
                  ),
                  
                  const Divider(height: 24),
                  
                  // Rows for each shift
                  ...(shifts.map((shift) => Padding(
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
                          final daySchedules = _getSchedulesForDayAndShift(day, shift.id);
                          
                          return GestureDetector(
                            onTap: daySchedules.isEmpty 
                                ? (onEmptyCellTap != null ? () => onEmptyCellTap!(day, shift.id) : null)
                                : null,
                            child: SizedBox(
                              width: 150,
                              child: Container(
                                margin: const EdgeInsets.symmetric(horizontal: 4),
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: daySchedules.isEmpty 
                                      ? Colors.grey.shade100 
                                      : Colors.indigo.shade50,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(
                                    color: daySchedules.isEmpty 
                                        ? Colors.grey.shade300 
                                        : Colors.indigo.shade200,
                                  ),
                                ),
                                child: daySchedules.isEmpty
                                    ? Center(
                                        child: Column(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            if (onEmptyCellTap != null)
                                              Icon(Icons.add, size: 16, color: Colors.grey.shade400),
                                            Text(
                                              onEmptyCellTap != null ? 'Dodaj' : '-',
                                              style: GoogleFonts.inter(
                                                color: Colors.grey.shade400,
                                                fontSize: 11,
                                              ),
                                            ),
                                          ],
                                        ),
                                      )
                                    : Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          ...daySchedules.map((schedule) {
                                            return GestureDetector(
                                              onTap: onAssignmentTap != null 
                                                  ? () => onAssignmentTap!(schedule) 
                                                  : null,
                                              child: Padding(
                                                padding: const EdgeInsets.only(bottom: 4),
                                                child: Row(
                                                  children: [
                                                    Icon(
                                                      Icons.person,
                                                      size: 14,
                                                      color: Colors.indigo.shade700,
                                                    ),
                                                    const SizedBox(width: 4),
                                                    Expanded(
                                                      child: Column(
                                                        crossAxisAlignment: CrossAxisAlignment.start,
                                                        children: [
                                                          Text(
                                                            schedule.userName,
                                                            style: GoogleFonts.inter(
                                                              fontSize: 12,
                                                              fontWeight: FontWeight.w600,
                                                            ),
                                                            overflow: TextOverflow.ellipsis,
                                                          ),
                                                          const SizedBox(height: 2),
                                                          Container(
                                                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                            decoration: BoxDecoration(
                                                              color: _getRoleColor(schedule.roleId),
                                                              borderRadius: BorderRadius.circular(4),
                                                            ),
                                                            child: Text(
                                                              schedule.roleName,
                                                              style: GoogleFonts.inter(
                                                                fontSize: 9,
                                                                color: Colors.white,
                                                                fontWeight: FontWeight.w500,
                                                              ),
                                                              overflow: TextOverflow.ellipsis,
                                                            ),
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
                                          if (onEmptyCellTap != null)
                                            GestureDetector(
                                              onTap: () => onEmptyCellTap!(day, shift.id),
                                              child: Container(
                                                margin: const EdgeInsets.only(top: 4),
                                                padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
                                                decoration: BoxDecoration(
                                                  color: Colors.indigo.shade100,
                                                  borderRadius: BorderRadius.circular(4),
                                                ),
                                                child: Row(
                                                  mainAxisSize: MainAxisSize.min,
                                                  children: [
                                                    Icon(Icons.add, size: 12, color: Colors.indigo.shade700),
                                                    const SizedBox(width: 4),
                                                    Text(
                                                      'Dodaj',
                                                      style: GoogleFonts.inter(
                                                        fontSize: 10,
                                                        color: Colors.indigo.shade700,
                                                        fontWeight: FontWeight.w500,
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
                        }),
                      ],
                    ),
                  ))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
