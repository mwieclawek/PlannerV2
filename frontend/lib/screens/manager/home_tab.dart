import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';

enum CalendarViewMode { day, week }

class HomeTab extends ConsumerStatefulWidget {
  const HomeTab({super.key});

  @override
  ConsumerState<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends ConsumerState<HomeTab> {
  late Future<DashboardHome> _dashboardFuture;
  CalendarViewMode _viewMode = CalendarViewMode.day;
  List<ScheduleEntry> _weekEntries = [];
  bool _weekLoading = false;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    setState(() {
      _dashboardFuture = ref.read(apiServiceProvider).getDashboardHome(
        date: DateTime.now(),
      );
    });
    if (_viewMode == CalendarViewMode.week) {
      _loadWeekSchedule();
    }
  }

  Future<void> _loadWeekSchedule() async {
    setState(() => _weekLoading = true);
    try {
      final now = DateTime.now();
      final weekStart = now.subtract(Duration(days: now.weekday - 1));
      final weekEnd = weekStart.add(const Duration(days: 6));
      final entries = await ref.read(apiServiceProvider).getManagerSchedule(weekStart, weekEnd);
      setState(() {
        _weekEntries = entries;
        _weekLoading = false;
      });
    } catch (e) {
      setState(() => _weekLoading = false);
    }
  }

