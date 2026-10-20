import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';
import '../../widgets/schedule_viewer.dart';

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
  bool _teamLoading = false;
  List<ScheduleEntry> _teamEntries = [];
  Map<String, dynamic>? _summary;
  bool _teamGridView = true;
  List<AnnouncementModel> _unreadAnnouncements = [];
  List<Map<String, dynamic>> _missingAttendances = [];
  List<Map<String, dynamic>> _directSwapProposals = [];

  static DateTime _getMonday(DateTime date) {
    return date.subtract(Duration(days: date.weekday - 1));
  }

  DateTime get _selectedWeekEnd =>
      _selectedWeekStart.add(const Duration(days: 6));

  @override
  void initState() {
    super.initState();
    _loadSchedule();
    _loadSummary();
    _loadHomeExtras();
  }

  Future<void> _loadHomeExtras() async {
    final api = ref.read(apiServiceProvider);
    try {
      final announcements = await api.getEmployeeAnnouncements();
      if (mounted) {
        setState(() {
          _unreadAnnouncements =
              announcements.where((a) => !a.isRead).toList();
        });
      }
    } catch (_) {}

    try {
      final missingResp = await api.getMissingAttendance();
      final rawList = missingResp['missing'] as List<dynamic>? ?? [];
      if (mounted) {
        setState(() {
          _missingAttendances =
              rawList
                  .map((e) => Map<String, dynamic>.from(e as Map))
                  .toList();
        });
      }
    } catch (_) {}

    try {
      final giveaways = await api.getEmployeeGiveaways();
      final directSwaps =
          giveaways.where((g) => g['is_direct_swap'] == true).toList();
      if (mounted) {
        setState(() {
          _directSwapProposals = directSwaps;
        });
      }
    } catch (_) {}
  }

  Future<void> _loadSummary() async {
    try {
      final now = DateTime.now();
      final data = await ref
          .read(apiServiceProvider)
          .getScheduleSummary(
            year: now.year,
            month: now.month,
            weekStart: _selectedWeekStart,
            weekEnd: _selectedWeekEnd,
          );
      if (mounted) setState(() => _summary = data);
    } catch (_) {
      // summary is optional, ignore errors
    }
  }

  Future<void> _loadSchedule() async {
    setState(() => _isLoading = true);

    try {
      final schedules = await ref
          .read(apiServiceProvider)
          .getEmployeeSchedule(_selectedWeekStart, _selectedWeekEnd);

      setState(() {
        _scheduleEntries = schedules;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Błąd ładowania: $e')));
      }
    }
  }

  void _previousWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.subtract(const Duration(days: 7));
    });
    _loadSchedule();
    _loadSummary();
    if (_showCoworkers) _loadTeamSchedule();
  }

  void _nextWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.add(const Duration(days: 7));
    });
    _loadSchedule();
    _loadSummary();
    if (_showCoworkers) _loadTeamSchedule();
  }

  Future<void> _loadTeamSchedule() async {
    setState(() => _teamLoading = true);
    try {
      final entries = await ref
          .read(apiServiceProvider)
          .getTeamSchedule(_selectedWeekStart, _selectedWeekEnd);
      if (mounted) {
        setState(() {
          _teamEntries = entries;
          _teamLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _teamLoading = false);
    }
  }

  Widget _buildDirectSwapProposalsSection() {
    if (_directSwapProposals.isEmpty) return const SizedBox.shrink();
    final colorScheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.swap_horiz, color: colorScheme.primary, size: 22),
              const SizedBox(width: 8),
              Text(
                'Prośby o wymianę zmian (${_directSwapProposals.length})',
                style: GoogleFonts.outfit(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: colorScheme.primary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ..._directSwapProposals.map((item) {
            final id = item['id'].toString();
            final offeredByName =
                item['offered_by_name']?.toString() ?? 'Pracownik';

            final offeredDateRaw = item['date']?.toString() ?? '';
            final offeredDate = DateTime.tryParse(offeredDateRaw);
            final offeredDateLabel =
                offeredDate != null
                    ? DateFormat('EEE, d MMM yyyy', 'pl_PL').format(offeredDate)
                    : offeredDateRaw;
            final offeredShift = item['shift_name']?.toString() ?? '';
            final offeredStart = _formatTimeWithoutSeconds(
              item['start_time']?.toString() ?? '',
            );
            final offeredEnd = _formatTimeWithoutSeconds(
              item['end_time']?.toString() ?? '',
            );
            final roleName = item['role_name']?.toString();

            final targetDateRaw = item['target_date']?.toString() ?? '';
            final targetDate = DateTime.tryParse(targetDateRaw);
            final targetDateLabel =
                targetDate != null
                    ? DateFormat('EEE, d MMM yyyy', 'pl_PL').format(targetDate)
                    : targetDateRaw;
            final targetShift = item['target_shift_name']?.toString() ?? '';
            final targetStart = _formatTimeWithoutSeconds(
              item['target_start_time']?.toString() ?? '',
            );
            final targetEnd = _formatTimeWithoutSeconds(
              item['target_end_time']?.toString() ?? '',
            );

            return Card(
              margin: const EdgeInsets.only(bottom: 10),
              color: Colors.white,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(
                  color: colorScheme.primary.withValues(alpha: 0.4),
                  width: 1.5,
                ),
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
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: colorScheme.primary,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text(
                            'PROPOZYCJA WYMIANY',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '$offeredByName proponuje wymianę',
                            style: GoogleFonts.inter(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: const Color(0xFF0F172A),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    LayoutBuilder(
                      builder: (context, constraints) {
                        final isMobile = constraints.maxWidth < 600;

                        Widget buildShiftCard({
                          required String title,
                          required String dateLabel,
                          required String shiftName,
                          required String timeRange,
                          String? role,
                          required bool isOffered,
                        }) {
                          return Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color:
                                  isOffered
                                      ? const Color(0xFFF1F5F9)
                                      : colorScheme.primaryContainer.withValues(
                                        alpha: 0.25,
                                      ),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color:
                                    isOffered
                                        ? const Color(0xFFE2E8F0)
                                        : colorScheme.primary.withValues(
                                          alpha: 0.3,
                                        ),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  title,
                                  style: GoogleFonts.inter(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color:
                                        isOffered
                                            ? const Color(0xFF64748B)
                                            : colorScheme.primary,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  dateLabel,
                                  style: GoogleFonts.inter(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                    color: const Color(0xFF0F172A),
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  '$shiftName • $timeRange${role != null ? ' ($role)' : ''}',
                                  style: GoogleFonts.inter(
                                    fontSize: 12,
                                    color: const Color(0xFF475569),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }

                        final offeredCard = buildShiftCard(
                          title: 'OTRZYMASZ (od: $offeredByName)',
                          dateLabel: offeredDateLabel,
                          shiftName: offeredShift,
                          timeRange: '$offeredStart – $offeredEnd',
                          role: roleName,
                          isOffered: true,
                        );

                        final targetCard = buildShiftCard(
                          title: 'ODDASZ (Twoja zmiana)',
                          dateLabel: targetDateLabel,
                          shiftName: targetShift,
                          timeRange: '$targetStart – $targetEnd',
                          isOffered: false,
                        );

                        if (isMobile) {
                          return Column(
                            children: [
                              offeredCard,
                              const Padding(
                                padding: EdgeInsets.symmetric(vertical: 6),
                                child: Icon(
                                  Icons.arrow_downward,
                                  size: 20,
                                  color: Color(0xFF94A3B8),
                                ),
                              ),
                              targetCard,
                            ],
                          );
                        }

                        return Row(
                          children: [
                            Expanded(child: offeredCard),
                            const Padding(
                              padding: EdgeInsets.symmetric(horizontal: 10),
                              child: Icon(
                                Icons.swap_horiz,
                                size: 24,
                                color: Color(0xFF94A3B8),
                              ),
                            ),
                            Expanded(child: targetCard),
                          ],
                        );
                      },
                    ),
                    const SizedBox(height: 14),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        OutlinedButton.icon(
                          onPressed: () async {
                            final confirm = await showDialog<bool>(
                              context: context,
                              builder:
                                  (ctx) => AlertDialog(
                                    title: const Text('Odrzucenie propozycji'),
                                    content: Text(
                                      'Czy na pewno chcesz odrzucić propozycję wymiany od użytkownika $offeredByName?',
                                    ),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.pop(ctx, false),
                                        child: const Text('Wróć'),
                                      ),
                                      FilledButton(
                                        style: FilledButton.styleFrom(
                                          backgroundColor: Colors.red.shade700,
                                        ),
                                        onPressed: () => Navigator.pop(ctx, true),
                                        child: const Text('Odrzuć'),
                                      ),
                                    ],
                                  ),
                            );
                            if (confirm == true) {
                              try {
                                await ref
                                    .read(apiServiceProvider)
                                    .cancelEmployeeGiveaway(id);
                                if (mounted) {
                                  setState(() {
                                    _directSwapProposals.removeWhere(
                                      (g) => g['id'].toString() == id,
                                    );
                                  });
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text('Odrzucono propozycję wymiany'),
                                    ),
                                  );
                                }
                              } catch (e) {
                                if (mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('Błąd: $e')),
                                  );
                                }
                              }
                            }
                          },
                          icon: const Icon(Icons.close, size: 16),
                          label: const Text('Odrzuć'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.red.shade700,
                            side: BorderSide(color: Colors.red.shade200),
                          ),
                        ),
                        const SizedBox(width: 10),
                        FilledButton.icon(
                          onPressed: () async {
                            final confirm = await showDialog<bool>(
                              context: context,
                              builder:
                                  (ctx) => AlertDialog(
                                    title: const Text('Akceptacja wymiany zmian'),
                                    content: Text(
                                      'Czy na pewno chcesz zaakceptować wymianę zmian z użytkownikiem $offeredByName? Twoja zmiana zostanie z nim zamieniona natychmiast.',
                                    ),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.pop(ctx, false),
                                        child: const Text('Anuluj'),
                                      ),
                                      FilledButton(
                                        onPressed: () => Navigator.pop(ctx, true),
                                        child: const Text('Zaakceptuj'),
                                      ),
                                    ],
                                  ),
                            );
                            if (confirm == true) {
                              try {
                                await ref
                                    .read(apiServiceProvider)
                                    .claimGiveaway(id);
                                if (mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text(
                                        '✓ Wymiana zmian została pomyślnie zrealizowana!',
                                      ),
                                      backgroundColor: Colors.green,
                                    ),
                                  );
                                  _loadSchedule();
                                  _loadSummary();
                                  _loadHomeExtras();
                                }
                              } catch (e) {
                                if (mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('Błąd: $e')),
                                  );
                                }
                              }
                            }
                          },
                          icon: const Icon(Icons.check, size: 16),
                          label: const Text('Zaakceptuj wymianę'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildUnreadAnnouncementsSection() {
    if (_unreadAnnouncements.isEmpty) return const SizedBox.shrink();
    final colorScheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.campaign, color: colorScheme.primary, size: 20),
              const SizedBox(width: 8),
              Text(
                'Nowe ogłoszenia (${_unreadAnnouncements.length})',
                style: GoogleFonts.outfit(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: colorScheme.primary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ..._unreadAnnouncements.map(
            (ann) => Card(
              margin: const EdgeInsets.only(bottom: 8),
              color: colorScheme.primaryContainer.withValues(alpha: 0.25),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(color: colorScheme.primary, width: 1.5),
              ),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          margin: const EdgeInsets.only(right: 8),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: colorScheme.primary,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text(
                            'NOWE OGŁOSZENIE',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        Expanded(
                          child: Text(
                            ann.title,
                            style: GoogleFonts.outfit(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(ann.content),
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          '${ann.authorName} • ${DateFormat('dd.MM.yyyy HH:mm').format(ann.createdAt.toLocal())}',
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.grey.shade600,
                          ),
                        ),
                        FilledButton.icon(
                          onPressed: () async {
                            await ref
                                .read(apiServiceProvider)
                                .markAnnouncementRead(ann.id);
                            if (mounted) {
                              setState(() {
                                _unreadAnnouncements.removeWhere(
                                  (a) => a.id == ann.id,
                                );
                              });
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text(
                                    'Ogłoszenie oznaczone jako przeczytane (dostępne w zakładce Operacje)',
                                  ),
                                ),
                              );
                            }
                          },
                          icon: const Icon(Icons.done_all, size: 16),
                          label: const Text('Zapoznałem się'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMissingAttendanceBanner() {
    if (_missingAttendances.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        color: Colors.orange.shade50,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: Colors.orange.shade400, width: 1.5),
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.warning_amber_rounded,
                    color: Colors.orange.shade900,
                    size: 22,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Brakujące rejestracje obecności (${_missingAttendances.length})',
                      style: GoogleFonts.outfit(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.orange.shade900,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Poniższe zakończone zmiany z grafiku nie mają jeszcze zarejestrowanej obecności:',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: Colors.orange.shade900,
                ),
              ),
              const SizedBox(height: 10),
              ..._missingAttendances.map((item) {
                final rawDate = item['date']?.toString() ?? '';
                final parsedDate = DateTime.tryParse(rawDate);
                final dateLabel =
                    parsedDate != null
                        ? DateFormat('EEEE, d MMM yyyy', 'pl_PL').format(
                          parsedDate,
                        )
                        : rawDate;
                final shiftName = item['shift_name']?.toString() ?? '';
                final startTime = item['start_time']?.toString() ?? '';
                final endTime = item['end_time']?.toString() ?? '';
                final roleName = item['role_name']?.toString() ?? '';

                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.orange.shade200),
                  ),
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    alignment: WrapAlignment.spaceBetween,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '$dateLabel • $shiftName ($roleName)',
                            style: GoogleFonts.inter(
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                            ),
                          ),
                          Text(
                            'Godziny w grafiku: $startTime - $endTime',
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey.shade700,
                            ),
                          ),
                        ],
                      ),
                      Wrap(
                        spacing: 6,
                        children: [
                          OutlinedButton.icon(
                            onPressed:
                                parsedDate == null
                                    ? null
                                    : () => _showRegisterMissingDialog(
                                      date: parsedDate,
                                      shiftName: shiftName,
                                      startTime: startTime,
                                      endTime: endTime,
                                      initialAbsent: true,
                                    ),
                            icon: const Icon(
                              Icons.person_off_outlined,
                              size: 16,
                            ),
                            label: const Text('Nieobecny'),
                            style: OutlinedButton.styleFrom(
                              visualDensity: VisualDensity.compact,
                              foregroundColor: Colors.deepOrange.shade800,
                              side: BorderSide(
                                color: Colors.deepOrange.shade300,
                              ),
                            ),
                          ),
                          FilledButton.icon(
                            onPressed:
                                parsedDate == null
                                    ? null
                                    : () => _showRegisterMissingDialog(
                                      date: parsedDate,
                                      shiftName: shiftName,
                                      startTime: startTime,
                                      endTime: endTime,
                                      initialAbsent: false,
                                    ),
                            icon: const Icon(Icons.how_to_reg, size: 16),
                            label: const Text('Zarejestruj'),
                            style: FilledButton.styleFrom(
                              visualDensity: VisualDensity.compact,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              }),
            ],
          ),
        ),
      ),
    );
  }

  String _formatTimeWithoutSeconds(String time) {
    final parts = time.split(':');
    if (parts.length >= 2) {
      return '${parts[0].padLeft(2, '0')}:${parts[1].padLeft(2, '0')}';
    }
    return time;
  }

  String _formatHours(double hours) {
    if (hours % 1 == 0) {
      return '${hours.toInt()} godz.';
    }
    return '${hours.toStringAsFixed(1)} godz.';
  }

  Widget _buildKpiCard({
    required String title,
    required String value,
    String? subtitle,
    required IconData icon,
  }) {
    return Card(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F5247).withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    icon,
                    size: 18,
                    color: const Color(0xFF0F5247),
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  title,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: const Color(0xFF64748B),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              value,
              style: GoogleFonts.inter(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: const Color(0xFF0F172A),
                letterSpacing: -0.5,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  color: const Color(0xFF94A3B8),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildKpiCardsHorizontal() {
    if (_summary == null) return const SizedBox.shrink();

    final weekHours = (_summary!['week_hours'] as num?)?.toDouble() ?? 0.0;
    final monthHours = (_summary!['month_hours'] as num?)?.toDouble() ?? 0.0;
    final lastScheduledDate = _summary!['last_scheduled_date'] as String?;
    final now = DateTime.now();

    String? monthSubtitle;
    if (lastScheduledDate != null) {
      final lastDate = DateTime.parse(lastScheduledDate);
      final lastDayOfMonth = DateTime(now.year, now.month + 1, 0);
      if (lastDate.day < lastDayOfMonth.day) {
        monthSubtitle = 'Grafik do ${DateFormat('d MMM', 'pl_PL').format(lastDate)}';
      }
    }

    return Row(
      children: [
        Expanded(
          child: _buildKpiCard(
            title: 'Ten tydzień',
            value: _formatHours(weekHours),
            icon: Icons.calendar_view_week,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildKpiCard(
            title: 'Ten miesiąc',
            value: _formatHours(monthHours),
            subtitle: monthSubtitle,
            icon: Icons.calendar_month,
          ),
        ),
      ],
    );
  }

  Widget _buildKpiCardsVertical() {
    if (_summary == null) return const SizedBox.shrink();

    final weekHours = (_summary!['week_hours'] as num?)?.toDouble() ?? 0.0;
    final monthHours = (_summary!['month_hours'] as num?)?.toDouble() ?? 0.0;
    final lastScheduledDate = _summary!['last_scheduled_date'] as String?;
    final now = DateTime.now();

    String? monthSubtitle;
    if (lastScheduledDate != null) {
      final lastDate = DateTime.parse(lastScheduledDate);
      final lastDayOfMonth = DateTime(now.year, now.month + 1, 0);
      if (lastDate.day < lastDayOfMonth.day) {
        monthSubtitle = 'Grafik do ${DateFormat('d MMM', 'pl_PL').format(lastDate)}';
      }
    }

    return Column(
      children: [
        _buildKpiCard(
          title: 'Ten tydzień',
          value: _formatHours(weekHours),
          icon: Icons.calendar_view_week,
        ),
        const SizedBox(height: 12),
        _buildKpiCard(
          title: 'Ten miesiąc',
          value: _formatHours(monthHours),
          subtitle: monthSubtitle,
          icon: Icons.calendar_month,
        ),
      ],
    );
  }

  Widget _buildSidebarAuxiliaryCard() {
    return Card(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.info_outline,
                  size: 18,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'Wskazówki',
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: const Color(0xFF0F172A),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              '• Pamiętaj o rejestracji obecności w dniu zmiany.\n'
              '• Zmianę możesz oddać na giełdę przed jej rozpoczęciem.\n'
              '• Zakładka "Cała załoga" pozwala sprawdzić obsadę zespołu.',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: const Color(0xFF64748B),
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildShiftActionButtons(
    EmployeeScheduleEntry shift,
    bool isToday,
    bool isPast,
  ) {
    final buttons = <Widget>[];

    if (!isPast) {
      if (shift.isOnGiveaway) {
        buttons.add(
          OutlinedButton.icon(
            onPressed: null,
            icon: const Icon(
              Icons.check_circle_outline,
              size: 16,
              color: Colors.purple,
            ),
            label: const Text(
              'Wystawiono na giełdę',
              style: TextStyle(color: Colors.purple, fontSize: 13),
            ),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(110, 36),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              side: BorderSide(color: Colors.purple.shade200),
            ),
          ),
        );
      } else {
        buttons.add(
          OutlinedButton.icon(
            onPressed: () => _showGiveawayConfirmation(shift),
            icon: Icon(Icons.swap_horiz, size: 16, color: Colors.grey.shade700),
            label: Text(
              'Oddaj zmianę',
              style: GoogleFonts.inter(
                color: Colors.grey.shade700,
                fontSize: 13,
              ),
            ),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(110, 36),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              side: const BorderSide(color: Color(0xFFCBD5E1)),
            ),
          ),
        );
      }
    }

    if (isToday) {
      buttons.add(
        FilledButton.icon(
          onPressed: () => _showRegisterPresenceDialog(shift),
          icon: const Icon(Icons.how_to_reg, size: 16),
          label: const Text('Zarejestruj obecność', style: TextStyle(fontSize: 13)),
          style: FilledButton.styleFrom(
            minimumSize: const Size(130, 36),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          ),
        ),
      );
    }

    if (buttons.isEmpty) return const SizedBox.shrink();

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.end,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: buttons,
    );
  }

  Widget _buildShiftItem(
    EmployeeScheduleEntry shift,
    DateTime date,
    bool isToday,
    bool isPast,
  ) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth >= 768;

        final shiftDetails = Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isToday
                    ? const Color(0xFF0F5247).withValues(alpha: 0.12)
                    : const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                Icons.access_time_filled,
                color: isToday
                    ? const Color(0xFF0F5247)
                    : const Color(0xFF64748B),
                size: 20,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          shift.shiftName,
                          style: GoogleFonts.inter(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: const Color(0xFF0F172A),
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (shift.isOnGiveaway) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.purple.shade50,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: Colors.purple.shade200),
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
                  Wrap(
                    spacing: 12,
                    runSpacing: 4,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.schedule,
                            size: 14,
                            color: Color(0xFF64748B),
                          ),
                          const SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              '${_formatTimeWithoutSeconds(shift.startTime)} - ${_formatTimeWithoutSeconds(shift.endTime)}',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: const Color(0xFF64748B),
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.badge_outlined,
                            size: 14,
                            color: Color(0xFF64748B),
                          ),
                          const SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              shift.roleName,
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: const Color(0xFF64748B),
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        );

        final actions = _buildShiftActionButtons(shift, isToday, isPast);

        if (isWide) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              children: [
                Expanded(child: shiftDetails),
                const SizedBox(width: 16),
                Flexible(
                  fit: FlexFit.loose,
                  child: actions,
                ),
              ],
            ),
          );
        } else {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                shiftDetails,
                if (!isPast || isToday) ...[
                  const SizedBox(height: 10),
                  Align(
                    alignment: Alignment.centerRight,
                    child: actions,
                  ),
                ],
              ],
            ),
          );
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final isWideScreen = constraints.maxWidth > 960;

        final weekSelector = Card(
          elevation: 0,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: const Icon(Icons.chevron_left),
                  onPressed: _previousWeek,
                  tooltip: 'Poprzedni tydzień',
                ),
                Text(
                  '${DateFormat('d MMM', 'pl_PL').format(_selectedWeekStart)} - ${DateFormat('d MMM yyyy', 'pl_PL').format(_selectedWeekEnd)}',
                  style: GoogleFonts.inter(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: const Color(0xFF0F172A),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.chevron_right),
                  onPressed: _nextWeek,
                  tooltip: 'Następny tydzień',
                ),
              ],
            ),
          ),
        );

        final shiftsHeader = Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              _showCoworkers ? 'Cała załoga' : 'Twoje zmiany',
              style: GoogleFonts.outfit(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: const Color(0xFF0F172A),
              ),
            ),
            TextButton.icon(
              onPressed: () {
                _loadSchedule();
                _loadHomeExtras();
                if (_showCoworkers) _loadTeamSchedule();
              },
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Odśwież'),
            ),
          ],
        );

        final modeToggle = Center(
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
            onSelectionChanged: (v) {
              final newVal = v.first;
              setState(() => _showCoworkers = newVal);
              if (newVal) _loadTeamSchedule();
            },
            style: SegmentedButton.styleFrom(
              selectedBackgroundColor:
                  const Color(0xFF0F5247).withValues(alpha: 0.12),
              selectedForegroundColor: const Color(0xFF0F5247),
            ),
          ),
        );

        Widget shiftsOrTeamContent;
        if (_showCoworkers) {
          shiftsOrTeamContent = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Container(
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerLow,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _viewModeButton(
                          Icons.view_list_rounded,
                          !_teamGridView,
                          () => setState(() => _teamGridView = false),
                        ),
                        _viewModeButton(
                          Icons.grid_view_rounded,
                          _teamGridView,
                          () => setState(() => _teamGridView = true),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              if (_teamLoading)
                const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_teamEntries.isEmpty)
                Center(
                  child: Padding(
                    padding: const EdgeInsets.all(48),
                    child: Column(
                      children: [
                        Icon(
                          Icons.people_outline,
                          size: 64,
                          color: Colors.grey.shade400,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Brak zaplanowanych zmian zespołu',
                          style: GoogleFonts.outfit(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            color: Colors.grey.shade600,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'W tym tygodniu żaden pracownik nie ma jeszcze opublikowanego grafiku.',
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            color: Colors.grey.shade500,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                )
              else if (_teamGridView)
                _buildTeamGridView()
              else
                _buildTeamWeekView(),
            ],
          );
        } else {
          if (_scheduleEntries.isEmpty) {
            shiftsOrTeamContent = Center(
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
                      'Grafik nie został jeszcze opublikowany lub nie masz zmian w tym tygodniu. Przełącz na "Cała załoga", aby sprawdzić grafik współpracowników.',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: Colors.grey.shade500,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            );
          } else {
            final grouped = _groupByDate(_scheduleEntries);
            shiftsOrTeamContent = Column(
              children: grouped.entries.map((entry) {
                final date = entry.key;
                final shifts = entry.value;
                final isToday = _isToday(date);
                final isPast = _isPast(date);

                return Opacity(
                  opacity: isPast ? 0.65 : 1.0,
                  child: Card(
                    margin: const EdgeInsets.only(bottom: 12),
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: BorderSide(
                        color: isToday
                            ? const Color(0xFF0F5247)
                            : const Color(0xFFE2E8F0),
                        width: isToday ? 1.8 : 1,
                      ),
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
                                  horizontal: 10,
                                  vertical: 4,
                                ),
                                decoration: BoxDecoration(
                                  color: isToday
                                      ? const Color(0xFF0F5247)
                                      : const Color(0xFFF1F5F9),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  isToday
                                      ? 'DZISIAJ'
                                      : DateFormat(
                                          'EEE',
                                          'pl_PL',
                                        ).format(date).toUpperCase(),
                                  style: GoogleFonts.inter(
                                    color: isToday
                                        ? Colors.white
                                        : const Color(0xFF475569),
                                    fontWeight: FontWeight.bold,
                                    fontSize: 11,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Text(
                                DateFormat('d MMMM yyyy', 'pl_PL').format(date),
                                style: GoogleFonts.inter(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                  color: isPast
                                      ? const Color(0xFF64748B)
                                      : const Color(0xFF0F172A),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          const Divider(height: 1, color: Color(0xFFE2E8F0)),
                          const SizedBox(height: 4),
                          ...shifts.map(
                            (shift) =>
                                _buildShiftItem(shift, date, isToday, isPast),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            );
          }
        }

        return Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1280),
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildDirectSwapProposalsSection(),
                  _buildUnreadAnnouncementsSection(),
                  _buildMissingAttendanceBanner(),
                  if (!isWideScreen) ...[
                    // Mobile / Single column flow
                    weekSelector,
                    const SizedBox(height: 12),
                    if (_summary != null) ...[
                      _buildKpiCardsHorizontal(),
                      const SizedBox(height: 12),
                    ],
                    shiftsHeader,
                    const SizedBox(height: 8),
                    modeToggle,
                    const SizedBox(height: 12),
                    shiftsOrTeamContent,
                  ] else ...[
                    // Desktop / Two-column layout (> 960px)
                    // Left column (~68%), Right column (~32%)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          flex: 68,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              weekSelector,
                              const SizedBox(height: 14),
                              shiftsHeader,
                              const SizedBox(height: 8),
                              modeToggle,
                              const SizedBox(height: 14),
                              shiftsOrTeamContent,
                            ],
                          ),
                        ),
                        const SizedBox(width: 24),
                        Expanded(
                          flex: 32,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (_summary != null) ...[
                                _buildKpiCardsVertical(),
                                const SizedBox(height: 16),
                              ],
                              _buildSidebarAuxiliaryCard(),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }
  Widget _viewModeButton(IconData icon, bool isActive, VoidCallback onTap) {
    final colorScheme = Theme.of(context).colorScheme;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: isActive ? colorScheme.primaryContainer : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(
          icon,
          size: 20,
          color: isActive ? colorScheme.primary : colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }

  Widget _buildTeamGridView() {
    final shiftsAsync = ref.watch(allShiftsProvider);
    final rolesAsync = ref.watch(rolesProvider);
    final user = ref.read(authProvider).value;
    final currentUserId = user?.id ?? '';
    final myRoleIds = user?.jobRoleIds ?? [];

    return ScheduleViewer(
      schedules: _teamEntries,
      shifts: shiftsAsync.valueOrNull ?? const [],
      roles: rolesAsync.valueOrNull ?? const [],
      weekStart: _selectedWeekStart,
      onAssignmentTap: (entry) {
        if (entry.userId != currentUserId &&
            myRoleIds.contains(entry.roleId) &&
            !_isPast(entry.date) &&
            !entry.isOnGiveaway) {
          _showDirectSwapFromTeamView(entry);
        }
      },
    );
  }

  Widget _buildTeamWeekView() {
    final colorScheme = Theme.of(context).colorScheme;
    final user = ref.read(authProvider).value;
    final currentUserId = user?.id ?? '';
    final days = List.generate(7, (i) => _selectedWeekStart.add(Duration(days: i)));
    final today = DateTime.now();

    final Map<DateTime, List<ScheduleEntry>> grouped = {};
    for (final entry in _teamEntries) {
      final key = DateTime(entry.date.year, entry.date.month, entry.date.day);
      grouped.putIfAbsent(key, () => []).add(entry);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: colorScheme.primaryContainer.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.date_range, size: 18, color: colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                '${DateFormat('d MMM', 'pl_PL').format(_selectedWeekStart)} – ${DateFormat('d MMM yyyy', 'pl_PL').format(days.last)}',
                style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600, color: colorScheme.onSurface),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        ...days.map((day) {
          final isToday = day.year == today.year && day.month == today.month && day.day == today.day;
          final dateKey = DateTime(day.year, day.month, day.day);
          final dayEntries = (grouped[dateKey] ?? [])..sort((a, b) => a.startTime.compareTo(b.startTime));

          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: isToday
                  ? Border.all(color: colorScheme.primary, width: 2)
                  : Border.all(color: colorScheme.outlineVariant.withValues(alpha: 0.4)),
              color: isToday ? colorScheme.primaryContainer.withValues(alpha: 0.15) : colorScheme.surface,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  decoration: BoxDecoration(
                    color: isToday ? colorScheme.primary.withValues(alpha: 0.08) : colorScheme.surfaceContainerLow,
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
                  ),
                  child: Row(
                    children: [
                      if (isToday) ...[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(color: colorScheme.primary, borderRadius: BorderRadius.circular(6)),
                          child: Text('DZIEŃ', style: GoogleFonts.inter(fontSize: 10, fontWeight: FontWeight.bold, color: colorScheme.onPrimary)),
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
                          color: dayEntries.isEmpty ? Colors.grey.shade200 : colorScheme.primaryContainer,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '${dayEntries.length} ${dayEntries.length == 1 ? 'zmiana' : 'zmian'}',
                          style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w600, color: dayEntries.isEmpty ? Colors.grey.shade600 : colorScheme.primary),
                        ),
                      ),
                    ],
                  ),
                ),
                if (dayEntries.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text('Brak zaplanowanych zmian', style: GoogleFonts.inter(fontSize: 13, color: Colors.grey.shade500)),
                  )
                else
                  ...dayEntries.map((entry) {
                    final isMe = entry.userId == currentUserId;
                    final myRoleIds = user?.jobRoleIds ?? [];
                    final hasMatchingRole = myRoleIds.contains(entry.roleId);
                    final isPastDay = _isPast(entry.date);
                    final hue = (entry.roleName.hashCode % 360).abs().toDouble();
                    final roleColor = HSLColor.fromAHSL(1.0, hue, 0.55, 0.55).toColor();
                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 80,
                            child: Text(
                              '${entry.startTime.substring(0, 5)}–${entry.endTime.substring(0, 5)}',
                              style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: Colors.grey.shade600),
                            ),
                          ),
                          Container(
                            width: isMe ? 4 : 3,
                            height: 32,
                            decoration: BoxDecoration(color: isMe ? colorScheme.primary : roleColor, borderRadius: BorderRadius.circular(2)),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(entry.userName, style: GoogleFonts.inter(fontSize: 13, fontWeight: isMe ? FontWeight.w800 : FontWeight.w600, color: isMe ? colorScheme.primary : null)),
                                    if (isMe) ...[
                                      const SizedBox(width: 6),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                        decoration: BoxDecoration(color: colorScheme.primaryContainer, borderRadius: BorderRadius.circular(4)),
                                        child: Text('TY', style: TextStyle(fontSize: 9, color: colorScheme.primary, fontWeight: FontWeight.w800)),
                                      ),
                                    ],
                                  ],
                                ),
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                      decoration: BoxDecoration(color: roleColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(4)),
                                      child: Text(entry.roleName, style: TextStyle(fontSize: 10, color: roleColor, fontWeight: FontWeight.w600)),
                                    ),
                                    const SizedBox(width: 6),
                                    Text(entry.shiftName, style: GoogleFonts.inter(fontSize: 11, color: Colors.grey.shade500)),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          if (!isMe && hasMatchingRole && !isPastDay) ...[
                            const SizedBox(width: 8),
                            if (entry.isOnGiveaway)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.purple.shade50,
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: Colors.purple.shade300),
                                ),
                                child: Text(
                                  'GIEŁDA',
                                  style: GoogleFonts.inter(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.purple.shade700,
                                  ),
                                ),
                              )
                            else
                              OutlinedButton.icon(
                                onPressed: () => _showDirectSwapFromTeamView(entry),
                                icon: const Icon(Icons.swap_horiz, size: 14),
                                label: const Text('Wymień', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                                style: OutlinedButton.styleFrom(
                                  visualDensity: VisualDensity.compact,
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                  minimumSize: const Size(0, 30),
                                  side: BorderSide(color: colorScheme.primary.withValues(alpha: 0.5)),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                ),
                              ),
                          ],
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

  void _showDirectSwapFromTeamView(ScheduleEntry targetEntry) async {
    // 1. Gather all of current user's future shifts
    List<EmployeeScheduleEntry> candidateShifts = [];
    
    // First, from _scheduleEntries (already in state)
    for (final s in _scheduleEntries) {
      if (!_isPast(s.date) && !s.isOnGiveaway && s.id != targetEntry.id) {
        candidateShifts.add(s);
      }
    }

    // Also fetch upcoming 30 days so the employee can swap a future shift from upcoming weeks
    try {
      final upcoming = await ref.read(apiServiceProvider).getEmployeeSchedule(
            DateTime.now(),
            DateTime.now().add(const Duration(days: 30)),
          );
      final setIds = candidateShifts.map((e) => e.id).toSet();
      for (final u in upcoming) {
        if (!_isPast(u.date) && !u.isOnGiveaway && u.id != targetEntry.id && !setIds.contains(u.id)) {
          candidateShifts.add(u);
        }
      }
    } catch (_) {}

    candidateShifts.sort((a, b) => a.date.compareTo(b.date));

    if (!mounted) return;

    String? selectedMyShiftId = candidateShifts.isNotEmpty ? candidateShifts.first.id : null;
    bool isValidating = false;
    bool? canSwap;
    String? validationMessage;

    Future<void> runValidation(String offeredId, StateSetter setDialogState) async {
      setDialogState(() {
        isValidating = true;
        canSwap = null;
        validationMessage = null;
      });

      try {
        final res = await ref.read(apiServiceProvider).validateSwap(
              offeredId,
              targetEntry.id,
            );
        if (mounted) {
          setDialogState(() {
            isValidating = false;
            canSwap = res['can_swap'] as bool? ?? false;
            validationMessage = res['reason'] as String?;
          });
        }
      } catch (e) {
        if (mounted) {
          setDialogState(() {
            isValidating = false;
            canSwap = false;
            validationMessage = 'Błąd walidacji: $e';
          });
        }
      }
    }

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          if (selectedMyShiftId != null && canSwap == null && !isValidating) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              runValidation(selectedMyShiftId!, setDialogState);
            });
          }

          final colorScheme = Theme.of(context).colorScheme;

          return AlertDialog(
            title: Row(
              children: [
                Icon(Icons.swap_horiz, color: colorScheme.primary),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text('Wymiana ze współpracownikiem'),
                ),
              ],
            ),
            content: SizedBox(
              width: 480,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Target Shift Card
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: colorScheme.outlineVariant.withValues(alpha: 0.4)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              CircleAvatar(
                                radius: 14,
                                backgroundColor: colorScheme.primary,
                                child: Text(
                                  targetEntry.userName.isNotEmpty ? targetEntry.userName[0].toUpperCase() : '?',
                                  style: const TextStyle(fontSize: 12, color: Colors.white, fontWeight: FontWeight.bold),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  targetEntry.userName,
                                  style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 14),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: colorScheme.primaryContainer,
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  targetEntry.roleName,
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: colorScheme.primary,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Icon(Icons.calendar_today, size: 14, color: Colors.grey.shade600),
                              const SizedBox(width: 6),
                              Text(
                                DateFormat('EEEE, d MMMM yyyy', 'pl_PL').format(targetEntry.date),
                                style: GoogleFonts.inter(fontSize: 13, color: Colors.grey.shade800),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              Icon(Icons.access_time, size: 14, color: Colors.grey.shade600),
                              const SizedBox(width: 6),
                              Text(
                                '${targetEntry.shiftName} (${targetEntry.startTime.substring(0, 5)} - ${targetEntry.endTime.substring(0, 5)})',
                                style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w500),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 16),
                    Text(
                      'Wybierz swoją zmianę do oddania w zamian:',
                      style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 13),
                    ),
                    const SizedBox(height: 8),

                    if (candidateShifts.isEmpty)
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.amber.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.amber.shade300),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.info_outline, color: Colors.amber.shade900, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Nie masz żadnych przyszłych zmian, które mógłbyś zaoferować w zamian.',
                                style: GoogleFonts.inter(fontSize: 12, color: Colors.amber.shade900),
                              ),
                            ),
                          ],
                        ),
                      )
                    else
                      DropdownButtonFormField<String>(
                        isExpanded: true,
                        value: selectedMyShiftId,
                        decoration: InputDecoration(
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                        items: candidateShifts.map((s) {
                          final dateStr = DateFormat('E, d MMM', 'pl_PL').format(s.date);
                          return DropdownMenuItem<String>(
                            value: s.id,
                            child: Text(
                              '$dateStr • ${s.startTime.substring(0, 5)}-${s.endTime.substring(0, 5)} (${s.roleName})',
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 13),
                            ),
                          );
                        }).toList(),
                        onChanged: (newId) {
                          if (newId != null && newId != selectedMyShiftId) {
                            setDialogState(() {
                              selectedMyShiftId = newId;
                            });
                            runValidation(newId, setDialogState);
                          }
                        },
                      ),

                    const SizedBox(height: 16),

                    // Validation Status Box
                    if (isValidating)
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: colorScheme.surfaceContainerLow,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                'Sprawdzanie dostępności i grafiku współpracownika...',
                                style: GoogleFonts.inter(fontSize: 12, color: colorScheme.onSurfaceVariant),
                              ),
                            ),
                          ],
                        ),
                      )
                    else if (canSwap == true)
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.green.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.green.shade300),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.check_circle, color: Colors.green.shade700, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                '✓ Wymiana możliwa! Brak kolizji w grafiku współpracownika.',
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.green.shade800,
                                ),
                              ),
                            ),
                          ],
                        ),
                      )
                    else if (canSwap == false)
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.red.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.red.shade300),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(Icons.error_outline, color: Colors.red.shade700, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                validationMessage ?? 'Brak możliwości zaproponowania tej wymiany.',
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                  color: Colors.red.shade800,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                    const SizedBox(height: 12),
                    Text(
                      'Po wysłaniu propozycji współpracownik otrzyma powiadomienie. Bezpośrednia wymiana wejdzie w życie po jej zaakceptowaniu.',
                      style: GoogleFonts.inter(fontSize: 11, color: Colors.grey.shade600),
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Anuluj'),
              ),
              FilledButton(
                onPressed: (canSwap == true && !isValidating && selectedMyShiftId != null)
                    ? () {
                        Navigator.pop(context);
                        _submitGiveaway(
                          selectedMyShiftId!,
                          targetShiftId: targetEntry.id,
                        );
                      }
                    : null,
                child: const Text('Zaproponuj wymianę'),
              ),
            ],
          );
        },
      ),
    );
  }

  Map<DateTime, List<EmployeeScheduleEntry>> _groupByDate(
    List<EmployeeScheduleEntry> entries,
  ) {
    final Map<DateTime, List<EmployeeScheduleEntry>> grouped = {};

    for (var entry in entries) {
      final dateKey = DateTime(
        entry.date.year,
        entry.date.month,
        entry.date.day,
      );
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
    return date.year == now.year &&
        date.month == now.month &&
        date.day == now.day;
  }

  bool _isPast(DateTime date) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    return date.isBefore(today);
  }

  void _showRegisterPresenceDialog(EmployeeScheduleEntry shift) async {
    _showRegisterMissingDialog(
      date: shift.date,
      shiftName: shift.shiftName,
      startTime: shift.startTime,
      endTime: shift.endTime,
      initialAbsent: false,
    );
  }

  void _showRegisterMissingDialog({
    required DateTime date,
    required String shiftName,
    required String startTime,
    required String endTime,
    bool initialAbsent = false,
  }) async {
    final checkInController = TextEditingController(text: startTime);
    final checkOutController = TextEditingController(text: endTime);
    final absenceReasonController = TextEditingController();
    bool isAbsent = initialAbsent;
    String? errorMsg;

    showDialog(
      context: context,
      builder:
          (context) => StatefulBuilder(
            builder:
                (context, setDialogState) => AlertDialog(
                  title: const Text('Zarejestruj obecność'),
                  content: SizedBox(
                    width: 340,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Zmiana: $shiftName',
                          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                        ),
                        Text(
                          'Data: ${DateFormat('EEEE, d MMMM yyyy', 'pl_PL').format(date)}',
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.grey.shade700,
                          ),
                        ),
                        const SizedBox(height: 12),
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          controlAffinity: ListTileControlAffinity.leading,
                          value: isAbsent,
                          title: const Text(
                            'Nieobecny (nie przyszedłem na zmianę)',
                            style: TextStyle(fontSize: 14),
                          ),
                          onChanged: (val) {
                            setDialogState(() {
                              isAbsent = val ?? false;
                              errorMsg = null;
                            });
                          },
                        ),
                        const SizedBox(height: 12),
                        if (isAbsent)
                          TextField(
                            controller: absenceReasonController,
                            maxLines: 2,
                            decoration: InputDecoration(
                              labelText: 'Powód nieobecności *',
                              hintText: 'np. Choroba, nagła sytuacja losowa',
                              prefixIcon: const Icon(Icons.info_outline),
                              border: const OutlineInputBorder(),
                              errorText: errorMsg,
                            ),
                          )
                        else ...[
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
                          if (errorMsg != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              errorMsg!,
                              style: const TextStyle(
                                color: Colors.red,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ],
                      ],
                    ),
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Anuluj'),
                    ),
                    FilledButton(
                      onPressed: () {
                        if (isAbsent) {
                          final reason = absenceReasonController.text.trim();
                          if (reason.isEmpty) {
                            setDialogState(
                              () => errorMsg = 'Podaj powód nieobecności',
                            );
                            return;
                          }
                          Navigator.pop(context);
                          _submitAttendance(
                            date,
                            '00:00',
                            '00:00',
                            isAbsent: true,
                            absenceReason: reason,
                          );
                        } else {
                          final inVal = checkInController.text.trim();
                          final outVal = checkOutController.text.trim();
                          if (inVal.isEmpty || outVal.isEmpty) {
                            setDialogState(
                              () => errorMsg = 'Podaj godziny pracy',
                            );
                            return;
                          }
                          Navigator.pop(context);
                          _submitAttendance(date, inVal, outVal);
                        }
                      },
                      child: Text(isAbsent ? 'Zgłoś nieobecność' : 'Zapisz'),
                    ),
                  ],
                ),
          ),
    );
  }

  Future<void> _submitAttendance(
    DateTime date,
    String checkIn,
    String checkOut, {
    bool isAbsent = false,
    String? absenceReason,
  }) async {
    setState(() => _isLoading = true);
    try {
      await ref
          .read(apiServiceProvider)
          .registerAttendance(
            date,
            checkIn,
            checkOut,
            isAbsent: isAbsent,
            absenceReason: absenceReason,
          );
      await _loadHomeExtras();
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              isAbsent
                  ? '✓ Zgłoszono nieobecność na zmianie'
                  : '✓ Obecność zarejestrowana',
            ),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Błąd rejestracji: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }

  void _showGiveawayConfirmation(EmployeeScheduleEntry shift) async {
    List<ScheduleEntry> team = List.from(_teamEntries);
    if (team.isEmpty) {
      try {
        team = await ref
            .read(apiServiceProvider)
            .getTeamSchedule(_selectedWeekStart, _selectedWeekEnd);
      } catch (_) {}
    }

    final user = ref.read(authProvider).value;
    final currentUserId = user?.id ?? '';
    final coworkerShifts = team.where((e) => e.userId != currentUserId).toList();

    bool isDirectSwap = false;
    String? selectedTargetShiftId;

    if (!mounted) return;

    showDialog(
      context: context,
      builder:
          (context) => StatefulBuilder(
            builder: (context, setDialogState) {
              return AlertDialog(
                title: Row(
                  children: [
                    Icon(
                      Icons.swap_horiz,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                    const Text('Oddanie / wymiana zmiany'),
                  ],
                ),
                content: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Twoja zmiana: ${shift.shiftName} (${shift.startTime} - ${shift.endTime})',
                        style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                      ),
                      Text(
                        'Data: ${DateFormat('EEEE, d MMMM yyyy', 'pl_PL').format(shift.date)}',
                        style: GoogleFonts.inter(
                          color: Colors.grey.shade600,
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 16),
                      const Divider(),
                      const SizedBox(height: 8),
                      Text(
                        'Wybierz rodzaj oferty:',
                        style: GoogleFonts.inter(
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                        ),
                      ),
                      RadioListTile<bool>(
                        title: const Text('Otwarta giełda'),
                        subtitle: const Text(
                          'Każdy pracownik z odpowiednią rolą może przejąć tę zmianę.',
                        ),
                        value: false,
                        groupValue: isDirectSwap,
                        onChanged: (val) {
                          setDialogState(() {
                            isDirectSwap = val ?? false;
                            selectedTargetShiftId = null;
                          });
                        },
                        contentPadding: EdgeInsets.zero,
                      ),
                      RadioListTile<bool>(
                        title: const Text('Wymiana bezpośrednia (A ↔ B)'),
                        subtitle: const Text(
                          'Zaproponuj zamianę z konkretną zmianą współpracownika.',
                        ),
                        value: true,
                        groupValue: isDirectSwap,
                        onChanged:
                            coworkerShifts.isEmpty
                                ? null
                                : (val) {
                                  setDialogState(() {
                                    isDirectSwap = val ?? true;
                                    if (selectedTargetShiftId == null &&
                                        coworkerShifts.isNotEmpty) {
                                      selectedTargetShiftId =
                                          coworkerShifts.first.id;
                                    }
                                  });
                                },
                        contentPadding: EdgeInsets.zero,
                      ),
                      if (isDirectSwap) ...[
                        const SizedBox(height: 8),
                        if (coworkerShifts.isEmpty)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: Text(
                              'Brak dostępnych zmian współpracowników w tym tygodniu.',
                              style: TextStyle(
                                color: Colors.orange.shade800,
                                fontSize: 12,
                              ),
                            ),
                          )
                        else ...[
                          Text(
                            'Wybierz zmianę współpracownika:',
                            style: GoogleFonts.inter(
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 8),
                          DropdownButtonFormField<String>(
                            isExpanded: true,
                            value: selectedTargetShiftId,
                            decoration: InputDecoration(
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                              contentPadding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 8,
                              ),
                            ),
                            items:
                                coworkerShifts.map((c) {
                                  final dateStr = DateFormat(
                                    'E, d MMM',
                                    'pl_PL',
                                  ).format(c.date);
                                  return DropdownMenuItem<String>(
                                    value: c.id,
                                    child: Text(
                                      '${c.userName}: $dateStr ${c.startTime.substring(0, 5)}-${c.endTime.substring(0, 5)} (${c.roleName})',
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(fontSize: 13),
                                    ),
                                  );
                                }).toList(),
                            onChanged: (val) {
                              setDialogState(
                                () => selectedTargetShiftId = val,
                              );
                            },
                          ),
                        ],
                      ],
                      const SizedBox(height: 12),
                      Text(
                        isDirectSwap
                            ? 'Wskazany współpracownik zobaczy dedykowaną ofertę wymiany. Po jej akceptacji nastąpi automatyczna obustronna zamiana grafików.'
                            : 'Zmiana pojawi się na ogólnej giełdzie. Musisz pracować, dopóki ktoś jej nie przejmie.',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: Colors.grey.shade600,
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
                    onPressed:
                        isDirectSwap && selectedTargetShiftId == null
                            ? null
                            : () {
                              Navigator.pop(context);
                              _submitGiveaway(
                                shift.id,
                                targetShiftId:
                                    isDirectSwap ? selectedTargetShiftId : null,
                              );
                            },
                    child: Text(
                      isDirectSwap
                          ? 'Zaproponuj wymianę'
                          : 'Wystaw na giełdę',
                    ),
                  ),
                ],
              );
            },
          ),
    );
  }

  Future<void> _submitGiveaway(String scheduleId, {String? targetShiftId}) async {
    setState(() => _isLoading = true);
    try {
      await ref
          .read(apiServiceProvider)
          .giveAwayShift(scheduleId, targetShiftId: targetShiftId);
      await _loadSchedule(); // Refresh to show "On Giveaway" status
      if (_showCoworkers) await _loadTeamSchedule();
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              targetShiftId != null
                  ? '✓ Zaproponowano bezpośrednią wymianę (A ↔ B)'
                  : '✓ Zmiana wystawiona na giełdę',
            ),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
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
}