  DateTime get _weekStart {
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day).subtract(Duration(days: now.weekday - 1));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return RefreshIndicator(
      onRefresh: () async => _refresh(),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Greeting
            Text(
              'Dzień dobry!',
              style: GoogleFonts.outfit(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: colorScheme.onSurface,
              ),
            ),
            Text(
              DateFormat('EEEE, d MMMM yyyy', 'pl_PL').format(DateTime.now()),
              style: GoogleFonts.inter(
                fontSize: 16,
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 20),

            // View mode toggle
            Center(
              child: SegmentedButton<CalendarViewMode>(
                segments: const [
                  ButtonSegment(
                    value: CalendarViewMode.day,
                    label: Text('Dziś'),
                    icon: Icon(Icons.today),
                  ),
                  ButtonSegment(
                    value: CalendarViewMode.week,
                    label: Text('Tydzień'),
                    icon: Icon(Icons.view_week),
                  ),
                ],
                selected: {_viewMode},
                onSelectionChanged: (newSelection) {
                  setState(() => _viewMode = newSelection.first);
                  if (_viewMode == CalendarViewMode.week && _weekEntries.isEmpty) {
                    _loadWeekSchedule();
                  }
                },
                style: ButtonStyle(
                  shape: WidgetStatePropertyAll(
                    RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Content based on view mode
            if (_viewMode == CalendarViewMode.day) ...[
              FutureBuilder<DashboardHome>(
                future: _dashboardFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  if (snapshot.hasError) {
                    return Center(child: Text('Błąd: ${snapshot.error}'));
                  }
                  if (!snapshot.hasData) {
                    return const Center(child: Text('Brak danych'));
                  }

                  final data = snapshot.data!;

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSectionTitle('Dzisiaj w pracy', Icons.work_rounded),
                      const SizedBox(height: 12),
                      _buildDayTimeline(data.workingToday),
                      const SizedBox(height: 32),
                      _buildSectionTitle('Zaległe potwierdzenia', Icons.warning_amber_rounded),
                      const SizedBox(height: 12),
                      _buildMissingConfirmationsList(data.missingConfirmations),
                    ],
                  );
                },
              ),
            ] else ...[
              if (_weekLoading)
                const Center(child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ))
              else
                _buildWeekView(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title, IconData icon) {
    final colorScheme = Theme.of(context).colorScheme;
    return Row(
      children: [
        Icon(icon, color: colorScheme.primary, size: 24),
        const SizedBox(width: 8),
        Text(
          title,
          style: GoogleFonts.outfit(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: colorScheme.onSurface,
          ),
        ),
      ],
    );
  }

  // ============== DAY TIMELINE ==============

  Widget _buildDayTimeline(List<ScheduleEntry> entries) {
    if (entries.isEmpty) {
      return Card(
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Icon(Icons.person_off, color: Colors.grey.shade400),
              const SizedBox(width: 12),
              Text(
                'Nikogo dzisiaj nie ma w grafiku',
                style: TextStyle(color: Colors.grey.shade600),
              ),
            ],
          ),
        ),
      );
    }

    // Parse entries and sort by start time
    final parsedEntries = entries.map((e) {
      final startParts = e.startTime.split(':');
      final endParts = e.endTime.split(':');
      final startMinutes = int.parse(startParts[0]) * 60 + int.parse(startParts[1]);
      final endMinutes = int.parse(endParts[0]) * 60 + int.parse(endParts[1]);
      return _TimelineEntry(
        entry: e,
        startMinutes: startMinutes,
        endMinutes: endMinutes <= startMinutes ? endMinutes + 24 * 60 : endMinutes,
      );
    }).toList()
      ..sort((a, b) => a.startMinutes.compareTo(b.startMinutes));

    // Determine time range to display
    final minHour = (parsedEntries.first.startMinutes ~/ 60).clamp(0, 23);
    final maxHour = ((parsedEntries.last.endMinutes + 59) ~/ 60).clamp(minHour + 1, 25);
    final totalMinutes = (maxHour - minHour) * 60;
    const pixelsPerMinute = 1.2;
    final totalHeight = totalMinutes * pixelsPerMinute;

    return SizedBox(
      height: totalHeight + 40,
      child: Stack(
        children: [
          // Hour markers
          for (int h = minHour; h <= maxHour; h++)
            Positioned(
              top: (h - minHour) * 60 * pixelsPerMinute,
              left: 0,
              right: 0,
              child: Row(
                children: [
                  SizedBox(
                    width: 48,
                    child: Text(
                      '${h.clamp(0, 23).toString().padLeft(2, '0')}:00',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: Colors.grey.shade500,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Container(
                      height: 0.5,
                      color: Colors.grey.shade300,
                    ),
                  ),
                ],
              ),
            ),

          // Current time indicator
          if (_isCurrentTimeInRange(minHour, maxHour))
            Positioned(
              top: _currentTimeOffset(minHour, pixelsPerMinute),
              left: 44,
              right: 0,
              child: Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: Colors.red.shade600,
                      shape: BoxShape.circle,
                    ),
                  ),
                  Expanded(
                    child: Container(
                      height: 1.5,
                      color: Colors.red.shade600,
                    ),
                  ),
                ],
              ),
            ),

          // Event blocks
          ..._layoutEvents(parsedEntries, minHour, pixelsPerMinute),
        ],
      ),
    );
  }

  bool _isCurrentTimeInRange(int minHour, int maxHour) {
    final now = DateTime.now();
    final currentHour = now.hour;
    return currentHour >= minHour && currentHour < maxHour;
  }

  double _currentTimeOffset(int minHour, double pixelsPerMinute) {
    final now = DateTime.now();
    final minutesSinceStart = (now.hour - minHour) * 60 + now.minute;
    return minutesSinceStart * pixelsPerMinute;
  }

  List<Widget> _layoutEvents(List<_TimelineEntry> entries, int minHour, double pixelsPerMinute) {
    final colorScheme = Theme.of(context).colorScheme;
    // Simple column layout — group overlapping events into columns
    final widgets = <Widget>[];
    final columns = <List<_TimelineEntry>>[];

    for (final entry in entries) {
      bool placed = false;
      for (final col in columns) {
        if (col.last.endMinutes <= entry.startMinutes) {
          col.add(entry);
          placed = true;
          break;
        }
      }
      if (!placed) {
        columns.add([entry]);
      }
    }

    final totalColumns = columns.length;
    final availableWidth = MediaQuery.of(context).size.width - 48 - 32 - 16; // padding + time label

    for (int colIdx = 0; colIdx < totalColumns; colIdx++) {
      for (final entry in columns[colIdx]) {
        final top = (entry.startMinutes - minHour * 60) * pixelsPerMinute;
        final height = ((entry.endMinutes - entry.startMinutes) * pixelsPerMinute).clamp(30.0, 9999.0);
        final colWidth = availableWidth / totalColumns;
        final left = 56.0 + colIdx * colWidth;

        // Generate a color based on role name hash for variety
        final hue = (entry.entry.roleName.hashCode % 360).abs().toDouble();
        final eventColor = HSLColor.fromAHSL(1.0, hue, 0.55, 0.55).toColor();

        widgets.add(
          Positioned(
            top: top,
            left: left,
            width: colWidth - 4,
            height: height,
            child: Container(
              decoration: BoxDecoration(
                color: eventColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(10),
                border: Border(
                  left: BorderSide(color: eventColor, width: 3.5),
                ),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        radius: 11,
                        backgroundColor: eventColor.withOpacity(0.2),
                        child: Text(
                          entry.entry.userName.isNotEmpty ? entry.entry.userName[0].toUpperCase() : '?',
                          style: TextStyle(fontSize: 11, color: eventColor, fontWeight: FontWeight.bold),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          entry.entry.userName,
                          style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 12.5),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: eventColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      entry.entry.roleName,
                      style: TextStyle(fontSize: 10, color: eventColor.withOpacity(0.9), fontWeight: FontWeight.w500),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (height > 60.0) ...[
                    const Spacer(),
                    Text(
                      '${entry.entry.startTime.substring(0, 5)} - ${entry.entry.endTime.substring(0, 5)}',
                      style: TextStyle(fontSize: 10, color: Colors.grey.shade600),
                    ),
                  ],
                ],
              ),
            ),
          ),
        );
      }
    }

    return widgets;
  }

  // ============== WEEK VIEW ==============

  Widget _buildWeekView() {
    final colorScheme = Theme.of(context).colorScheme;
    final weekStart = _weekStart;
    final days = List.generate(7, (i) => weekStart.add(Duration(days: i)));
    final today = DateTime.now();

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
                '${DateFormat('d MMM', 'pl_PL').format(weekStart)} – ${DateFormat('d MMM yyyy', 'pl_PL').format(days.last)}',
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
          final dayEntries = _weekEntries.where((e) =>
            e.date.year == day.year && e.date.month == day.month && e.date.day == day.day
          ).toList()
            ..sort((a, b) => a.startTime.compareTo(b.startTime));

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
                          color: dayEntries.isEmpty
                              ? Colors.grey.shade200
                              : colorScheme.primaryContainer,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '${dayEntries.length} ${dayEntries.length == 1 ? 'zmiana' : 'zmian'}' ,
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: dayEntries.isEmpty
                                ? Colors.grey.shade600
                                : colorScheme.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // Entries
                if (dayEntries.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      'Brak zaplanowanych zmian',
                      style: GoogleFonts.inter(fontSize: 13, color: Colors.grey.shade500),
                    ),
                  )
                else
                  ...dayEntries.map((entry) {
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
                                    fontWeight: FontWeight.w600,
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

  // ============== MISSING CONFIRMATIONS ==============

  Widget _buildMissingConfirmationsList(List<Map<String, dynamic>> items) {
    final colorScheme = Theme.of(context).colorScheme;

    if (items.isEmpty) {
      return Card(
        color: Colors.green.shade50,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Icon(Icons.check_circle_outline, color: Colors.green.shade600),
              const SizedBox(width: 12),
              Text(
                'Wszystkie obecności potwierdzone',
                style: TextStyle(color: Colors.green.shade800),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        final userName = item['user_name'] ?? 'Nieznany';
        final dateStr = item['date'] ?? '';

        return Card(
          elevation: 1,
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: Colors.orange.shade100,
              child: Icon(Icons.warning, color: Colors.orange.shade700, size: 20),
            ),
            title: Text(userName, style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text('Brak potwierdzenia obecności z dnia $dateStr'),
            trailing: OutlinedButton(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Przejdź do zakładki "Obecności", aby zarządzać')),
                );
              },
              child: const Text('Sprawdź'),
            ),
          ),
        );
      },
    );
  }
}

class _TimelineEntry {
  final ScheduleEntry entry;
  final int startMinutes;
  final int endMinutes;

  _TimelineEntry({required this.entry, required this.startMinutes, required this.endMinutes});
}
